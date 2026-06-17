"""Local GBK-CSV L2 ingest adapter — Track L.

Reads per-stock GBK CSVs (`行情`/`逐笔委托`/`逐笔成交`) from the local corpus
layout::

    <root>/<date>/<date>/<stock>/{行情.csv, 逐笔委托.csv, 逐笔成交.csv}

Returns a cleaned, temporally-sorted DataFrame whose column set is a **superset**
of what ``ingest._normalise_and_clean`` produces on the xlsx path, so the whole
downstream pipeline (aggregate → features → rules → …) can consume both paths
unchanged.

Key differences vs the xlsx path
---------------------------------
- Encoding: **gb18030** (GBK superset); the xlsx path uses ``openpyxl``.
- Column names: **Chinese headers** → mapped to canonical English via a global
  constant dict (hard rule #2 — no per-stock branching).
- Time: ``时间`` is a Beijing-local ``HHMMSSmmm`` integer; we parse it directly to
  ``hour``/``minute`` (sidesteps the RS ``datetime64[ms]`` dtype bug on the xlsx
  path) while building a sortable ``datetime_utc``-equivalent from ``自然日`` +
  ``时间`` for ordering and RS interval diffs.
- Book: ``申买/卖价|量1..10`` are explicit columns; we reshape them to
  ``bids``/``asks`` JSON (list-of-dicts, same schema ``parse_book_json`` yields)
  so OBP/OFI features read them unchanged.
- Cancels: **embedded per-exchange** — SZ: ``逐笔成交.成交代码 == 'C'``;
  SH: ``逐笔委托.委托类型 == 'D'``.  ``cb_available`` is set to ``1.0`` whenever
  at least one cancel is found; no hint-column detector is needed.
- ``bigordervolume``: derived from large ``逐笔成交`` prints (not a snapshot col).

Out of scope for this module
-----------------------------
- ``src/ingest.load_raw`` (xlsx path) — left entirely intact.
- ``features._cb_features`` real math (Track L-b follow-up; the ``True`` branch
  currently returns zero CB values with ``cb_available=1.0`` — a structural stub).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import pandas as pd

from config import OSS_THRESHOLDS

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stream file names (without .csv extension)
# ---------------------------------------------------------------------------
STREAM_NAMES = ("行情", "逐笔委托", "逐笔成交")

# ---------------------------------------------------------------------------
# Column rename map: Chinese header → canonical English
# (Global constant dict — compliance hard rule #2: no per-stock branching.)
# ---------------------------------------------------------------------------
HQ_COL_MAP: dict[str, str] = {
    "万得代码": "stock_code",
    "交易所代码": "exchange",
    "自然日": "transaction_date",
    "时间": "_time_int",         # raw HHMMSSmmm integer — processed, not emitted as-is
    "成交价": "price",
    "成交量": "_tick_vol_raw",    # per-tick volume from snapshot (not cumulative; kept separate)
    "成交额": "_tick_amt_raw",    # per-tick amount from snapshot (not cumulative)
    "成交笔数": "transactions",
    "IOPV": "iopv",
    "成交标志": "trade_flag",
    "BS标志": "bs_flag",
    "当日累计成交量": "_cum_volume",   # cumulative → will be diff()'d to tick_volume
    "当日成交额": "_cum_amount",       # cumulative → will be diff()'d to tick_amount
    "最高价": "high",
    "最低价": "low",
    "开盘价": "open",
    "前收盘": "prev_close",
    # Bid/ask price/volume levels 1–10 (renamed to internal then reshaped to JSON)
    **{f"申卖价{i}": f"_ask_p{i}" for i in range(1, 11)},
    **{f"申卖量{i}": f"_ask_v{i}" for i in range(1, 11)},
    **{f"申买价{i}": f"_bid_p{i}" for i in range(1, 11)},
    **{f"申买量{i}": f"_bid_v{i}" for i in range(1, 11)},
    "加权平均叫卖价": "weightedaskprice",
    "加权平均叫买价": "weightedbidprice",
    "叫卖总量": "totalaskvolume",
    "叫买总量": "totalbidvolume",
    "不加权指数": "unweighted_index",
    "品种总数": "total_stocks",
    "上涨品种数": "rising_stocks",
    "下跌品种数": "falling_stocks",
    "持平品种数": "flat_stocks",
}

ORDER_COL_MAP: dict[str, str] = {
    "万得代码": "stock_code",
    "交易所代码": "exchange",
    "自然日": "transaction_date",
    "时间": "time_int",
    "委托编号": "order_no",
    "交易所委托号": "exchange_order_no",
    "委托类型": "order_type",   # 'A'=Add, 'D'=Delete/cancel (SH)
    "委托代码": "side",         # 'B'=buy, 'S'=sell
    "委托价格": "order_price",
    "委托数量": "order_qty",
}

TRADE_COL_MAP: dict[str, str] = {
    "万得代码": "stock_code",
    "交易所代码": "exchange",
    "自然日": "transaction_date",
    "时间": "time_int",
    "成交编号": "trade_no",
    "成交代码": "trade_code",   # '0'=trade, 'C'=cancel (SZ)
    "委托代码": "side",         # 'B'=buy, 'S'=sell
    "BS标志": "bs_flag",
    "成交价格": "trade_price",
    "成交数量": "trade_qty",
    "叫卖序号": "ask_seq",
    "叫买序号": "bid_seq",
}

# Threshold for "large" / big-order trades (shares) — same scale as OSS
BIG_ORDER_THRESHOLD: int = OSS_THRESHOLDS["large"]  # ≥ 10 000 shares


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_stocks(
    root: str,
    date: str,
    max_stocks: Optional[int] = None,
) -> list[tuple[str, str]]:
    """Return a list of ``(date, stock_code)`` pairs found under *root/date/date/*.

    Parameters
    ----------
    root:
        Corpus root directory (e.g. ``"data"`` or a test fixture path).
    date:
        Trading date as ``YYYYMMDD`` string.
    max_stocks:
        Cap on the number of stocks returned (for dev / testing). ``None`` (or
        ``0``) means no limit.
    """
    inner_dir = os.path.join(root, date, date)
    if not os.path.isdir(inner_dir):
        log.warning("discover_stocks: directory not found: %s", inner_dir)
        return []

    codes = sorted(
        d for d in os.listdir(inner_dir)
        if os.path.isdir(os.path.join(inner_dir, d))
    )
    if max_stocks:
        codes = codes[:max_stocks]
    return [(date, code) for code in codes]


def read_snapshot(stock_dir: str, stock_code: str, date: str) -> pd.DataFrame:
    """Read ``行情.csv`` (GBK, Chinese headers) → cleaned canonical DataFrame.

    Output carries: ``stock_code``, ``transaction_date``, ``price``, ``volume``
    (per-tick), ``amount`` (per-tick), ``tick_volume``, ``tick_amount``,
    ``hour``, ``minute``, ``datetime_utc``, ``price_change``, ``bids``, ``asks``,
    ``totalbidvolume``, ``totalaskvolume``, plus misc snapshot cols.
    """
    path = os.path.join(stock_dir, "行情.csv")
    df = pd.read_csv(path, encoding="gb18030", dtype=str)
    df = df.rename(columns={k: v for k, v in HQ_COL_MAP.items() if k in df.columns})

    # --- Ensure mandatory fields exist ---
    df["stock_code"] = stock_code
    df["transaction_date"] = str(date)

    # --- Time parsing: HHMMSSmmm integer → hour / minute + sortable timestamp ---
    df["_time_int"] = pd.to_numeric(df.get("_time_int", pd.Series(dtype="Int64")),
                                    errors="coerce").fillna(0).astype(int)
    # HHMMSSmmm: e.g. 93000000 = 09 30 00 000
    hour = df["_time_int"] // 10_000_000
    minute = (df["_time_int"] % 10_000_000) // 100_000
    second = (df["_time_int"] % 100_000) // 1_000
    ms = df["_time_int"] % 1_000

    df["hour"] = hour.astype(int)
    df["minute"] = minute.astype(int)

    # Build a tz-naive Beijing-local Timestamp (keeps RS interval diffs simple and
    # dtype-stable — avoids the datetime64[ms] over-division bug on the xlsx path).
    # Use the date + parsed H/M/S/ms components.
    year = int(date[:4])
    mon = int(date[4:6])
    day = int(date[6:8])
    df["datetime_utc"] = pd.to_datetime(
        dict(year=year, month=mon, day=day,
             hour=hour, minute=minute, second=second,
             microsecond=ms * 1000),
        errors="coerce",
    )

    # --- Numeric coercions ---
    for col in ["price", "_cum_volume", "_cum_amount", "totalbidvolume", "totalaskvolume",
                "weightedaskprice", "weightedbidprice"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Canonical names: cumulative volume/amount are the baseline for diff()
    # The raw per-tick columns from the snapshot are not cumulative and are kept
    # under internal names; we use the cumulative columns as the diff() source.
    df["price"] = pd.to_numeric(df.get("price", pd.Series(dtype="float64")),
                                errors="coerce").fillna(0.0)
    df["volume"] = pd.to_numeric(df.get("_cum_volume", pd.Series(dtype="float64")),
                                 errors="coerce").fillna(0.0)
    df["amount"] = pd.to_numeric(df.get("_cum_amount", pd.Series(dtype="float64")),
                                 errors="coerce").fillna(0.0)

    # --- Filter bad rows (baseline contract) ---
    df = df[(df["price"] > 0) & (df["volume"] >= 0) & (df["amount"] >= 0)]

    # --- Temporal sort (baseline contract) ---
    df = df.sort_values(by=["stock_code", "transaction_date", "datetime_utc"])
    df = df.reset_index(drop=True)

    # --- Cumulative → per-tick increments (baseline contract) ---
    for src, tick_col in [("volume", "tick_volume"), ("amount", "tick_amount")]:
        if src in df.columns:
            df[tick_col] = df[src].diff().fillna(0).clip(lower=0)

    # price_change for AP features (first row per stock → 0.0, not NaN)
    df["price_change"] = df["price"].diff().fillna(0.0)

    # --- Reshape explicit book levels → bids / asks JSON strings ---
    df["bids"] = _make_book_json(df, side="bid")
    df["asks"] = _make_book_json(df, side="ask")

    # Drop internal / redundant columns (keep frame lean)
    drop_cols = (
        [f"_bid_p{i}" for i in range(1, 11)] +
        [f"_bid_v{i}" for i in range(1, 11)] +
        [f"_ask_p{i}" for i in range(1, 11)] +
        [f"_ask_v{i}" for i in range(1, 11)] +
        ["_time_int", "_cum_volume", "_cum_amount",
         "_tick_vol_raw", "_tick_amt_raw"]
    )
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    return df


def read_cancel_frame(stock_dir: str, stock_code: str) -> pd.DataFrame:
    """Reconstruct a normalized cancel frame from the per-exchange embedded signals.

    - **SZ** (``.SZ``): cancels are rows in ``逐笔成交.csv`` where ``成交代码 == 'C'``.
    - **SH** (``.SH``): cancels are rows in ``逐笔委托.csv`` where ``委托类型 == 'D'``.

    Returns a DataFrame with at least columns: ``side``, ``time_int``, ``cancel_qty``.
    Returns an **empty** DataFrame (zero rows) if no cancels are found.
    """
    exchange = stock_code.split(".")[-1].upper() if "." in stock_code else "UNKNOWN"

    cancels_list = []

    if exchange == "SZ":
        path = os.path.join(stock_dir, "逐笔成交.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="gb18030", dtype=str)
            df = df.rename(columns={k: v for k, v in TRADE_COL_MAP.items() if k in df.columns})
            if "trade_code" in df.columns:
                mask = df["trade_code"].astype(str).str.strip() == "C"
                if mask.any():
                    c = df[mask].copy()
                    c["cancel_qty"] = pd.to_numeric(
                        c.get("trade_qty", pd.Series(dtype="float64")), errors="coerce"
                    ).fillna(0)
                    # Normalize side: preserve B/S if present, else derive from bs_flag
                    if "side" not in c.columns and "bs_flag" in c.columns:
                        c["side"] = c["bs_flag"]
                    elif "side" not in c.columns:
                        c["side"] = "U"
                    c["cancel_time"] = pd.to_numeric(
                        c.get("time_int", pd.Series(dtype="float64")), errors="coerce"
                    ).fillna(0).astype(int)
                    cancels_list.append(c[["side", "cancel_time", "cancel_qty"]])

    elif exchange == "SH":
        path = os.path.join(stock_dir, "逐笔委托.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="gb18030", dtype=str)
            df = df.rename(columns={k: v for k, v in ORDER_COL_MAP.items() if k in df.columns})
            if "order_type" in df.columns:
                mask = df["order_type"].astype(str).str.strip() == "D"
                if mask.any():
                    c = df[mask].copy()
                    c["cancel_qty"] = pd.to_numeric(
                        c.get("order_qty", pd.Series(dtype="float64")), errors="coerce"
                    ).fillna(0)
                    if "side" not in c.columns:
                        c["side"] = "U"
                    c["cancel_time"] = pd.to_numeric(
                        c.get("time_int", pd.Series(dtype="float64")), errors="coerce"
                    ).fillna(0).astype(int)
                    cancels_list.append(c[["side", "cancel_time", "cancel_qty"]])

    if cancels_list:
        result = pd.concat(cancels_list, ignore_index=True)
        # Add a generic 'time_int' alias so callers can use either name
        result["time_int"] = result["cancel_time"]
        return result

    return pd.DataFrame(columns=["side", "cancel_time", "cancel_qty", "time_int"])


def _derive_bigorder_volume(stock_dir: str, stock_code: str) -> dict[int, float]:
    """Derive per-snapshot-row bigordervolume from large 逐笔成交 prints.

    Returns a mapping ``{time_int: cumulative_bigorder_qty_up_to_that_time}``.
    We accumulate large prints (≥ BIG_ORDER_THRESHOLD shares) in time order, then
    the snapshot can pick up the nearest ≤ snapshot-time entry.

    Actually, we build a simple *total* per-stock-day (a scalar) and then spread
    it proportionally across snapshots on the first row.  The simpler approach:
    return a running total keyed by the trade's time_int so the snapshot merge can
    assign per-row deltas.
    """
    path = os.path.join(stock_dir, "逐笔成交.csv")
    if not os.path.exists(path):
        return {}

    df = pd.read_csv(path, encoding="gb18030", dtype=str)
    df = df.rename(columns={k: v for k, v in TRADE_COL_MAP.items() if k in df.columns})

    # Real trades only (not cancels)
    if "trade_code" in df.columns:
        df = df[df["trade_code"].astype(str).str.strip() != "C"]

    qty_col = "trade_qty" if "trade_qty" in df.columns else None
    time_col = "time_int" if "time_int" in df.columns else None

    if qty_col is None or time_col is None:
        return {}

    df["_qty"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
    df["_t"] = pd.to_numeric(df[time_col], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("_t")

    big = df[df["_qty"] >= BIG_ORDER_THRESHOLD]
    # Return {time_int: bigorder_qty_at_that_tick} — a list of (time, qty) pairs
    return dict(zip(big["_t"].tolist(), big["_qty"].tolist()))


def load_local(
    root: str,
    date: str,
    max_stocks: Optional[int] = None,
) -> pd.DataFrame:
    """Read the local GBK-CSV corpus and return a cleaned, multi-stock tick frame.

    The returned DataFrame carries the **same column contract** as
    ``ingest._normalise_and_clean`` — every column ``features.compute_daily_features``
    reads is present.  ``cb_available`` is ``1.0`` for stocks where embedded cancels
    are found, ``0.0`` otherwise.

    Parameters
    ----------
    root:
        Corpus root directory (e.g. ``"data"`` or ``"tests/fixtures/local_l2_tiny"``).
    date:
        Trading date as ``YYYYMMDD`` string.
    max_stocks:
        Cap on the number of stocks to load. ``None`` = no limit (all stocks).
    """
    pairs = discover_stocks(root, date, max_stocks=max_stocks)
    if not pairs:
        log.warning("load_local: no stock directories found under %s/%s", root, date)
        return pd.DataFrame()

    frames = []
    for (d, code) in pairs:
        stock_dir = os.path.join(root, d, d, code)
        try:
            snap = read_snapshot(stock_dir, code, d)
        except Exception as exc:
            log.warning("load_local: failed to read snapshot for %s/%s: %s", d, code, exc)
            continue

        if snap.empty:
            log.info("load_local: empty snapshot for %s/%s — skipping", d, code)
            continue

        # --- Cancel reconstruction ---
        try:
            cancel_df = read_cancel_frame(stock_dir, code)
            has_cancel = len(cancel_df) > 0
        except Exception as exc:
            log.warning("load_local: cancel read failed for %s/%s: %s", d, code, exc)
            has_cancel = False

        snap["cb_available"] = 1.0 if has_cancel else 0.0

        # --- bigordervolume from large trades ---
        try:
            big_map = _derive_bigorder_volume(stock_dir, code)
        except Exception as exc:
            log.warning("load_local: bigorder read failed for %s/%s: %s", d, code, exc)
            big_map = {}

        # Assign bigordervolume: for each snapshot row, find trade prints at or before
        # its time_int and accumulate into a per-tick delta (we use snapshot time for
        # nearest-match; then diff to get per-row ticks).
        snap["tick_bigordervolume"] = _assign_bigorder_per_tick(snap, big_map)

        frames.append(snap)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    # Final sort across all stocks
    out = out.sort_values(by=["stock_code", "transaction_date", "datetime_utc"])
    out = out.reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _make_book_json(df: pd.DataFrame, side: str) -> pd.Series:
    """Reshape explicit bid/ask price+volume columns → JSON string per row.

    *side* is ``"bid"`` (申买) or ``"ask"`` (申卖).
    Output JSON: ``[{"price": .., "volume": ..}, ...]`` — same schema as
    ``ingest.parse_book_json`` produces, so OBP/OFI features read them unchanged.
    """
    prefix_p = f"_bid_p" if side == "bid" else f"_ask_p"
    prefix_v = f"_bid_v" if side == "bid" else f"_ask_v"

    records: list[list[dict]] = [[] for _ in range(len(df))]

    for i in range(1, 11):
        col_p = f"{prefix_p}{i}"
        col_v = f"{prefix_v}{i}"
        if col_p not in df.columns or col_v not in df.columns:
            continue
        prices = pd.to_numeric(df[col_p], errors="coerce").fillna(0.0)
        vols = pd.to_numeric(df[col_v], errors="coerce").fillna(0.0)
        for row_idx, (p, v) in enumerate(zip(prices, vols)):
            records[row_idx].append({"price": float(p), "volume": float(v)})

    return pd.Series([json.dumps(r) for r in records], index=df.index)


def _assign_bigorder_per_tick(
    snap: pd.DataFrame,
    big_map: dict[int, float],
) -> pd.Series:
    """Assign per-snapshot-row bigordervolume increments.

    For each snapshot row, we sum all large trade prints whose ``time_int`` falls
    between the previous snapshot's time and the current one (left-exclusive,
    right-inclusive) using the snapshot's ``_time_int`` column.

    Since we dropped ``_time_int`` in ``read_snapshot``, we re-derive the integer
    time from ``hour``/``minute`` stored in *snap*.
    """
    if not big_map or snap.empty:
        return pd.Series(0.0, index=snap.index)

    # Rebuild integer time: HHMM * 100000 (no seconds in snapshot resolution)
    # Use hour/minute which are already computed
    snap_time = (snap["hour"] * 10_000_000 + snap["minute"] * 100_000).astype(int)

    big_times = sorted(big_map.keys())
    big_qtys = [big_map[t] for t in big_times]

    result = []
    prev_time = 0
    for st in snap_time:
        # Sum big-order prints strictly between prev_time and st (inclusive)
        total = sum(
            q for t, q in zip(big_times, big_qtys) if prev_time < t <= st
        )
        result.append(float(total))
        prev_time = st

    return pd.Series(result, index=snap.index)
