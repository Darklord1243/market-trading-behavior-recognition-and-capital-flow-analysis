"""Offline Track V intention weighted-F1 validation harness.

**Offline / post-hoc only.** This script MUST NOT be imported by main.py or any
src/ inference-path module.  It reads our own hand labels (``capital_intention``
truth) + our own pipeline output and scores them with a self-contained,
support-weighted F1 over ``config.INTENTION_CLASSES``.  It never reads the
platform's instant score / backtest answers / leaderboard files (compliance #3:
no answer-feedback tuning; compliance #1: no post-close data enters features).

Why a separate harness from ``validate_offline.py``
---------------------------------------------------
``validate_offline.py`` / ``src.validate.weighted_f1`` score **capital_type only**
— they are blind to ``capital_intention`` (see docs/hypotheses/p2-intent-t0-dominance
§0, §5).  Intention also differs in *how* it is predicted: ``get_intention`` runs
on the **raw** feature row (``label.py`` feeds ``feat_raw`` — its thresholds are
absolute by design), so — unlike the capital_type gate — there is **no
rank-normalization panel**.  We therefore load only the labeled codes per date
and call ``get_intention`` directly, reproducing the measured baseline exactly.

This harness is the committed promotion of the read-only scratchpad probe
referenced in the P2-intent hypothesis doc (§5.1).

Usage
-----
python scripts/validate_intent_offline.py \\
    --labels tests/fixtures/validation_labels.csv --input parquet:data/202606

# Reproduce the {0616..0623} baseline (excludes 0624):
python scripts/validate_intent_offline.py --input parquet:data/202606 \\
    --dates 20260616,20260617,20260618,20260622,20260623

Exit codes
----------
0 — success (including the "no scorable intention labels → skip" case).
1 — real failure: missing / malformed files.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from typing import Any

import pandas as pd

# Ensure repo root is importable regardless of cwd (scripts/ is not a package).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import INTENTION_CLASSES  # noqa: E402  (after sys.path patch)
from src.pipeline_parquet import build_feature_matrix_for_panel  # noqa: E402
from src.rules import get_intention  # noqa: E402

log = logging.getLogger(__name__)

# Column carrying the intention ground truth in the truth CSV.
_LABEL_COL = "capital_intention"
_JOIN_KEYS = ["stock_code", "transaction_date"]
_DEFAULT_LABELS = os.path.join(_ROOT, "tests", "fixtures", "validation_labels.csv")


# ---------------------------------------------------------------------------
# Public importable functions (so tests can call them directly)
# ---------------------------------------------------------------------------

def load_intention_truth(
    path: str,
    min_confidence: float = 0.0,
    dates: list[str] | None = None,
) -> pd.DataFrame:
    """Load the truth CSV and keep only rows scorable for intention.

    A row is scorable iff ALL of:
      - ``confidence != 0.0`` AND ``source`` does NOT start with ``EXAMPLE``
        (the same EXAMPLE / zero-confidence filter as ``validate_offline``), AND
      - ``capital_intention`` (stripped) is one of ``INTENTION_CLASSES`` — blank
        / illegal intention rows are dropped (they cannot be scored).

    Parameters
    ----------
    path           : Path to the truth CSV.
    min_confidence : Optional extra lower bound (keep ``confidence > x``).
    dates          : Optional whitelist of ``transaction_date`` strings to keep.

    Returns
    -------
    Filtered DataFrame (stock_code / transaction_date stripped).
    """
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)

    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)
    is_example = (df["confidence"] == 0.0) | (
        df["source"].astype(str).str.upper().str.startswith("EXAMPLE")
    )
    df = df[~is_example].copy()

    if min_confidence > 0.0:
        df = df[df["confidence"] > min_confidence].copy()

    df[_LABEL_COL] = df[_LABEL_COL].astype(str).str.strip()
    df = df[df[_LABEL_COL].isin(INTENTION_CLASSES)].copy()

    df["stock_code"] = df["stock_code"].astype(str).str.strip()
    df["transaction_date"] = df["transaction_date"].astype(str).str.strip()

    if dates is not None:
        keep = {str(d).strip() for d in dates}
        df = df[df["transaction_date"].isin(keep)].copy()

    return df.reset_index(drop=True)


def predict_intention(truth_df: pd.DataFrame, root: str) -> pd.DataFrame:
    """Run ``get_intention`` on the labeled (stock, date) keys via parquet.

    Builds one feature matrix per date over the labeled codes only (intention
    thresholds are absolute → no normalization panel needed), then applies the
    PRODUCTION ``get_intention`` to each raw row, matching ``label.py``.

    Returns a DataFrame with columns (stock_code, transaction_date,
    capital_intention) — the predicted intention under ``_LABEL_COL`` so it
    joins cleanly against the truth.
    """
    rows: list[dict[str, Any]] = []
    for date, grp in truth_df.groupby("transaction_date"):
        codes = grp["stock_code"].astype(str).unique().tolist()
        matrix = build_feature_matrix_for_panel(root, str(date), codes)
        if matrix is None or matrix.empty:
            log.warning("predict_intention: no matrix for %s (codes=%d)", date, len(codes))
            continue
        for idx, row in matrix.iterrows():
            sc, td = idx if isinstance(idx, tuple) else (idx, date)
            rows.append({
                "stock_code": str(sc),
                "transaction_date": str(td),
                _LABEL_COL: get_intention(row.to_dict()),
            })
    if not rows:
        return pd.DataFrame(columns=_JOIN_KEYS + [_LABEL_COL])
    return pd.DataFrame(rows)


def intention_weighted_f1(pred_df: pd.DataFrame, truth_df: pd.DataFrame) -> dict[str, Any]:
    """Support-weighted F1 of predicted vs truth ``capital_intention``.

    Inner-joins on (stock_code, transaction_date) and computes the SAME
    support-weighted average F1 as ``src.validate.weighted_f1`` — re-implemented
    here over ``INTENTION_CLASSES`` so that ``src/validate.py`` (the capital_type
    gate) is never touched.

    Returns ``{"weighted_f1": float, "n": int, "per_class": {label: {...}}}``.
    Empty join → all zeros, n=0 (does not raise).
    """
    per_class: dict[str, dict[str, float]] = {
        label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
        for label in INTENTION_CLASSES
    }

    if pred_df is None or pred_df.empty or truth_df is None or truth_df.empty:
        return {"weighted_f1": 0.0, "n": 0, "per_class": per_class}

    merged = pred_df[_JOIN_KEYS + [_LABEL_COL]].merge(
        truth_df[_JOIN_KEYS + [_LABEL_COL]],
        on=_JOIN_KEYS,
        how="inner",
        suffixes=("_pred", "_truth"),
    )
    n = len(merged)
    if n == 0:
        return {"weighted_f1": 0.0, "n": 0, "per_class": per_class}

    y_pred = merged[f"{_LABEL_COL}_pred"].tolist()
    y_true = merged[f"{_LABEL_COL}_truth"].tolist()

    support: dict[str, int] = defaultdict(int)
    for label in y_true:
        support[label] += 1

    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    for pred_label, true_label in zip(y_pred, y_true):
        if pred_label == true_label:
            tp[pred_label] += 1
        else:
            fp[pred_label] += 1

    for label in INTENTION_CLASSES:
        s = support[label]
        precision_denom = tp[label] + fp[label]
        precision = tp[label] / precision_denom if precision_denom > 0 else 0.0
        recall = tp[label] / s if s > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": s,
        }

    wf1 = sum(
        per_class[label]["f1"] * per_class[label]["support"] for label in INTENTION_CLASSES
    ) / n
    return {"weighted_f1": wf1, "n": n, "per_class": per_class}


def score_intention(
    labels_path: str,
    root: str,
    min_confidence: float = 0.0,
    dates: list[str] | None = None,
) -> dict[str, Any]:
    """End-to-end: load truth → predict → score.  Returns the weighted_f1 dict."""
    truth = load_intention_truth(labels_path, min_confidence=min_confidence, dates=dates)
    if truth.empty:
        return {"weighted_f1": 0.0, "n": 0,
                "per_class": {label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
                              for label in INTENTION_CLASSES}}
    pred = predict_intention(truth, root)
    return intention_weighted_f1(pred, truth)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_result(result: dict[str, Any], labels_path: str, input_source: str):
    print(f"Track V offline intention-F1 — labels={labels_path}, input={input_source}")
    print(f"  scored n = {result['n']} (stock, day) pairs")
    print(f"  weighted_f1 = {result['weighted_f1']:.4f}")
    print("  per class:")
    for cls in INTENTION_CLASSES:
        e = result["per_class"].get(cls, {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0})
        print(f"    {cls:<6}  P={e['precision']:.3f} R={e['recall']:.3f} "
              f"F1={e['f1']:.3f}  support={e['support']}")


def _print_skip():
    print(
        "Track V offline intention-F1 — no scorable intention labels "
        "(only EXAMPLE / zero-confidence / blank-intention rows, or no key overlap).\n"
        "Skipping — not an error."
    )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Track V offline intention weighted-F1 harness (offline / post-hoc only)."
    )
    parser.add_argument("--labels", default=_DEFAULT_LABELS,
                        help="Truth CSV (default: tests/fixtures/validation_labels.csv)")
    parser.add_argument("--input", required=True,
                        help="Prediction source: 'parquet:<root>' (default root data/202606).")
    parser.add_argument("--min-confidence", type=float, default=0.0, dest="min_confidence",
                        help="Only score truth rows with confidence > this (default 0.0).")
    parser.add_argument("--dates", default=None,
                        help="Comma-separated transaction_date whitelist (e.g. 20260616,20260617).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    src = args.input.strip()
    if not src.lower().startswith("parquet"):
        print(f"ERROR: --input must be 'parquet:<root>'; got {args.input!r}", file=sys.stderr)
        return 1
    root = (src.split(":", 1)[1].strip() or "data/202606") if ":" in src else "data/202606"

    if not os.path.isfile(args.labels):
        print(f"ERROR: labels file not found: {args.labels}", file=sys.stderr)
        return 1

    dates = [d.strip() for d in args.dates.split(",")] if args.dates else None

    try:
        result = score_intention(
            args.labels, root, min_confidence=args.min_confidence, dates=dates
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: scoring failed: {exc}", file=sys.stderr)
        return 1

    if result["n"] == 0:
        _print_skip()
        return 0

    _print_result(result, args.labels, args.input)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
