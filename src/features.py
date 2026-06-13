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

from config import OSS_THRESHOLDS
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
    """Rhythm/Sequence: inter-tick interval coefficient of variation + burst ratio."""
    # interval diffs are timezone-invariant; use the UTC stamp for clarity.
    ts = group["datetime_utc"].astype("int64") // 1_000_000  # ms
    intervals = ts.diff().dropna()
    intervals = intervals[intervals >= 0]
    if len(intervals) < 2:
        return {"rs_interval_cv": 0.0, "rs_burst_ratio": 0.0}
    mean = intervals.mean()
    cv = _safe_div(float(intervals.std(ddof=0)), float(mean))
    # burst ratio: share of intervals far below the mean (rapid-fire submissions)
    burst = _safe_div(int((intervals < 0.25 * mean).sum()), len(intervals))
    return {"rs_interval_cv": cv, "rs_burst_ratio": burst}


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


def _cb_features(group: pd.DataFrame, has_cancel_table: bool) -> dict:
    """Cancel-Behaviour. Snapshot-only -> zero-valued, flagged (graceful degrade)."""
    if not has_cancel_table:
        out = {k: 0.0 for k in CB_KEYS}
        out["cb_available"] = 0.0
        return out
    # Seam for the real tick-cancel computation once a cancel table is wired in.
    # TODO(cancel-table): compute fast-cancel ratio, buy/sell cancel divergence,
    # cancel-interval CV from the tick-cancellation stream.
    out = {k: 0.0 for k in CB_KEYS}
    out["cb_available"] = 1.0
    return out


def compute_daily_features(group: pd.DataFrame, has_cancel_table: bool = False) -> dict:
    """Compute the full per-(stock, day) feature vector for one tick group.

    `group` is the rows of a single (stock_code, transaction_date), already cleaned,
    sorted, and carrying tick_* increment columns (see ingest._normalise_and_clean).
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
    feat.update(_cb_features(group, has_cancel_table))

    # big-order share (directly available field, summed over ticks)
    if "tick_bigordervolume" in group.columns:
        feat["bigorder_volume_pct"] = _safe_div(
            float(group["tick_bigordervolume"].sum()), float(tick_vol.sum())
        )
    else:
        feat["bigorder_volume_pct"] = 0.0

    feat["n_ticks"] = float(len(group))
    # scrub any inf/nan that slipped through
    return {k: (0.0 if (v is None or not np.isfinite(v)) else float(v))
            for k, v in feat.items()}
