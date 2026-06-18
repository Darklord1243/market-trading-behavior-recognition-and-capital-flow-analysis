"""Tests for scripts/validate_offline.py — offline Track V proxy-F1 harness.

All tests use **inline synthetic DataFrames / temp CSVs** — never load
tests/fixtures/validation_labels.csv (which contains only EXAMPLE rows
and whose content is not the concern of this test file).

The local-source smoke test is guarded by pytest.mark.skipif on the presence
of tests/fixtures/local_l2_tiny so CI never breaks when the fixture is absent.

Compliance: this test file does NOT import validate_offline from any
src/ inference module; it imports only from scripts/.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import helper: load scripts/validate_offline.py without requiring scripts/
# to be a package (avoids polluting src/ import namespace).
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent
_HARNESS_PATH = _ROOT / "scripts" / "validate_offline.py"


def _import_harness():
    """Dynamically import scripts/validate_offline as a module."""
    spec = importlib.util.spec_from_file_location("validate_offline", _HARNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# V4.1 — EXAMPLE / zero-confidence rows are dropped by load_truth_labels
# ---------------------------------------------------------------------------

def test_example_rows_are_dropped():
    """load_truth_labels drops rows where confidence==0.0 OR source starts with EXAMPLE.

    Given 2 EXAMPLE rows + 2 real rows, the filtered result contains only the 2
    real rows.
    """
    harness = _import_harness()

    data = {
        "stock_code":        ["EXAMPLE.SZ", "EXAMPLE.SH", "000001.SZ", "600000.SH"],
        "transaction_date":  ["20260611",   "20260611",   "20260611",   "20260611"],
        "capital_type":      ["游资",         "量化",        "游资",        "散户"],
        "capital_intention": ["买入",         "",           "买入",        "卖出"],
        "source":            ["EXAMPLE — placeholder",
                              "example-lower-case",
                              "https://real-source.com",
                              "https://another-real.com"],
        "confidence":        [0.0,           0.0,          0.8,          0.6],
        "notes":             ["ex1",         "ex2",        "real1",      "real2"],
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        df.to_csv(f, index=False)
        tmp_path = f.name

    try:
        result = harness.load_truth_labels(tmp_path)
    finally:
        os.unlink(tmp_path)

    assert len(result) == 2, f"Expected 2 real rows, got {len(result)}"
    # All returned rows should have confidence > 0 and source not starting with EXAMPLE
    assert (result["confidence"] > 0).all(), "Some returned rows have confidence == 0"
    assert not result["source"].str.upper().str.startswith("EXAMPLE").any(), \
        "Some returned rows still have EXAMPLE source"


# ---------------------------------------------------------------------------
# V4.2 (no separate test — impl verified by V4.1 passing above)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# V4.3 — pred CSV path scores via weighted_f1 (not a reimplementation)
# ---------------------------------------------------------------------------

def test_pred_csv_path_scores_via_weighted_f1():
    """Harness join layer returns same weighted_f1/n as calling validate.weighted_f1
    directly on the filtered frames, proving the harness calls the real scorer.
    """
    harness = _import_harness()
    from src.validate import weighted_f1

    # 3-row truth CSV (all real/scorable — confidence > 0, no EXAMPLE source)
    truth_data = {
        "stock_code":        ["000001.SZ", "600000.SH", "000858.SZ"],
        "transaction_date":  ["20260611",  "20260611",  "20260611"],
        "capital_type":      ["游资",        "量化",        "散户"],
        "capital_intention": ["买入",        "",           "卖出"],
        "source":            ["https://src1.com", "https://src2.com", "https://src3.com"],
        "confidence":        [0.8,          0.5,         0.4],
        "notes":             ["n1",         "n2",        "n3"],
    }
    truth_df = pd.DataFrame(truth_data)

    # Prediction CSV (same keys, intentionally imperfect)
    pred_data = {
        "stock_code":        ["000001.SZ", "600000.SH", "000858.SZ"],
        "transaction_date":  ["20260611",  "20260611",  "20260611"],
        "capital_type":      ["游资",        "游资",        "散户"],   # 量化 mispredicted
        "capital_intention": ["买入",        "卖出",        "卖出"],
    }
    pred_df = pd.DataFrame(pred_data)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as tf:
        truth_df.to_csv(tf, index=False)
        truth_path = tf.name

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as pf:
        pred_df.to_csv(pf, index=False)
        pred_path = pf.name

    try:
        # Call the harness's scoring function directly
        harness_result = harness.score_from_pred_csv(truth_path, pred_path)

        # Compute expected result directly with validate.weighted_f1
        # (filter truth the same way load_truth_labels would)
        filtered_truth = harness.load_truth_labels(truth_path)
        direct_result = weighted_f1(pred_df, filtered_truth)
    finally:
        os.unlink(truth_path)
        os.unlink(pred_path)

    assert harness_result["weighted_f1"] == pytest.approx(direct_result["weighted_f1"]), \
        "Harness weighted_f1 != direct validate.weighted_f1 call"
    assert harness_result["n"] == direct_result["n"], \
        f"n mismatch: harness={harness_result['n']} direct={direct_result['n']}"


# ---------------------------------------------------------------------------
# V4.4 — EXAMPLE-only labels → skip message + exit code 0
# ---------------------------------------------------------------------------

def test_only_example_rows_prints_skip_and_exits_zero(capsys):
    """When labels are EXAMPLE-only, run() prints the skip message and returns 0."""
    harness = _import_harness()

    # Build an EXAMPLE-only CSV (all rows are non-scorable)
    data = {
        "stock_code":        ["EXAMPLE.SZ", "EXAMPLE.SH"],
        "transaction_date":  ["20260611",   "20260611"],
        "capital_type":      ["游资",         "量化"],
        "capital_intention": ["买入",         ""],
        "source":            ["EXAMPLE — placeholder", "EXAMPLE — another"],
        "confidence":        [0.0,           0.0],
        "notes":             ["ex1",         "ex2"],
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        df.to_csv(f, index=False)
        tmp_path = f.name

    try:
        # Use a non-existent pred CSV path to ensure the skip is triggered by
        # EXAMPLE-only truth, not by a missing pred file.
        # We create a dummy pred CSV (empty, just headers)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as pf:
            pd.DataFrame(columns=["stock_code", "transaction_date", "capital_type"]).to_csv(
                pf, index=False
            )
            pred_path = pf.name

        exit_code = harness.run(["--labels", tmp_path, "--input", pred_path])
    finally:
        os.unlink(tmp_path)
        os.unlink(pred_path)

    assert exit_code == 0, f"Expected exit code 0 for EXAMPLE-only labels, got {exit_code}"

    captured = capsys.readouterr()
    output = captured.out
    # Must mention "no scorable labels" or "EXAMPLE" and "Skipping"
    assert "no scorable" in output.lower() or "example" in output.lower(), \
        f"Skip message not found in output:\n{output}"
    assert "skipping" in output.lower(), \
        f"'Skipping' not found in output:\n{output}"


# ---------------------------------------------------------------------------
# V4.5 — local source smoke test (skipif fixture absent)
# ---------------------------------------------------------------------------

_LOCAL_TINY = _ROOT / "tests" / "fixtures" / "local_l2_tiny"


@pytest.mark.skipif(
    not _LOCAL_TINY.exists(),
    reason="tests/fixtures/local_l2_tiny not present — skip local-source smoke test",
)
def test_local_source_smoke():
    """With local_l2_tiny fixture, --input local: returns a dict with weighted_f1 and n>=1."""
    harness = _import_harness()

    # Build a tiny truth CSV pointing at a real stock/day in the fixture
    data = {
        "stock_code":        ["000001.SZ"],
        "transaction_date":  ["20260611"],
        "capital_type":      ["游资"],
        "capital_intention": ["买入"],
        "source":            ["https://smoke-test-source.com"],
        "confidence":        [0.8],
        "notes":             ["smoke test row"],
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        df.to_csv(f, index=False)
        tmp_path = f.name

    try:
        result = harness.predict_for_keys(
            filtered_truth=df,
            input_source=f"local:{str(_LOCAL_TINY)}",
        )
    finally:
        os.unlink(tmp_path)

    assert isinstance(result, dict), "predict_for_keys should return a dict"
    assert "weighted_f1" in result, "Result missing 'weighted_f1'"
    assert "n" in result, "Result missing 'n'"
    assert result["n"] >= 1, f"Expected n >= 1 for smoke fixture, got {result['n']}"
