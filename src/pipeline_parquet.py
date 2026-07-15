"""Shared parquet pipeline helper — Phase 6.1.

Extracted from scripts/validate_offline._build_parquet_matrix so that main.py
and the offline harness share one implementation without importing each other.

Public API
----------
load_universe_codes(path)
    Load exchange-suffixed stock codes from a CSV or xlsx file.

resolve_default_universe(transaction_date, *, explicit=None, ...)
    Prefer ``samples/B_board/stock_sample_{transaction_date}.xlsx`` when present
    (Board B trading-day naming, platform rename of 2026-07-15); else fall back
    to ``samples/stock-samples.xlsx``.

build_feature_matrix_for_panel(root, date, stock_codes)
    Build a feature matrix for the given panel.  Missing codes are omitted with
    a WARNING (not fatal) — the caller receives rows only for stocks that have
    parquet data.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

log = logging.getLogger(__name__)

# Column names accepted in universe files (first match wins).
_UNIVERSE_CODE_COLS = ("股票代码", "stock_code")

# Default paths for Board B daily samples vs A-board static list.
_DEFAULT_B_BOARD_DIR = os.path.join("samples", "B_board")
_DEFAULT_A_BOARD_UNIVERSE = os.path.join("samples", "stock-samples.xlsx")
_B_BOARD_SAMPLE_FMT = "stock_sample_{date}.xlsx"

# ---------------------------------------------------------------------------
# Universe loader
# ---------------------------------------------------------------------------

def resolve_default_universe(
    date: str,
    *,
    explicit: str | None = None,
    sample_date: str | None = None,
    b_board_dir: str = _DEFAULT_B_BOARD_DIR,
    a_board_fallback: str = _DEFAULT_A_BOARD_UNIVERSE,
) -> str:
    """Pick the universe file for a parquet run.

    Precedence
    ----------
    1. ``explicit`` (CLI ``--universe``) when provided
    2. ``{b_board_dir}/stock_sample_{sample_date}.xlsx`` when that file exists,
       where ``sample_date`` defaults to ``date`` itself (Board B: since the
       platform rename of 2026-07-15, the filename uses the L2 **trading** day,
       not the release day)
    3. ``a_board_fallback`` (A-board static list)

    Parameters
    ----------
    date : L2 / ``transaction_date`` ``YYYYMMDD`` (CLI ``--date``).
    explicit : Path from ``--universe``, or ``None`` to auto-resolve.
    sample_date : Optional filename-stem override (use only for odd platform slots).
    b_board_dir : Directory holding dated Board B sample workbooks.
    a_board_fallback : Static A-board universe path used when B-board file absent.

    Returns
    -------
    Path string to the chosen universe file (existence of the fallback is not
    checked here — ``load_universe_codes`` will raise if missing).

    Notes
    -----
    Example: ``--date 20260713`` → look for ``stock_sample_20260713.xlsx``.
    Before 2026-07-15 the platform named samples by **release** day (T for
    trading day T−1) and this resolver used the next trading day; samples in
    the repo were renamed to trading-day stems when the platform switched.
    """
    if explicit:
        return explicit

    if not date:
        raise ValueError("date is required to resolve a default universe path")

    stem = sample_date or date
    b_path = os.path.join(b_board_dir, _B_BOARD_SAMPLE_FMT.format(date=stem))
    if os.path.isfile(b_path):
        log.info(
            "universe auto-resolve: Board B sample %s "
            "(transaction_date=%s, sample_stem=%s)",
            b_path,
            date,
            stem,
        )
        return b_path

    log.info(
        "universe auto-resolve: no %s (transaction_date=%s sample_stem=%s) "
        "— falling back to %s",
        b_path,
        date,
        stem,
        a_board_fallback,
    )
    return a_board_fallback


def load_universe_codes(path: str) -> list[str]:
    """Load exchange-suffixed stock codes from a CSV or xlsx universe file.

    Recognised column names: ``股票代码`` or ``stock_code`` (first found wins).
    Empty strings and ``"nan"`` are filtered out; duplicates are deduplicated.

    Parameters
    ----------
    path : Path to a CSV or xlsx file.

    Returns
    -------
    Sorted list of unique stock codes (e.g. ``["000001.SZ", "600000.SH"]``).

    Raises
    ------
    FileNotFoundError  if the file does not exist.
    ValueError         if neither expected column is found.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"universe file not found: {path}")

    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, encoding="utf-8", dtype=str)

    col = next((c for c in _UNIVERSE_CODE_COLS if c in df.columns), None)
    if col is None:
        raise ValueError(
            f"universe file {path!r} must have one of {_UNIVERSE_CODE_COLS}; "
            f"got {list(df.columns)}"
        )
    # fillna("") before astype(str): pandas >=3.0 no longer stringifies NaN to
    # "nan", so a blank universe cell would otherwise survive as a float NaN and
    # crash sorted() with a float-vs-str TypeError. Coerce blanks to "" up front.
    codes = df[col].fillna("").astype(str).str.strip()
    codes = codes[codes.ne("") & codes.ne("nan")]
    return sorted(codes.unique().tolist())


# ---------------------------------------------------------------------------
# Feature matrix builder (shared with validate_offline)
# ---------------------------------------------------------------------------

def build_feature_matrix_for_panel(
    root: str,
    date: str,
    stock_codes: list[str],
) -> pd.DataFrame:
    """Build a feature matrix for *stock_codes* from the parquet corpus.

    Mirrors ``validate_offline._build_parquet_matrix`` but accepts the full
    competition universe directly (no harness ``labeled_keys`` concept).

    Missing-stock policy
    --------------------
    Stocks whose snapshot rows are absent in the parquet corpus are silently
    omitted from the returned matrix.  The caller receives rows only for stocks
    with data.  A WARNING is logged with the missing-count so operators can
    audit.

    Parameters
    ----------
    root        : Parquet corpus root (e.g. ``"data/202606"``).
    date        : Trading date ``YYYYMMDD``.
    stock_codes : Codes to load (``NNNNNN.XX`` format).

    Returns
    -------
    Feature matrix (MultiIndex ``(stock_code, transaction_date)``).  Empty
    DataFrame if no data is available.
    """
    from config import RS_CADENCE_SOURCE
    from src import aggregate
    from src.ingest_parquet import (
        load_parquet,
        read_cancel_frames_parquet,
        read_deal_sizes_parquet,
        read_deal_times_parquet,           # NEW (P3.3)
        read_order_times_parquet,          # NEW (P3.3)
        secu_to_stock_code,
        stock_code_to_secu,
    )

    if not stock_codes:
        log.warning("build_feature_matrix_for_panel: empty stock_codes list")
        return pd.DataFrame()

    df = load_parquet(root, date, keys=stock_codes)
    if df is None or df.empty:
        log.warning(
            "build_feature_matrix_for_panel: no snapshot data for date=%s root=%s codes=%s",
            date, root, stock_codes[:5],
        )
        return pd.DataFrame()

    # Determine which codes actually had snapshot rows (others are missing).
    present_codes: set[str] = set(df["stock_code"].astype(str).unique().tolist())
    missing = [c for c in stock_codes if c not in present_codes]
    if missing:
        log.warning(
            "build_feature_matrix_for_panel: %d/%d codes missing parquet data for %s: %s",
            len(missing), len(stock_codes), date, missing[:10],
        )

    present = list(present_codes)

    # Build cancel_lookup for present codes only (avoid wasted reads) — ONE batch
    # `order` read for all codes, not a per-stock rescan (Slice 5C gate-perf fix).
    try:
        cancel_lookup = read_cancel_frames_parquet(root, date, present)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "build_feature_matrix_for_panel: batch cancel read failed %s: %s",
            date, exc,
        )
        cancel_lookup = {}

    deal_lookup = read_deal_sizes_parquet(root, date, present)

    # NEW (P3.3): RS cadence event-time lookup, selected by config (snapshot → None).
    rs_timestamps_lookup = None
    if RS_CADENCE_SOURCE == "deal":
        rs_timestamps_lookup = read_deal_times_parquet(root, date, present)
    elif RS_CADENCE_SOURCE == "order":
        rs_timestamps_lookup = read_order_times_parquet(root, date, present)

    return aggregate.build_feature_matrix(
        df,
        has_cancel_table=True,
        cancel_lookup=cancel_lookup,
        deal_lookup=deal_lookup,
        rs_timestamps_lookup=rs_timestamps_lookup,
    )
