"""Parquet L2 ingest adapter — Track P.1.

Consumes the new English-schema, single-day parquet corpus under
``data/202606/<stream-CN>/<YYYYMMDD>/<stream>_<YYYYMMDD>.parquet`` (see
``docs/data_inventory_report_parquet.md``) and emits the **same cleaned-frame
contract** as :func:`src.ingest_local.load_local`, so the whole downstream
pipeline (aggregate → features → rules) consumes both paths unchanged.

Why a sibling module (not an extension of ``ingest_local``)
-----------------------------------------------------------
The schemas barely overlap: English columns vs Chinese headers, parquet
filter-read vs CSV-per-stock, **unified ``order`` cancels for both exchanges**
vs split SZ/SH streams, and integer ``×100`` prices. ``ingest_local`` and
``ingest.load_raw`` are left entirely intact.

Key facts (from the inventory report)
--------------------------------------
- All prices are integers = real price ``×100`` → divide by 100.
- ``SecuCode`` is a bare integer (leading zeros stripped, no exchange suffix).
- The ``order`` (委托补全) table carries cancels (``OrderType ∈ {-1,-11}``) for
  **both** exchanges — ``-1`` = 撤买 (buy cancel), ``-11`` = 撤卖 (sell cancel).
- The corpus is ~13 GB/day; **always filter by SecuCode before loading**
  (``pyarrow.dataset`` predicate pushdown) — never read a whole stream.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
import pyarrow.dataset as ds

from config import OSS_THRESHOLDS
from src.ingest_local import _make_book_json

log = logging.getLogger(__name__)

# Beijing-exchange numeric ranges (data_inventory_report_parquet.md §2)
_BJ_RANGES = ((400000, 500000), (800000, 900000), (920000, 930000))

# Stream folder (Chinese) for each logical stream — layout:
#   data/202606/<CN>/<YYYYMMDD>/<stream>_<YYYYMMDD>.parquet
_STREAM_DIR = {
    "snapshot": "十盘档口",
    "deal": "逐笔成交",
    "order_raw": "逐笔委托",
    "order": "委托补全",
    "index": "指数",
}

# Cancel encoding shared by both exchanges in the unified `order` table.
_CANCEL_TYPES = (-1, -11)          # -1 = 撤买 (buy cancel), -11 = 撤卖 (sell cancel)
_CANCEL_SIDE = {-1: "B", -11: "S"}

# "Large" / big-order threshold (shares) — same scale as OSS (mirrors ingest_local).
BIG_ORDER_THRESHOLD: int = OSS_THRESHOLDS["large"]

# Snapshot columns we consume (pushed down at read time; missing ones are skipped).
_SNAPSHOT_COLS = (
    ["SecuCode", "TradingDay", "TickTime", "Price",
     "TotalVolume", "TotalTurnover", "TotalAskVolume", "TotalBidVolume",
     "WeightAskPrice", "WeightBidPrice"]
    + [f"AskPrice{i}" for i in range(1, 11)] + [f"AskVolume{i}" for i in range(1, 11)]
    + [f"BidPrice{i}" for i in range(1, 11)] + [f"BidVolume{i}" for i in range(1, 11)]
)


def secu_to_stock_code(secu: int) -> str:
    """Map a bare integer ``SecuCode`` → canonical ``NNNNNN.XX`` stock code.

    ``SZ`` if ``< 400000``; ``BJ`` for the北交所 ranges; else ``SH`` (incl. 51x
    ETF, 6xx, 688/689 STAR, 90x B).
    """
    secu = int(secu)
    code6 = str(secu).zfill(6)
    if secu < 400000:
        exch = "SZ"
    elif any(lo <= secu < hi for (lo, hi) in _BJ_RANGES):
        exch = "BJ"
    else:
        exch = "SH"
    return f"{code6}.{exch}"


def stock_code_to_secu(code: str) -> int:
    """Inverse of :func:`secu_to_stock_code` — strip the suffix → bare integer."""
    return int(str(code).split(".")[0])


# ---------------------------------------------------------------------------
# Low-level filtered parquet read (memory-bounded — never loads a whole stream)
# ---------------------------------------------------------------------------

def _stream_path(root: str, date: str, stream: str) -> str:
    cn = _STREAM_DIR[stream]
    return os.path.join(root, cn, str(date), f"{stream}_{date}.parquet")


def _read_stream(
    root: str,
    date: str,
    stream: str,
    secu_codes: Optional[list[int]] = None,
    columns: Optional[list[str]] = None,
) -> Optional[pd.DataFrame]:
    """Read one parquet stream, filtered to *secu_codes* with column pushdown.

    Returns ``None`` if the stream file is absent, else a (possibly empty) frame.
    """
    path = _stream_path(root, date, stream)
    if not os.path.exists(path):
        log.warning("_read_stream: missing %s stream at %s", stream, path)
        return None
    dataset = ds.dataset(path, format="parquet")
    if columns is not None:
        avail = set(dataset.schema.names)
        columns = [c for c in columns if c in avail]
    filt = None
    if secu_codes is not None:
        filt = ds.field("SecuCode").isin([int(s) for s in secu_codes])
    return dataset.to_table(filter=filt, columns=columns).to_pandas()


# ---------------------------------------------------------------------------
# Cancel frame (from the unified `order` table — both exchanges, no branching)
# ---------------------------------------------------------------------------

_CANCEL_EMPTY_COLS = ["side", "cancel_time", "cancel_qty", "time_int", "latency_ms"]


def _hhmmssmmm_to_ms(t: int) -> int:
    """Decode an ``HHMMSSmmm`` integer to milliseconds-since-midnight.

    Minute/second boundaries are handled correctly — unlike a raw integer
    subtraction of two ``HHMMSSmmm`` values (which over-counts across them).
    """
    t = int(t)
    hh = t // 10_000_000
    mm = (t // 100_000) % 100
    ss = (t // 1_000) % 100
    ms = t % 1_000
    return ((hh * 60 + mm) * 60 + ss) * 1_000 + ms


def read_cancel_frame_parquet(root: str, date: str, stock_code: str) -> pd.DataFrame:
    """Reconstruct the cancel frame for one stock from ``order.OrderType ∈ {-1,-11}``.

    Emits the ``ingest_local.read_cancel_frame`` contract (``side`` ``B``/``S``,
    ``cancel_time`` HHMMSSmmm int, ``cancel_qty``, ``time_int`` alias) **plus a
    real ``latency_ms``** (Track L-c): each cancel is matched to its originating
    add row by ``OrderID`` (100% linkage in the 委托补全 table), and
    ``latency_ms = decoded_ms(cancel) − decoded_ms(add)``.  Unmatched cancels get
    ``NaN`` ``latency_ms`` (excluded downstream).  Empty frame if no cancels.
    """
    secu = stock_code_to_secu(stock_code)
    df = _read_stream(root, date, "order", [secu],
                      columns=["SecuCode", "OrderID", "OrderType", "OrderTime", "Volume"])
    if df is None or df.empty:
        return pd.DataFrame(columns=_CANCEL_EMPTY_COLS)

    otype = pd.to_numeric(df["OrderType"], errors="coerce")
    order_time = pd.to_numeric(df["OrderTime"], errors="coerce").fillna(0).astype("int64")

    # Add-side decoded-ms per OrderID (non-cancel rows) — the self-join key.
    add_mask = ~otype.isin(_CANCEL_TYPES)
    add_ms_by_id: dict = {}
    if add_mask.any():
        adds = pd.DataFrame({"OrderID": df.loc[add_mask, "OrderID"].to_numpy(),
                             "_ms": order_time[add_mask].map(_hhmmssmmm_to_ms).to_numpy()})
        add_ms_by_id = adds.groupby("OrderID")["_ms"].min().to_dict()

    c = df[otype.isin(_CANCEL_TYPES)].copy()
    if c.empty:
        return pd.DataFrame(columns=_CANCEL_EMPTY_COLS)

    c["side"] = pd.to_numeric(c["OrderType"], errors="coerce").map(_CANCEL_SIDE).fillna("U")
    c["cancel_qty"] = pd.to_numeric(c["Volume"], errors="coerce").fillna(0.0)
    c["cancel_time"] = order_time[otype.isin(_CANCEL_TYPES)].to_numpy()
    c["time_int"] = c["cancel_time"]

    cancel_ms = c["cancel_time"].map(_hhmmssmmm_to_ms)
    add_ms = c["OrderID"].map(add_ms_by_id)            # NaN where unmatched
    latency = cancel_ms - add_ms
    c["latency_ms"] = latency.where(latency >= 0)      # drop matched-but-negative as unmatched

    return c[_CANCEL_EMPTY_COLS].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Snapshot cleaning → cleaned-frame contract (same columns as load_local)
# ---------------------------------------------------------------------------

def _clean_snapshot(g: pd.DataFrame, stock_code: str, date: str) -> pd.DataFrame:
    """Map one stock's raw snapshot rows → the canonical cleaned tick frame."""
    df = g.copy()
    df["stock_code"] = stock_code
    df["transaction_date"] = str(date)

    tt = pd.to_numeric(df["TickTime"], errors="coerce").fillna(0).astype("int64")
    hour = tt // 10_000_000
    minute = (tt % 10_000_000) // 100_000
    second = (tt % 100_000) // 1_000
    ms = tt % 1_000
    df["hour"] = hour.astype(int)
    df["minute"] = minute.astype(int)
    df["_tick_int"] = tt

    year, mon, day = int(date[:4]), int(date[4:6]), int(date[6:8])
    df["datetime_utc"] = pd.to_datetime(
        dict(year=year, month=mon, day=day,
             hour=hour, minute=minute, second=second, microsecond=ms * 1000),
        errors="coerce",
    )

    # ×100-decoded price; cumulative volume/turnover are the diff() source.
    df["price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0) / 100.0
    df["volume"] = pd.to_numeric(df["TotalVolume"], errors="coerce").fillna(0.0)
    df["amount"] = pd.to_numeric(df["TotalTurnover"], errors="coerce").fillna(0.0) / 100.0
    df["totalaskvolume"] = pd.to_numeric(df.get("TotalAskVolume", 0.0), errors="coerce").fillna(0.0)
    df["totalbidvolume"] = pd.to_numeric(df.get("TotalBidVolume", 0.0), errors="coerce").fillna(0.0)
    df["weightedaskprice"] = pd.to_numeric(df.get("WeightAskPrice", 0.0), errors="coerce").fillna(0.0) / 100.0
    df["weightedbidprice"] = pd.to_numeric(df.get("WeightBidPrice", 0.0), errors="coerce").fillna(0.0) / 100.0

    # Filter pre-open / bad rows (baseline contract), then temporal sort.
    df = df[(df["price"] > 0) & (df["volume"] >= 0) & (df["amount"] >= 0)]
    df = df.sort_values(by=["stock_code", "transaction_date", "datetime_utc"]).reset_index(drop=True)

    df["tick_volume"] = df["volume"].diff().fillna(0).clip(lower=0)
    df["tick_amount"] = df["amount"].diff().fillna(0).clip(lower=0)
    df["price_change"] = df["price"].diff().fillna(0.0)

    # Reshape flat 10-level book → internal _bid/_ask cols (prices ÷100) → JSON.
    for i in range(1, 11):
        for eng, internal, scale in (
            (f"AskPrice{i}", f"_ask_p{i}", 100.0), (f"AskVolume{i}", f"_ask_v{i}", 1.0),
            (f"BidPrice{i}", f"_bid_p{i}", 100.0), (f"BidVolume{i}", f"_bid_v{i}", 1.0),
        ):
            if eng in df.columns:
                df[internal] = pd.to_numeric(df[eng], errors="coerce").fillna(0.0) / scale

    df["bids"] = _make_book_json(df, side="bid")
    df["asks"] = _make_book_json(df, side="ask")

    drop = (
        [f"_ask_p{i}" for i in range(1, 11)] + [f"_ask_v{i}" for i in range(1, 11)]
        + [f"_bid_p{i}" for i in range(1, 11)] + [f"_bid_v{i}" for i in range(1, 11)]
    )
    df = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    return df


# ---------------------------------------------------------------------------
# Big-order volume (from `deal` Side ∈ {0,1} large prints)
# ---------------------------------------------------------------------------

def _bigorder_maps(
    root: str, date: str, secu_codes: Optional[list[int]]
) -> dict[int, dict[int, float]]:
    """Return ``{secu: {deal_time_int: big_qty}}`` for large real trades (Side∈{0,1})."""
    df = _read_stream(root, date, "deal", secu_codes,
                      columns=["SecuCode", "Side", "Volume", "DealTime"])
    if df is None or df.empty:
        return {}
    side = pd.to_numeric(df["Side"], errors="coerce")
    vol = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0)
    mask = side.isin((0, 1)) & (vol >= BIG_ORDER_THRESHOLD)
    big = df[mask].copy()
    if big.empty:
        return {}
    big["_t"] = pd.to_numeric(big["DealTime"], errors="coerce").fillna(0).astype("int64")
    big["_q"] = pd.to_numeric(big["Volume"], errors="coerce").fillna(0.0)
    out: dict[int, dict[int, float]] = {}
    for secu, grp in big.groupby("SecuCode"):
        agg = grp.groupby("_t")["_q"].sum()
        out[int(secu)] = {int(t): float(q) for t, q in agg.items()}
    return out


def _deal_size_maps(
    root: str, date: str, secu_codes: Optional[list[int]]
) -> dict[int, list[float]]:
    """``{secu: [genuine-trade print volumes]}`` from the ``deal`` stream.

    Mirrors :func:`_bigorder_maps`' read of the same ``逐笔成交`` stream, but keeps
    EVERY genuine print's size (no BIG_ORDER threshold, no time-binning) — the raw
    size distribution feeds :func:`features._trd_size_entropy`. Cancels/auction
    (``Side ∉ {0,1}``) and non-positive volumes are excluded.
    """
    df = _read_stream(root, date, "deal", secu_codes, columns=["SecuCode", "Side", "Volume"])
    if df is None or df.empty:
        return {}
    side = pd.to_numeric(df["Side"], errors="coerce")
    vol = pd.to_numeric(df["Volume"], errors="coerce")
    keep = df[side.isin((0, 1)) & (vol > 0)].copy()
    if keep.empty:
        return {}
    keep["_v"] = pd.to_numeric(keep["Volume"], errors="coerce")
    out: dict[int, list[float]] = {}
    for secu, grp in keep.groupby("SecuCode"):
        out[int(secu)] = grp["_v"].dropna().astype(float).tolist()
    return out


def read_deal_sizes_parquet(root: str, date: str, keys: list[str]) -> dict:
    """Public ``deal_lookup`` builder — ``{(stock_code, date_str): [print volumes]}``.

    The deal-stream mirror of the cancel_lookup pattern: ONE batch ``deal`` read for
    all *keys*. Stocks with no genuine prints map to an empty list (backward-safe).
    """
    secus = [stock_code_to_secu(k) for k in keys] if keys else None
    maps = _deal_size_maps(root, date, secus)
    out: dict = {}
    for k in (keys or []):
        out[(k, str(date))] = maps.get(stock_code_to_secu(k), [])
    return out


# ---------------------------------------------------------------------------
# RS cadence event times (P3.3) — sub-100ms deal/order tick timestamps
# ---------------------------------------------------------------------------

def _deal_time_maps(
    root: str, date: str, secu_codes: Optional[list[int]]
) -> dict[int, list[int]]:
    """``{secu: [genuine-trade DealTime ints]}`` from the ``deal`` stream.

    The cadence sibling of :func:`_deal_size_maps`: same genuine-print filter
    (``Side ∈ {0,1}`` & ``Volume > 0``) but keeps the raw ``DealTime`` HHMMSSmmm
    integer of each print — the true sub-100ms event clock that the snapshot
    ``TickTime`` (~3 s) cannot carry.  Cancels / auction (``Side ∉ {0,1}``) and
    non-positive volumes are excluded.
    """
    df = _read_stream(root, date, "deal", secu_codes, columns=["SecuCode", "Side", "Volume", "DealTime"])
    if df is None or df.empty:
        return {}
    side = pd.to_numeric(df["Side"], errors="coerce")
    vol = pd.to_numeric(df["Volume"], errors="coerce")
    keep = df[side.isin((0, 1)) & (vol > 0)].copy()
    if keep.empty:
        return {}
    keep["_t"] = pd.to_numeric(keep["DealTime"], errors="coerce")
    keep = keep[keep["_t"].notna()]
    out: dict[int, list[int]] = {}
    for secu, grp in keep.groupby("SecuCode"):
        out[int(secu)] = grp["_t"].astype("int64").tolist()
    return out


def _order_time_maps(
    root: str, date: str, secu_codes: Optional[list[int]]
) -> dict[int, list[int]]:
    """``{secu: [OrderTime ints]}`` from the ``order`` (委托补全) stream.

    Keeps EVERY order event's ``OrderTime`` HHMMSSmmm integer (both adds and
    cancels — the full order-arrival cadence).  Non-numeric times are dropped.
    """
    df = _read_stream(root, date, "order", secu_codes, columns=["SecuCode", "OrderTime"])
    if df is None or df.empty:
        return {}
    t = pd.to_numeric(df["OrderTime"], errors="coerce")
    keep = df[t.notna()].copy()
    if keep.empty:
        return {}
    keep["_t"] = t[t.notna()]
    out: dict[int, list[int]] = {}
    for secu, grp in keep.groupby("SecuCode"):
        out[int(secu)] = grp["_t"].astype("int64").tolist()
    return out


def read_deal_times_parquet(root: str, date: str, keys: list[str]) -> dict:
    """Public RS-cadence builder — ``{(stock_code, date_str): [DealTime ints]}``.

    ONE batch ``deal`` read for all *keys* (mirrors :func:`read_deal_sizes_parquet`).
    Stocks with no genuine prints map to an empty list (backward-safe → RS falls
    back to the snapshot clock).  Selected via ``config.RS_CADENCE_SOURCE == "deal"``.
    """
    secus = [stock_code_to_secu(k) for k in keys] if keys else None
    maps = _deal_time_maps(root, date, secus)
    return {(k, str(date)): maps.get(stock_code_to_secu(k), []) for k in (keys or [])}


def read_order_times_parquet(root: str, date: str, keys: list[str]) -> dict:
    """Public RS-cadence builder — ``{(stock_code, date_str): [OrderTime ints]}``.

    ONE batch ``order`` read for all *keys*.  Stocks with no order rows map to an
    empty list (backward-safe).  Selected via ``config.RS_CADENCE_SOURCE == "order"``.
    """
    secus = [stock_code_to_secu(k) for k in keys] if keys else None
    maps = _order_time_maps(root, date, secus)
    return {(k, str(date)): maps.get(stock_code_to_secu(k), []) for k in (keys or [])}


def _assign_bigorder(tick_int: pd.Series, big_map: dict[int, float]) -> pd.Series:
    """Assign each large print to the snapshot tick covering its time (left-exclusive).

    Only the per-stock-day **sum** matters downstream (``bigorder_volume_pct``);
    prints after the last tick are folded into the last row to preserve the total.
    """
    if not big_map or len(tick_int) == 0:
        return pd.Series(0.0, index=tick_int.index)
    big_times = sorted(big_map)
    result, prev = [], -1
    for st in tick_int:
        result.append(float(sum(big_map[t] for t in big_times if prev < t <= int(st))))
        prev = int(st)
    leftover = sum(big_map[t] for t in big_times if t > prev)
    if leftover and result:
        result[-1] += float(leftover)
    return pd.Series(result, index=tick_int.index)


# ---------------------------------------------------------------------------
# Public API — load_parquet (mirrors ingest_local.load_local contract)
# ---------------------------------------------------------------------------

def load_parquet(
    root: str,
    date: str,
    keys: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Read the parquet corpus and return a cleaned, multi-stock tick frame.

    The returned frame carries the **same column contract** as
    ``ingest_local.load_local`` (every column ``features.compute_daily_features``
    reads). ``cb_available`` is ``1.0`` for stocks with cancels in ``order``.

    Parameters
    ----------
    root:  corpus root (e.g. ``"data/202606"`` or a tiny fixture dir).
    date:  trading date ``YYYYMMDD``.
    keys:  stock codes to load (``NNNNNN.XX``). **Strongly recommended** — the real
           corpus is ~13 GB/day; ``None`` loads every stock (avoid on real data).
    """
    date = str(date)
    secu_codes = [stock_code_to_secu(k) for k in keys] if keys else None

    snap = _read_stream(root, date, "snapshot", secu_codes, columns=_SNAPSHOT_COLS)
    if snap is None or snap.empty:
        log.warning("load_parquet: no snapshot rows under %s/%s (keys=%s)", root, date, keys)
        return pd.DataFrame()

    # Cancel availability per stock — one filtered `order` read for all keys.
    order = _read_stream(root, date, "order", secu_codes, columns=["SecuCode", "OrderType"])
    cancel_secus: set[int] = set()
    if order is not None and not order.empty:
        ot = pd.to_numeric(order["OrderType"], errors="coerce")
        cancel_secus = set(order.loc[ot.isin(_CANCEL_TYPES), "SecuCode"].astype("int64").tolist())

    big_maps = _bigorder_maps(root, date, secu_codes)

    frames = []
    for secu, g in snap.groupby("SecuCode"):
        secu = int(secu)
        code = secu_to_stock_code(secu)
        sf = _clean_snapshot(g, code, date)
        if sf.empty:
            continue
        sf["cb_available"] = 1.0 if secu in cancel_secus else 0.0
        sf["tick_bigordervolume"] = _assign_bigorder(sf.pop("_tick_int"), big_maps.get(secu, {}))
        frames.append(sf)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(by=["stock_code", "transaction_date", "datetime_utc"]).reset_index(drop=True)
    return out
