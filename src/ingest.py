"""Raw Level-2 reader.

Ports the baseline `load_and_preprocess()` (baseline-guide.md L309-328) into a
module: read the 65-column raw L2 snapshot stream, normalise time, clean, sort,
and convert the cumulative-intraday fields to per-tick increments via diff().

Critical documented behaviours preserved from the baseline:
  * `date` is UTC epoch-ms; the Beijing trading hour lives in `hh` (8-16). Session
    windows MUST use `hh`, never `date.dt.hour` (which is UTC 0-8 -> PI all-zero).
  * After sorting by (stock_code, transaction_date, datetime), the cumulative
    fields are monotonic, so `.diff().fillna(0).clip(lower=0)` yields valid ticks.

Nothing here reads a pre-computed feature file — features are recomputed from raw
L2 downstream (audit-contract requirement, brief §9).
"""

from __future__ import annotations

import glob
import json
import logging
from typing import Any

import pandas as pd

from config import CUMULATIVE_FIELDS, RAW_L2_N_COLS

log = logging.getLogger(__name__)

# Columns that, if present, indicate a genuine tick-cancellation table is attached
# (as opposed to the snapshot-only stream where cancel info is unreconstructable).
CANCEL_TABLE_HINT_COLS = (
    "cb_cancel_order_count",
    "cancel_count_all",
    "cancelvolume",
    "cancelprice",
    "canceltime",
)


def load_raw(input_glob: str) -> pd.DataFrame:
    """Read one or more raw L2 xlsx files into a single cleaned, sorted frame.

    Accepts a literal path or a glob (e.g. ``data/*.xlsx``). Relative paths only —
    the caller is responsible for keeping paths relative for audit compliance.
    """
    paths = sorted(glob.glob(input_glob))
    if not paths:
        # A literal path that exists but doesn't glob (e.g. has no wildcard).
        paths = [input_glob]

    frames = []
    for p in paths:
        log.info("reading raw L2 file: %s", p)
        frames.append(pd.read_excel(p, engine="openpyxl"))
    df = pd.concat(frames, ignore_index=True)

    if df.shape[1] != RAW_L2_N_COLS:
        log.warning(
            "raw L2 has %d columns (expected %d) — self-sourced schema may differ; "
            "aligning by name, not position",
            df.shape[1],
            RAW_L2_N_COLS,
        )

    df = _normalise_and_clean(df)
    return df


def _normalise_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Time normalisation, renaming, filtering, sorting, cumulative->tick.

    Faithful port of baseline `load_and_preprocess()` plus per-group tick diffs.
    """
    df = df.copy()

    # --- canonical keys ---
    df["transaction_date"] = df["dt"].astype(str)                     # YYYYMMDD string
    df["datetime"] = pd.to_datetime(df["date"], unit="ms")            # UTC epoch-ms
    df["hour"] = df["hh"]                                             # Beijing hour (8-16)
    df["minute"] = df["datetime"].dt.minute                          # offset is constant
    df = df.rename(columns={"symbol": "stock_code"})

    # --- cleaning: drop obviously invalid rows (baseline filter) ---
    df = df[(df["price"] > 0) & (df["volume"] >= 0) & (df["amount"] >= 0)]

    # --- temporal sort so cumulative fields are monotonic per group ---
    df = df.sort_values(by=["stock_code", "transaction_date", "datetime"])
    df = df.reset_index(drop=True)

    # --- cumulative -> per-tick increments (Finding 1) ---
    grp = df.groupby(["stock_code", "transaction_date"], sort=False)
    for col in CUMULATIVE_FIELDS:
        if col in df.columns:
            df["tick_" + col] = grp[col].diff().fillna(0).clip(lower=0)
    # price change drives aggressor-side inference downstream (AP features)
    df["price_change"] = grp["price"].diff()

    return df


def detect_cancel_table(df: pd.DataFrame) -> bool:
    """Return True iff a usable tick-cancellation table is present.

    Snapshot-only data (the official fixture) carries no cancel detail —
    `bidaskrate`/`bidaskdifference` are identically 0 and none of the cancel
    hint columns exist. Downstream CB features degrade gracefully (see features.py).
    """
    present = [c for c in CANCEL_TABLE_HINT_COLS if c in df.columns]
    if present:
        # Hint columns exist; require at least one to carry signal (non-all-zero).
        for c in present:
            try:
                if df[c].fillna(0).abs().sum() > 0:
                    return True
            except TypeError:
                # non-numeric cancel column (e.g. timestamps) — treat presence as signal
                return True
    return False


def parse_book_json(raw: Any) -> list[dict]:
    """Parse a nested-JSON `bids`/`asks` cell into a list of level dicts.

    Each level looks like ``{"price": .., "volume": .., "order": [..],
    "bigOrderPercent": ..}``; deeper levels often omit `order`/`bigOrderPercent`.
    Returns [] on any malformed / missing cell rather than raising.
    """
    if raw is None or (isinstance(raw, float)):
        return []
    if isinstance(raw, (list, dict)):
        return raw if isinstance(raw, list) else [raw]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else [parsed]
