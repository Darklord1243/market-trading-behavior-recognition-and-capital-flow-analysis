"""Aggregation: raw ticks -> per-(stock, day) feature matrix.

The minimal scored unit is (stock_code, transaction_date) (baseline-guide.md L265).
This module groups the cleaned tick stream by that key and reduces each group to one
daily feature vector via `features.compute_daily_features`.

The `hh` Beijing-hour window is the seam for finer intraday aggregation: PI features
already consume `hour`/`minute` inside the daily reduction, so window->daily rollup
is handled there. Should later work need explicit per-hour vectors before the daily
reduce, `compute_window_features` is the place to add it without touching callers.

Cancel data plumbing (Track L-b)
---------------------------------
``build_feature_matrix`` accepts an optional ``cancel_lookup`` mapping
``(stock_code, date) -> cancel_df`` produced by ``ingest_local.read_cancel_frame``.
When present, the per-(stock, day) cancel frame is passed into
``compute_daily_features`` so real CB feature values are computed.
The xlsx / snapshot path passes no ``cancel_lookup`` → backward-compatible.

Deal-size plumbing (Feature B.2)
----------------------------------
``build_feature_matrix`` also accepts an optional ``deal_lookup`` mapping
``(stock_code, date) -> [print volumes]`` produced by
``ingest_parquet.read_deal_sizes_parquet``. When present, the per-(stock, day) volume
list is passed into ``compute_daily_features`` as ``deal_volumes`` so the
``trd_size_entropy`` feature is computed. The xlsx / snapshot path passes no
``deal_lookup`` → backward-compatible (``trd_size_entropy`` stays 0.0).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.features import compute_daily_features

log = logging.getLogger(__name__)


def build_feature_matrix(
    df: pd.DataFrame,
    has_cancel_table: bool = False,
    cancel_lookup: Optional[dict] = None,
    deal_lookup: Optional[dict] = None,        # NEW (B.2): {(code, date): [print volumes]}
) -> pd.DataFrame:
    """Reduce the cleaned tick frame to one row per (stock_code, transaction_date).

    Parameters
    ----------
    df:
        Cleaned, multi-stock tick frame (output of ``ingest.load_raw`` or
        ``ingest_local.load_local``).
    has_cancel_table:
        ``True`` when the source data contains cancel events (local CSV path).
        Controls whether CB features are flagged as available.
    cancel_lookup:
        Optional dict mapping ``(stock_code, date_str)`` →
        ``pd.DataFrame`` of cancel events (columns: ``side``, ``cancel_time``,
        ``cancel_qty``).  Produced by calling ``ingest_local.read_cancel_frame``
        for each stock-day.  When ``None`` (default), CB values are 0.0.
    deal_lookup:
        Optional dict mapping ``(stock_code, date_str)`` → ``[print volumes]``
        (list of genuine-trade Volume floats). Produced by calling
        ``ingest_parquet.read_deal_sizes_parquet`` for the day's panel. When
        ``None`` (default — xlsx/snapshot path), ``trd_size_entropy`` is 0.0.
    """
    rows = []
    keys = []
    for (code, date), group in df.groupby(["stock_code", "transaction_date"], sort=True):
        cancel_df = None
        if cancel_lookup is not None:
            cancel_df = cancel_lookup.get((code, str(date)))
        deal_volumes = None
        if deal_lookup is not None:
            deal_volumes = deal_lookup.get((code, str(date)))
        feat = compute_daily_features(
            group,
            has_cancel_table=has_cancel_table,
            cancel_df=cancel_df,
            deal_volumes=deal_volumes,         # NEW (B.2)
        )
        rows.append(feat)
        keys.append((code, date))

    matrix = pd.DataFrame(rows)
    idx = pd.MultiIndex.from_tuples(keys, names=["stock_code", "transaction_date"])
    matrix.index = idx
    log.info("feature matrix: %d (stock, day) rows x %d features",
             matrix.shape[0], matrix.shape[1])
    return matrix


def compute_window_features(group: pd.DataFrame) -> pd.DataFrame:
    """Seam: per-`hh` window vectors for one (stock, day) group.

    Not yet consumed by the daily reduce (PI features fold the windows in directly).
    Kept as an explicit hook so window->daily rollup can be made first-class later.
    """
    # TODO(window-rollup): emit one feature row per Beijing hour, then reduce.
    return group.groupby("hour", sort=True).size().rename("n_ticks").to_frame()
