"""Feature computation from raw L2 ticks — the critical path.

Ports the baseline feature-extraction logic (baseline-guide.md L330-414) into a
single per-(stock, day) function. Eight families are touched; the snapshot-only
fixture cannot supply Cancel-Behaviour (CB) signal, so CB degrades gracefully to
a zero-valued, flagged sub-vector rather than hard-failing (brief §9 step 5).

All features are intraday-only (no look-ahead). Every output key is a plain float
so the daily matrix is numeric and seed-stable.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from config import CB_FAST_CANCEL_MS, OSS_THRESHOLDS, RS_BURST_THRESHOLD_MS, TRD_SIZE_BINS
from src.ingest import parse_book_json

log = logging.getLogger(__name__)

# CB feature keys produced whether or not a cancel table is present (graceful set).
CB_KEYS = (
    "cb_cancel_order_ratio",
    "cb_cancel_volume_ratio",
    "cb_fast_cancel_ratio",
    "cb_buy_cancel_ratio",
    "cb_sell_cancel_ratio",
)


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _book_imbalance(book_bids: list[dict], book_asks: list[dict]) -> float:
    """(bid_vol - ask_vol) / (bid_vol + ask_vol) summed over available levels."""
    bid_vol = sum(float(lvl.get("volume", 0) or 0) for lvl in book_bids)
    ask_vol = sum(float(lvl.get("volume", 0) or 0) for lvl in book_asks)
    return _safe_div(bid_vol - ask_vol, bid_vol + ask_vol)


def _oss_features(tick_vol: pd.Series, tick_amt: pd.Series) -> dict:
    """Order-Size-Segmentation amount/count shares by SHARE thresholds."""
    mega = tick_vol >= OSS_THRESHOLDS["mega"]
    large = (tick_vol >= OSS_THRESHOLDS["large"]) & (tick_vol < OSS_THRESHOLDS["mega"])
    mid = (tick_vol >= OSS_THRESHOLDS["mid"]) & (tick_vol < OSS_THRESHOLDS["large"])
    small = tick_vol < OSS_THRESHOLDS["mid"]

    total_amt = tick_amt.sum()
    total_cnt = len(tick_vol)
    out = {}
    for name, mask in (("mega", mega), ("large", large), ("mid", mid), ("small", small)):
        out[f"oss_{name}_amount_pct"] = _safe_div(tick_amt[mask].sum(), total_amt)
        out[f"oss_{name}_count_pct"] = _safe_div(int(mask.sum()), total_cnt)
    return out


def _ap_features(group: pd.DataFrame) -> dict:
    """Active-Participation: infer aggressor side from price changes (baseline AP)."""
    pc = group["price_change"]
    amt = group["tick_amount"]
    buy_amt = amt[pc > 0].sum()
    sell_amt = amt[pc < 0].sum()
    denom = buy_amt + sell_amt
    buy_pct = _safe_div(buy_amt, denom)
    sell_pct = _safe_div(sell_amt, denom)
    return {
        "ap_active_buy_pct": buy_pct,
        "ap_active_sell_pct": sell_pct,
        "ap_active_net_direction": buy_pct - sell_pct,
        "ap_unilateral_intensity": _safe_div(abs(buy_amt - sell_amt), denom),
    }


def _pi_features(group: pd.DataFrame) -> dict:
    """Period-Intraday session concentration using the Beijing clock.

    Beijing A-share continuous session: 09:30:00–11:30:00 and 13:00:00–15:00:00.
    Open window = first 30 min [09:30, 10:00]; close window = last 10 min
    [14:50, 15:00] — inclusive of 15:00:00 so the closing-auction prints count.
    `hour`/`minute` are both derived from the Beijing-local clock (see ingest).
    """
    hour, minute, amt = group["hour"], group["minute"], group["tick_amount"]
    total = amt.sum()
    # minutes-since-midnight makes the inclusive boundaries unambiguous.
    mins = hour * 60 + minute
    open_30 = (mins >= 9 * 60 + 30) & (mins <= 10 * 60)        # 09:30 .. 10:00
    close_10 = (mins >= 14 * 60 + 50) & (mins <= 15 * 60)      # 14:50 .. 15:00 (incl 15:00)
    open_pct = _safe_div(amt[open_30].sum(), total)
    close_pct = _safe_div(amt[close_10].sum(), total)
    return {
        "pi_open_30min_amount_pct": open_pct,
        "pi_close_10min_amount_pct": close_pct,
        "pi_time_concentration": open_pct + close_pct,
        "pi_price_std_pct": _safe_div(float(group["price"].std(ddof=0)),
                                      float(group["price"].mean())),
    }


def _rs_features(group: pd.DataFrame) -> dict:
    """Rhythm/Sequence: inter-tick interval CV, burst ratio, split similarity.

    Resolution-robust: uses .diff().dt.total_seconds() * 1000 so the result
    is the same regardless of whether datetime_utc is datetime64[ns] (pandas
    2.2.x) or datetime64[ms] (pandas 3.0.x).  The old astype("int64")//1_000_000
    path assumed nanosecond resolution and over-divided on ms-dtype timestamps
    (every 30 s gap collapsed to 0 ms → cv=13.48, burst=0.99).

    Burst definition: share of intervals strictly < RS_BURST_THRESHOLD_MS (100 ms
    by default).  Absolute threshold avoids the saturation problem of the old
    0.25*mean definition (which equals 1.0 whenever mean≈0).
    """
    # dtype-portable millisecond intervals
    intervals_ms = (
        group["datetime_utc"].diff().dropna().dt.total_seconds() * 1000.0
    )
    intervals_ms = intervals_ms[intervals_ms >= 0]
    if len(intervals_ms) < 2:
        return {
            "rs_interval_cv": 0.0,
            "rs_burst_ratio": 0.0,
            "rs_split_similarity": 0.0,
        }
    mean_ms = float(intervals_ms.mean())
    cv = _safe_div(float(intervals_ms.std(ddof=0)), mean_ms)
    # burst: absolute threshold (baseline ref: < 100 ms)
    burst = float((intervals_ms < RS_BURST_THRESHOLD_MS).sum()) / len(intervals_ms)
    # split similarity: max(0, 1 - cv) — higher when cadence is uniform (iceberg split proxy)
    split_sim = max(0.0, 1.0 - cv)
    return {
        "rs_interval_cv": cv,
        "rs_burst_ratio": burst,
        "rs_split_similarity": split_sim,
    }


def _obp_features(group: pd.DataFrame) -> dict:
    """Order-Book-Profile: dual-source imbalance (first snapshot + full-day mean)."""
    # Plan A — first snapshot nested JSON.
    first = group.iloc[0]
    bids = parse_book_json(first.get("bids"))
    asks = parse_book_json(first.get("asks"))
    book_imbalance = _book_imbalance(bids, asks)
    best_bid = float(bids[0]["price"]) if bids else np.nan
    best_ask = float(asks[0]["price"]) if asks else np.nan
    spread = (best_ask - best_bid) if (bids and asks) else 0.0
    big_quote_share = np.nanmean(
        [float(lvl.get("bigOrderPercent", 0) or 0) for lvl in (bids + asks)]
    ) if (bids or asks) else 0.0

    # Plan B — full-day totals.
    if {"totalbidvolume", "totalaskvolume"}.issubset(group.columns):
        tb = group["totalbidvolume"].astype(float)
        ta = group["totalaskvolume"].astype(float)
        per_row = (tb - ta) / (tb + ta).replace(0, np.nan)
        obp_imbalance_mean = float(per_row.fillna(0).mean())
    else:
        obp_imbalance_mean = 0.0

    return {
        "book_imbalance": book_imbalance,
        "obp_imbalance_mean": obp_imbalance_mean,
        "obp_spread": float(spread),
        "obp_big_quote_share": float(big_quote_share),
    }


def _pd_features(group: pd.DataFrame) -> dict:
    """Price-Discovery (light): max intraday price impact + execution efficiency."""
    p = group["price"]
    base = float(p.iloc[0]) if len(p) else 0.0
    max_impact = _safe_div(float((p - base).abs().max()), base) if base else 0.0
    return {"pd_max_price_impact_pct": max_impact}


def _trd_size_entropy(volumes) -> float:
    """Normalized Shannon entropy of genuine-trade print SIZES over the log-spaced
    ``TRD_SIZE_BINS`` ladder, in [0, 1].

    Measures size-VALUE heterogeneity (spec §B.2): 散户 = many distinct human sizes
    (HIGH); 量化 = a few repeated algo clip sizes (LOW); 游资 = mega-skewed (low).
    The denominator is ``ln(total_bins)`` FIXED — NOT ``ln(non-empty bins)`` — so a
    2-clip distribution stays low (it would be 1.0 under non-empty normalisation).
    Empty / single-print / degenerate input -> 0.0.
    """
    if volumes is None:
        return 0.0
    v = np.asarray(list(volumes), dtype=float)
    v = v[np.isfinite(v) & (v > 0.0)]
    if v.size < 2:
        return 0.0
    n_bins = len(TRD_SIZE_BINS) + 1
    idx = np.digitize(v, TRD_SIZE_BINS)                  # 0 .. n_bins-1
    counts = np.bincount(idx, minlength=n_bins).astype(float)
    p = counts[counts > 0]
    p = p / p.sum()
    h = float(-(p * np.log(p)).sum())
    denom = np.log(n_bins)
    return 0.0 if denom <= 0 else float(min(1.0, max(0.0, h / denom)))


def _trd_size_entropy_features(volumes) -> dict:
    """Wrapper mirroring the ``_x_features`` family."""
    return {"trd_size_entropy": _trd_size_entropy(volumes)}


def _limit_seal_features(group: pd.DataFrame) -> dict:
    """Intraday limit-seal detector (Feature B.3).

    Computes the fraction of ticks whose price is within tick_eps of the day's
    extreme (max for limit-up, min for limit-down).

        limit_seal_up_ratio   = mean(price >= day_high - tick_eps)
        limit_seal_down_ratio = mean(price <= day_low  + tick_eps)

    Price-scale note: ``group["price"]`` is always in yuan-float units when it
    reaches this function.  The parquet L2 corpus stores raw prices as ×100
    integers, but ``ingest_parquet._normalise_and_clean`` divides by 100.0
    (line ~218: ``df["price"] = pd.to_numeric(df["Price"]) / 100.0``), so the
    column contains values like 12.34 (yuan).  The snapshot/xlsx ingest also
    delivers yuan-float prices.
    ``tick_eps=0.01`` = 1 fen = the minimum A-share tick increment, which is the
    correct granularity: it admits ticks within one minimum move of the extreme
    (e.g., a sealed stock printing at or 1 fen below the limit) while excluding
    ticks further away.

    Graceful degradation:
        If the group's ``price`` column is missing, empty, or contains no
        finite values, **both keys are omitted entirely** (not emitted as 0.0).
        An absent key votes NEUTRAL (+0.5) via the existing absent-dim
        convention in ``rules._class_score`` (line 104-106), which is the
        correct behaviour: no price series → no regime information.

    Returns
    -------
    dict
        Contains ``limit_seal_up_ratio`` and/or ``limit_seal_down_ratio`` as
        raw [0, 1] floats when a usable price series is present; empty dict
        otherwise.  Both keys are always emitted together or not at all.
    """
    if "price" not in group.columns:
        return {}
    price = group["price"]
    # Filter to finite values only
    p_numeric = pd.to_numeric(price, errors="coerce")
    p_finite = p_numeric.dropna()
    p_finite = p_finite[np.isfinite(p_finite)]
    if len(p_finite) == 0:
        return {}
    p = p_finite.astype(float)
    tick_eps = 0.01
    day_high = float(p.max())
    day_low = float(p.min())
    seal_up_ratio = float((p >= day_high - tick_eps).mean())
    seal_down_ratio = float((p <= day_low + tick_eps).mean())
    return {
        "limit_seal_up_ratio": seal_up_ratio,
        "limit_seal_down_ratio": seal_down_ratio,
    }


def _cb_features(
    group: pd.DataFrame,
    has_cancel_table: bool,
    cancel_df: "pd.DataFrame | None" = None,
) -> dict:
    """Cancel-Behaviour features.

    Snapshot-only path (has_cancel_table=False):
        All CB values → 0.0, cb_available → 0.0.  CB dims vote NEUTRAL in rules.

    Local-CSV / parquet path (has_cancel_table=True, cancel_df provided):
        Computes 5 CB ratios from the cancel event frame.  All outputs are finite
        floats in [0,1].

    Fast-cancel proxy note (Track L-c re-eval disposition)
    -------------------------------------------------------
    ``cb_fast_cancel_ratio`` is the share of **consecutive cancel pairs** whose
    inter-cancel interval (``cancel_time`` HHMMSSmmm integer diff, proxying ms at
    this resolution) is < CB_FAST_CANCEL_MS.  This is an **inter-cancel interval
    proxy**, NOT true order→cancel latency.

    Track L-c re-eval on n=24 parquet:data/202606 gate:
    - True sub-CB_FAST_CANCEL_MS latency = 0.64% of cancels (vanishingly rare)
    - Inter-cancel proxy fast rate = 86.8% (carries meaningful class signal)
    - Swapping to true latency: gate regressed 0.6599 → 0.6500 (FAIL, < 0.6599)
    - Disposition: inter-cancel proxy KEPT per LIS §6 Track L gate rule.

    The parquet and local paths both emit per-cancel ``latency_ms`` (OrderID
    self-join / ref-column join), available for a future re-thresholded or
    latency-distribution feature.  ``latency_ms`` is intentionally NOT consumed
    here per the gate disposition.  See tests/test_features.py Lc.1/Lc.4 for the
    discriminating tests (marked xfail, will pass when/if re-enabled).
    """
    if not has_cancel_table:
        out = {k: 0.0 for k in CB_KEYS}
        out["cb_available"] = 0.0
        return out

    out = {k: 0.0 for k in CB_KEYS}
    out["cb_available"] = 1.0

    # No cancel data available → return zero values with flag=1.0
    if cancel_df is None or len(cancel_df) == 0:
        return out

    n_cancel = len(cancel_df)

    # --- cb_cancel_order_ratio ---
    # cancel count / (cancel count + trade count)
    n_trades = len(group)
    out["cb_cancel_order_ratio"] = _safe_div(n_cancel, n_cancel + n_trades)

    # --- cb_cancel_volume_ratio ---
    # sum(cancel_qty) / (sum(cancel_qty) + sum(trade tick_volume))
    cancel_qty_col = "cancel_qty" if "cancel_qty" in cancel_df.columns else None
    cancel_vol = float(cancel_df[cancel_qty_col].sum()) if cancel_qty_col else 0.0
    trade_vol = float(group["tick_volume"].sum()) if "tick_volume" in group.columns else 0.0
    out["cb_cancel_volume_ratio"] = _safe_div(cancel_vol, cancel_vol + trade_vol)

    # --- cb_buy_cancel_ratio / cb_sell_cancel_ratio ---
    if "side" in cancel_df.columns:
        side = cancel_df["side"].astype(str).str.strip().str.upper()
        # Accept 'B'/'BUY' for buy, 'S'/'SELL' for sell
        buy_mask = side.str.startswith("B")
        sell_mask = side.str.startswith("S")
        out["cb_buy_cancel_ratio"] = _safe_div(int(buy_mask.sum()), n_cancel)
        out["cb_sell_cancel_ratio"] = _safe_div(int(sell_mask.sum()), n_cancel)

    # --- cb_fast_cancel_ratio ---
    # Inter-cancel interval proxy: share of consecutive cancel pairs with
    # cancel_time difference < CB_FAST_CANCEL_MS.
    # cancel_time is a HHMMSSmmm integer; consecutive differences proxy ms intervals
    # at the sub-second resolution used in A-share tick data.
    #
    # Track L-c re-eval note: the parquet and local cancel frames both carry a
    # true per-cancel ``latency_ms`` (OrderID self-join / ref-column join), but
    # swapping it in here REGRESSED the gate (0.6599 → 0.6500 on n=24 parquet)
    # because true sub-CB_FAST_CANCEL_MS latency is vanishingly rare (0.64% of
    # cancels), while the inter-cancel-burstiness proxy (~86.8% fast) carries
    # stronger class signal. Proxy kept per the Track L-c gate disposition;
    # ``latency_ms`` stays available (ingest_parquet / ingest_local both compute
    # it) for a future re-thresholded latency-distribution feature.
    time_col = "cancel_time" if "cancel_time" in cancel_df.columns else (
        "time_int" if "time_int" in cancel_df.columns else None
    )
    if time_col is not None and n_cancel >= 2:
        times = pd.to_numeric(cancel_df[time_col], errors="coerce").dropna().sort_values()
        intervals = times.diff().dropna()
        intervals = intervals[intervals >= 0]
        if len(intervals) > 0:
            fast = int((intervals < CB_FAST_CANCEL_MS).sum())
            out["cb_fast_cancel_ratio"] = _safe_div(fast, len(intervals))

    return out


def compute_daily_features(
    group: pd.DataFrame,
    has_cancel_table: bool = False,
    cancel_df: "pd.DataFrame | None" = None,
    deal_volumes=None,                      # NEW: per-print genuine-trade sizes (B.2)
) -> dict:
    """Compute the full per-(stock, day) feature vector for one tick group.

    `group` is the rows of a single (stock_code, transaction_date), already cleaned,
    sorted, and carrying tick_* increment columns (see ingest._normalise_and_clean).

    `cancel_df` is the per-(stock, day) cancel event frame produced by
    ``ingest_local.read_cancel_frame``.  When provided and ``has_cancel_table=True``,
    real CB feature values are computed.  When ``None`` (the default), CB values are
    0.0 (backward-compatible: snapshot/xlsx path is unaffected).

    `deal_volumes` is the list of genuine-trade print sizes (shares) for this
    (stock, day), produced by ``ingest_parquet.read_deal_sizes_parquet`` and threaded
    through ``aggregate.build_feature_matrix``.  When ``None`` (default — snapshot/
    xlsx path), ``trd_size_entropy`` is 0.0 (backward-compatible).
    """
    feat: dict[str, float] = {}
    tick_vol = group["tick_volume"]
    tick_amt = group["tick_amount"]

    feat.update(_oss_features(tick_vol, tick_amt))
    feat.update(_ap_features(group))
    feat.update(_pi_features(group))
    feat.update(_rs_features(group))
    feat.update(_obp_features(group))
    feat.update(_pd_features(group))
    feat.update(_cb_features(group, has_cancel_table, cancel_df=cancel_df))
    feat.update(_trd_size_entropy_features(deal_volumes))    # NEW (B.2)

    # big-order share (directly available field, summed over ticks)
    if "tick_bigordervolume" in group.columns:
        feat["bigorder_volume_pct"] = _safe_div(
            float(group["tick_bigordervolume"].sum()), float(tick_vol.sum())
        )
    else:
        feat["bigorder_volume_pct"] = 0.0

    feat["n_ticks"] = float(len(group))
    # scrub any inf/nan that slipped through (standard features only)
    result = {k: (0.0 if (v is None or not np.isfinite(v)) else float(v))
              for k, v in feat.items()}

    # NEW (B.3): limit-seal ratios — added AFTER the scrubber so that graceful
    # degradation (absent key) is preserved.  An absent key votes NEUTRAL in
    # rules._class_score; emitting 0.0 would falsely suppress the seal signal.
    # The dict is empty when no usable price series exists (snapshot/no-price path).
    seal_feats = _limit_seal_features(group)
    result.update(seal_feats)

    return result
