"""Tests for scripts/validate_intent_offline.py — offline intention weighted-F1.

Unit tests use **inline synthetic DataFrames / temp CSVs** (always run).  One
integration test reproduces the committed baseline 0.5539 / n=64 against the
real parquet corpus; it is skipped when data/202606 is absent so a clean CI
checkout never breaks.

Compliance: this file imports only from scripts/ — never from a src/
inference-path module.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).parent.parent
_HARNESS_PATH = _ROOT / "scripts" / "validate_intent_offline.py"
_PARQUET_ROOT = _ROOT / "data" / "202606"
_LABELS = _ROOT / "tests" / "fixtures" / "validation_labels.csv"


def _import_harness():
    spec = importlib.util.spec_from_file_location("validate_intent_offline", _HARNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# load_intention_truth — filtering
# ---------------------------------------------------------------------------

def _write_csv(tmp_path: Path, rows: dict) -> str:
    p = tmp_path / "labels.csv"
    pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
    return str(p)


def test_load_drops_example_zeroconf_and_blank_intention(tmp_path):
    """EXAMPLE rows, zero-confidence rows, and blank/illegal intention all drop."""
    harness = _import_harness()
    path = _write_csv(tmp_path, {
        "stock_code":        ["000001.SZ", "600000.SH", "000002.SZ", "600001.SH", "000003.SZ"],
        "transaction_date":  ["20260616"] * 5,
        "capital_type":      ["游资", "量化", "散户", "游资", "量化"],
        "capital_intention": ["买入", "卖出", "",      "T0交易", "买入"],
        "source":            ["real", "real", "real", "EXAMPLE-x", "real"],
        "confidence":        ["0.9", "0.0", "0.9", "0.9", "0.8"],
    })
    df = harness.load_intention_truth(path)
    # kept: row0 (买入), row4 (买入).  dropped: row1 (conf 0), row2 (blank intent), row3 (EXAMPLE)
    assert len(df) == 2
    assert set(df["stock_code"]) == {"000001.SZ", "000003.SZ"}
    assert set(df["capital_intention"]) == {"买入"}


def test_load_date_whitelist(tmp_path):
    """The dates= whitelist restricts to the given transaction_dates."""
    harness = _import_harness()
    path = _write_csv(tmp_path, {
        "stock_code":        ["000001.SZ", "600000.SH", "000002.SZ"],
        "transaction_date":  ["20260616", "20260623", "20260624"],
        "capital_type":      ["游资", "量化", "散户"],
        "capital_intention": ["买入", "卖出", "T0交易"],
        "source":            ["real", "real", "real"],
        "confidence":        ["0.9", "0.9", "0.9"],
    })
    df = harness.load_intention_truth(path, dates=["20260616", "20260623"])
    assert set(df["transaction_date"]) == {"20260616", "20260623"}
    assert len(df) == 2


# ---------------------------------------------------------------------------
# intention_weighted_f1 — math
# ---------------------------------------------------------------------------

def test_weighted_f1_known_case():
    """Hand-computed 3-row case pins the support-weighted F1 formula.

    truth  A=买入 B=卖出 C=T0交易 ; pred A=买入 B=T0交易 C=T0交易
      买入   : TP1 FP0 -> P1 R1   F1=1
      卖出   : TP0       -> P0 R0   F1=0
      T0交易 : TP1 FP1 -> P.5 R1  F1=2/3
    wf1 = (1*1 + 0*1 + (2/3)*1) / 3 = 0.55556
    """
    harness = _import_harness()
    keys = {"stock_code": ["A", "B", "C"], "transaction_date": ["d", "d", "d"]}
    truth = pd.DataFrame({**keys, "capital_intention": ["买入", "卖出", "T0交易"]})
    pred = pd.DataFrame({**keys, "capital_intention": ["买入", "T0交易", "T0交易"]})
    res = harness.intention_weighted_f1(pred, truth)
    assert res["n"] == 3
    assert res["weighted_f1"] == pytest.approx(0.55556, abs=1e-4)
    assert res["per_class"]["买入"]["f1"] == pytest.approx(1.0)
    assert res["per_class"]["卖出"]["f1"] == pytest.approx(0.0)
    assert res["per_class"]["T0交易"]["f1"] == pytest.approx(2 / 3, abs=1e-4)


def test_weighted_f1_empty_join_returns_zeros():
    """No common keys → n=0, weighted_f1=0.0, all classes zeroed (no raise)."""
    harness = _import_harness()
    truth = pd.DataFrame({"stock_code": ["A"], "transaction_date": ["d"], "capital_intention": ["买入"]})
    pred = pd.DataFrame({"stock_code": ["Z"], "transaction_date": ["d"], "capital_intention": ["买入"]})
    res = harness.intention_weighted_f1(pred, truth)
    assert res["n"] == 0
    assert res["weighted_f1"] == 0.0
    assert all(res["per_class"][c]["support"] == 0 for c in res["per_class"])


def test_weighted_f1_empty_frames():
    """Empty pred/truth frames return the zero result without raising."""
    harness = _import_harness()
    empty = pd.DataFrame(columns=["stock_code", "transaction_date", "capital_intention"])
    res = harness.intention_weighted_f1(empty, empty)
    assert res["n"] == 0 and res["weighted_f1"] == 0.0


# ---------------------------------------------------------------------------
# Integration — reproduce the committed baseline (data-gated)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (_PARQUET_ROOT.is_dir() and _LABELS.is_file()),
    reason="requires data/202606 parquet corpus + validation_labels.csv",
)
def test_reproduces_baseline_0p5539_n64():
    """End-to-end harness reproduces the locked baseline 0.5539 / n=64 on {0616-0623}.

    This is the committed-number guarantee for the P2-intent slice: the gate
    (INTENT_NET_BAND=0.08) scores 0.5539 weighted-F1 over the five dates that
    predate the 0624 label addendum.  If get_intention or the feature pipeline
    drifts, this test fails loudly.
    """
    harness = _import_harness()
    res = harness.score_intention(
        str(_LABELS),
        str(_PARQUET_ROOT),
        dates=["20260616", "20260617", "20260618", "20260622", "20260623"],
    )
    assert res["n"] == 64
    assert res["weighted_f1"] == pytest.approx(0.5539, abs=5e-4)
    # 买入 recall is the P2-intent lever — pin it well above the old-gate 0.185.
    assert res["per_class"]["买入"]["recall"] == pytest.approx(0.519, abs=1e-2)
