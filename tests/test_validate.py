"""Tests for src/validate.py — offline weighted-F1 proxy scorer.

All tests use **inline synthetic DataFrames** — never load
tests/fixtures/validation_labels.csv (which contains EXAMPLE-only rows).

This scorer is offline / post-hoc.  It must never be wired into main.py or
any inference path (compliance #1: no post-close data in features).
"""

from __future__ import annotations

import pandas as pd
import pytest
from sklearn.metrics import f1_score

from src.validate import weighted_f1


# ---------------------------------------------------------------------------
# Shared tiny fixture (3 classes, matching keys in pred and truth)
# ---------------------------------------------------------------------------

def _make_pred_truth():
    """Return (pred_df, truth_df) sharing (stock_code, transaction_date) keys.

    Classes present: 游资, 量化, 散户 — all three, so weighted F1 is non-trivial.
    5 rows total.  pred is intentionally imperfect (not all correct).
    """
    keys = {
        "stock_code":       ["600000.SH", "000001.SZ", "600519.SH", "000858.SZ", "601318.SH"],
        "transaction_date": ["20260101",   "20260101",   "20260102",   "20260102",   "20260103"],
    }
    pred_df = pd.DataFrame({
        **keys,
        "capital_type": ["游资", "量化", "散户", "游资", "量化"],
    })
    truth_df = pd.DataFrame({
        **keys,
        "capital_type": ["游资", "散户", "散户", "游资", "量化"],
    })
    return pred_df, truth_df


# ---------------------------------------------------------------------------
# V.1  weighted_f1 matches sklearn (the canonical acceptance test)
# ---------------------------------------------------------------------------

def test_weighted_f1_matches_sklearn():
    """weighted_f1(pred, truth)["weighted_f1"] == sklearn weighted F1."""
    pred_df, truth_df = _make_pred_truth()
    result = weighted_f1(pred_df, truth_df)

    # Ground-truth oracle via sklearn on the SAME aligned rows
    merged = pred_df.merge(truth_df, on=["stock_code", "transaction_date"],
                           suffixes=("_pred", "_truth"))
    y_pred = merged["capital_type_pred"].tolist()
    y_true = merged["capital_type_truth"].tolist()

    expected = f1_score(y_true, y_pred, average="weighted")
    assert result["weighted_f1"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Inner-join: only co-present (stock, day) pairs are scored
# ---------------------------------------------------------------------------

def test_inner_join_only_scores_common_keys():
    """Rows not in both pred and truth are dropped; n reflects only the join."""
    pred_df = pd.DataFrame({
        "stock_code":       ["A", "B", "C"],
        "transaction_date": ["20260101", "20260101", "20260101"],
        "capital_type":     ["游资", "量化", "散户"],
    })
    truth_df = pd.DataFrame({
        "stock_code":       ["A", "D"],          # B, C not in truth; D not in pred
        "transaction_date": ["20260101", "20260101"],
        "capital_type":     ["游资", "游资"],
    })
    result = weighted_f1(pred_df, truth_df)
    # Only (A, 20260101) is common → n == 1
    assert result["n"] == 1
    # Perfect prediction for the one common row → weighted_f1 == 1.0
    assert result["weighted_f1"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Edge: no common keys → weighted_f1 == 0.0, n == 0 (documented behavior)
# ---------------------------------------------------------------------------

def test_empty_join_is_zero():
    """No overlapping (stock, date) keys → weighted_f1=0.0, n=0; no exception."""
    pred_df = pd.DataFrame({
        "stock_code":       ["X"],
        "transaction_date": ["20260101"],
        "capital_type":     ["游资"],
    })
    truth_df = pd.DataFrame({
        "stock_code":       ["Y"],
        "transaction_date": ["20260101"],
        "capital_type":     ["量化"],
    })
    result = weighted_f1(pred_df, truth_df)
    assert result["n"] == 0
    assert result["weighted_f1"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Return structure: per-class P/R/F1/support present for all 3 classes
# ---------------------------------------------------------------------------

def test_per_class_keys_present():
    """Result dict contains 'per_class' with all three capital_type labels."""
    pred_df, truth_df = _make_pred_truth()
    result = weighted_f1(pred_df, truth_df)

    assert "per_class" in result
    for label in ("游资", "量化", "散户"):
        assert label in result["per_class"], f"Missing per-class entry for {label!r}"
        entry = result["per_class"][label]
        for key in ("precision", "recall", "f1", "support"):
            assert key in entry, f"Missing key {key!r} in per_class[{label!r}]"


def test_per_class_support_sums_to_n():
    """Sum of per-class support equals n (total aligned rows)."""
    pred_df, truth_df = _make_pred_truth()
    result = weighted_f1(pred_df, truth_df)
    total_support = sum(v["support"] for v in result["per_class"].values())
    assert total_support == result["n"]
