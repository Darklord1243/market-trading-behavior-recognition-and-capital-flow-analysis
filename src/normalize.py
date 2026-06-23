"""Cross-sample (within-day) rank normalization to [0,1].

Intraday-only: uses only the same-day cross-section of stocks, never future data
or external lookups (compliance #1).  This module contains no stock-specific
constants (compliance #2) and no call to any inference-time LLM (compliance #4).

Public API
----------
normalize_matrix(matrix) -> pd.DataFrame
    Rank-normalize each numeric column across rows (stocks) to [0, 1].
    Columns listed in EXCLUDE are passed through unchanged.
"""

from __future__ import annotations

import pandas as pd

# Columns excluded from rank normalization: flags/counts whose raw values
# are meaningful across the cross-section and should not be replaced.
# limit_seal_*_ratio are raw [0,1] proportions whose rule thresholds operate
# on the raw seal fraction (e.g. LIMIT_SEAL_MIN=0.5 means "majority of ticks
# were at the limit price").  Rank-normalizing them would destroy this absolute
# meaning — a stock sealing 80% of the session could rank 0.5 on a day when
# every name has some seal fraction, making the threshold meaningless.
EXCLUDE: frozenset[str] = frozenset({
    "cb_available",
    "n_ticks",
    "limit_seal_up_ratio",
    "limit_seal_down_ratio",
})


def normalize_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    """Rank-normalize each numeric column to [0, 1] across the row cross-section.

    Formula per column (n > 1, non-constant):
        r = rank(method="average")          # 1-based, ties → average rank
        normalized = (r - 1) / (n - 1)     # maps [1, n] → [0, 1]

    Special cases:
    - n <= 1          : every normalizable column → 0.5 (neutral; single stock
                        cannot be ranked against itself).
    - Constant column : all rows → 0.5 (no cross-sectional information).
    - Excluded cols   : cb_available, n_ticks pass through unchanged.
    - Non-numeric     : pass through unchanged.

    Parameters
    ----------
    matrix : pd.DataFrame
        Daily cross-section matrix (rows = stocks, columns = features).

    Returns
    -------
    pd.DataFrame
        Same index and columns as input; numeric non-excluded columns replaced
        with rank-normalized values in [0, 1].
    """
    out = matrix.copy()
    n = len(out)

    for col in out.select_dtypes("number").columns:
        if col in EXCLUDE:
            continue
        if n <= 1:
            out[col] = 0.5
            continue
        r = out[col].rank(method="average")
        normalized = (r - 1.0) / (n - 1.0)
        if normalized.nunique() == 1:  # constant column after ranking
            out[col] = 0.5
        else:
            out[col] = normalized

    return out
