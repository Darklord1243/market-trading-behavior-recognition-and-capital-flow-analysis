"""Tests for src/normalize.py — cross-sample rank normalization.

All tests use synthetic matrices. The official fixture (n=1) normalizes to all-0.5
(degenerate single-row case) and cannot prove rank behavior; see LIS §6 Phase 1.
"""

import pandas as pd
import pytest
from src.normalize import normalize_matrix


def test_ranks_to_unit_interval():
    """Basic rank normalization: min->0, max->1; cb_available passes through."""
    m = pd.DataFrame({"a": [10.0, 20.0, 30.0, 40.0], "cb_available": [0, 0, 0, 1]})
    out = normalize_matrix(m)
    assert list(out["a"]) == [0.0, 1 / 3, 2 / 3, 1.0]
    assert list(out["cb_available"]) == [0, 0, 0, 1]  # flag passes through untouched


def test_single_row_is_neutral():
    """A 1-row matrix -> every normalizable numeric column -> 0.5 (neutral)."""
    m = pd.DataFrame(
        {
            "a": [99.0],
            "b": [0.0],
            "cb_available": [0.0],
            "n_ticks": [100.0],
        }
    )
    out = normalize_matrix(m)
    assert out["a"].iloc[0] == 0.5
    assert out["b"].iloc[0] == 0.5
    # excluded columns pass through unchanged
    assert out["cb_available"].iloc[0] == 0.0
    assert out["n_ticks"].iloc[0] == 100.0


def test_constant_column_is_neutral():
    """A constant column (all equal values, n>1) -> 0.5 (no information)."""
    m = pd.DataFrame(
        {
            "a": [5.0, 5.0, 5.0],
            "b": [1.0, 2.0, 3.0],
        }
    )
    out = normalize_matrix(m)
    assert list(out["a"]) == [0.5, 0.5, 0.5]
    # non-constant column still normalized normally
    assert list(out["b"]) == [0.0, 0.5, 1.0]


def test_n_ticks_passes_through():
    """n_ticks is excluded from normalization and passes through unchanged."""
    m = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0],
            "n_ticks": [10.0, 20.0, 30.0],
        }
    )
    out = normalize_matrix(m)
    assert list(out["n_ticks"]) == [10.0, 20.0, 30.0]
    assert list(out["a"]) == [0.0, 0.5, 1.0]


def test_non_numeric_columns_pass_through():
    """Non-numeric columns (e.g. string labels) are left unchanged."""
    m = pd.DataFrame(
        {
            "score": [10.0, 20.0, 30.0],
            "label": ["x", "y", "z"],
        }
    )
    out = normalize_matrix(m)
    assert list(out["label"]) == ["x", "y", "z"]
    assert list(out["score"]) == [0.0, 0.5, 1.0]


def test_same_index_and_columns():
    """Output preserves the same index and column set as input."""
    m = pd.DataFrame(
        {"a": [3.0, 1.0, 2.0], "b": [100.0, 200.0, 150.0]},
        index=[10, 20, 30],
    )
    out = normalize_matrix(m)
    assert list(out.index) == [10, 20, 30]
    assert list(out.columns) == list(m.columns)


def test_ties_use_average_rank():
    """Tied values use average rank (rank method='average')."""
    # Two equal values at positions 0,1 -> ranks 1.5,1.5 out of 3
    # normalized: (1.5 - 1) / (3 - 1) = 0.25
    m = pd.DataFrame({"a": [5.0, 5.0, 10.0]})
    out = normalize_matrix(m)
    assert out["a"].iloc[0] == pytest.approx(0.25)
    assert out["a"].iloc[1] == pytest.approx(0.25)
    assert out["a"].iloc[2] == pytest.approx(1.0)
