"""Aggregation: raw ticks -> per-(stock, day) feature matrix.

The minimal scored unit is (stock_code, transaction_date) (baseline-guide.md L265).
This module groups the cleaned tick stream by that key and reduces each group to one
daily feature vector via `features.compute_daily_features`.

The `hh` Beijing-hour window is the seam for finer intraday aggregation: PI features
already consume `hour`/`minute` inside the daily reduction, so window->daily rollup
is handled there. Should later work need explicit per-hour vectors before the daily
reduce, `compute_window_features` is the place to add it without touching callers.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.features import compute_daily_features

log = logging.getLogger(__name__)


def build_feature_matrix(df: pd.DataFrame, has_cancel_table: bool = False) -> pd.DataFrame:
    """Reduce the cleaned tick frame to one row per (stock_code, transaction_date)."""
    rows = []
    keys = []
    for (code, date), group in df.groupby(["stock_code", "transaction_date"], sort=True):
        feat = compute_daily_features(group, has_cancel_table=has_cancel_table)
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
