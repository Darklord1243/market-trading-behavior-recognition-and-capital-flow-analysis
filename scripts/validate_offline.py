"""Offline Track V proxy-F1 validation harness.

**Offline / post-hoc only.** This script MUST NOT be imported by main.py or
any src/ inference-path module.  It reads our own hand labels + our own pipeline
output and compares them via validate.weighted_f1.  It never reads the platform's
instant score / backtest answers / outputs/ leaderboard files (compliance #3: no
answer-feedback tuning; compliance #1: no post-close data enters features).

Usage
-----
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv \\
    --input local:data
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv \\
    --input outputs/predict_result.csv

Exit codes
----------
0 — success (including the "EXAMPLE-only / empty-join → skip" case; that is not
    an error — it is the expected pre-V.3 state).
1 — real failure: missing / malformed files.

The EXAMPLE-only / empty-join case is not an error because before human labels
(V.3) are seeded the fixture ships with only placeholder rows.  Treating that as
a hard failure would break CI on a clean checkout; instead we print a clear skip
message so the operator knows the harness ran but had nothing to score.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

import pandas as pd

# Ensure repo root is importable regardless of cwd (scripts/ is not a package).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import CAPITAL_TYPES  # noqa: E402  (after sys.path patch)
from src.validate import weighted_f1  # noqa: E402

log = logging.getLogger(__name__)

# Columns required in the truth CSV
_TRUTH_REQUIRED = ["stock_code", "transaction_date", "capital_type", "confidence", "source"]
# Default truth labels path
_DEFAULT_LABELS = os.path.join(_ROOT, "tests", "fixtures", "validation_labels.csv")


# ---------------------------------------------------------------------------
# Public importable functions (so tests can call them directly)
# ---------------------------------------------------------------------------

def load_truth_labels(path: str, min_confidence: float = 0.0) -> pd.DataFrame:
    """Load the truth CSV and drop EXAMPLE / zero-confidence rows.

    A row is non-scorable (dropped) iff:
      - ``confidence == 0.0``  OR
      - ``source`` starts with ``EXAMPLE`` (case-insensitive)

    Rows with ``confidence > min_confidence`` are kept when ``min_confidence > 0``.

    Parameters
    ----------
    path:
        Path to the truth CSV (columns: stock_code, transaction_date, capital_type,
        capital_intention, source, confidence, notes).
    min_confidence:
        Additional lower bound on confidence (default 0.0 → keep all non-EXAMPLE rows).

    Returns
    -------
    Filtered DataFrame with only scorable rows.
    """
    df = pd.read_csv(path, encoding="utf-8", dtype=str)

    # Coerce confidence to float
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)

    # Drop EXAMPLE rows: confidence == 0.0 OR source starts with EXAMPLE (case-insensitive)
    is_example = (df["confidence"] == 0.0) | (
        df["source"].astype(str).str.upper().str.startswith("EXAMPLE")
    )
    df = df[~is_example].copy()

    # Apply optional min_confidence filter
    if min_confidence > 0.0:
        df = df[df["confidence"] > min_confidence].copy()

    df = df.reset_index(drop=True)
    return df


def predict_for_keys(
    filtered_truth: pd.DataFrame,
    input_source: str,
) -> dict[str, Any]:
    """Run the pipeline on the labeled (stock, day) keys and return scored result.

    Parameters
    ----------
    filtered_truth:
        Scorable truth rows (already filtered — no EXAMPLE / zero-confidence rows).
    input_source:
        Either ``local:<root>`` (run the local ingest pipeline) or a path to a
        precomputed prediction CSV.

    Returns
    -------
    dict with keys: ``weighted_f1``, ``n``, ``per_class`` — from validate.weighted_f1.
    """
    pred_df = _get_predictions(filtered_truth, input_source)
    if pred_df is None or pred_df.empty:
        return _empty_result()
    return weighted_f1(pred_df, filtered_truth)


def score_from_pred_csv(truth_path: str, pred_csv_path: str, min_confidence: float = 0.0) -> dict[str, Any]:
    """Load truth, filter EXAMPLE rows, load pred CSV, call weighted_f1.

    This is the join layer used by tests to verify the harness calls the real scorer.

    Returns
    -------
    dict with keys: ``weighted_f1``, ``n``, ``per_class``.
    """
    filtered_truth = load_truth_labels(truth_path, min_confidence=min_confidence)
    if filtered_truth.empty:
        return _empty_result()
    pred_df = pd.read_csv(pred_csv_path, encoding="utf-8", dtype=str)
    return weighted_f1(pred_df, filtered_truth)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _empty_result() -> dict[str, Any]:
    """Return the weighted_f1 zero-result dict (matches validate.weighted_f1 contract)."""
    per_class = {label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
                 for label in CAPITAL_TYPES}
    return {"weighted_f1": 0.0, "n": 0, "per_class": per_class}


def _get_predictions(
    filtered_truth: pd.DataFrame,
    input_source: str,
) -> pd.DataFrame | None:
    """Dispatch to local ingest or precomputed CSV based on input_source.

    Returns a DataFrame with at least columns (stock_code, transaction_date, capital_type),
    or None if no predictions can be produced.
    """
    src = input_source.strip()

    if src.lower().startswith("local"):
        # local:<root> or just "local" (default root = data)
        if ":" in src:
            root = src.split(":", 1)[1].strip() or "data"
        else:
            root = "data"
        return _predict_local(filtered_truth, root)
    elif src.lower().startswith("parquet"):
        # parquet:<root> or just "parquet" (default root = data/202606)
        if ":" in src:
            root = src.split(":", 1)[1].strip() or "data/202606"
        else:
            root = "data/202606"
        return _predict_parquet(filtered_truth, root)
    else:
        # Treat src as a path to a precomputed prediction CSV
        if not os.path.isfile(src):
            log.error("Prediction file not found: %s", src)
            return None
        return pd.read_csv(src, encoding="utf-8", dtype=str)


def _predict_local(filtered_truth: pd.DataFrame, root: str) -> pd.DataFrame:
    """Run the local ingest pipeline for every labeled (stock, day) and return predictions.

    Mirrors the Stage-2 path in main.py:
      ingest_local.load_local → aggregate.build_feature_matrix
          (with cancel_lookup) → label.weak_label_matrix → postprocess.assemble_predict

    Only the labeled keys (from filtered_truth) are processed and returned.
    """
    # Import here (not at module top) to keep the harness import graph lean
    # and to make it obvious these are library-function calls, not inference-path imports.
    from src import aggregate, label as label_mod, postprocess
    from src.ingest_local import discover_stocks, load_local, read_cancel_frame

    # Distinct dates in the labels
    dates = filtered_truth["transaction_date"].astype(str).unique().tolist()

    all_pred_rows = []

    for date in dates:
        # Load all stocks available for this date
        df = load_local(root, date)
        if df is None or df.empty:
            log.warning("_predict_local: no data for date %s under %s", date, root)
            continue

        # Build cancel_lookup: {(stock_code, date): cancel_df} for each discovered stock
        cancel_lookup: dict = {}
        pairs = discover_stocks(root, date)
        for (d, code) in pairs:
            stock_dir = os.path.join(root, d, d, code)
            try:
                cancel_df = read_cancel_frame(stock_dir, code)
                cancel_lookup[(code, str(date))] = cancel_df
            except Exception as exc:  # noqa: BLE001
                log.warning("_predict_local: cancel read failed for %s/%s: %s", d, code, exc)

        # Build feature matrix with cancel data
        matrix = aggregate.build_feature_matrix(
            df, has_cancel_table=True, cancel_lookup=cancel_lookup
        )

        if matrix.empty:
            log.warning("_predict_local: empty feature matrix for date %s", date)
            continue

        # Stage-2: weak labels (same as main.py [4/5])
        weak = label_mod.weak_label_matrix(matrix)

        # assemble_predict flattens the MultiIndex → stock_code, transaction_date columns
        predict_df = postprocess.assemble_predict(weak)
        all_pred_rows.append(predict_df)

    if not all_pred_rows:
        return pd.DataFrame(columns=["stock_code", "transaction_date", "capital_type"])

    combined = pd.concat(all_pred_rows, ignore_index=True)

    # Restrict to the labeled keys only
    keys = filtered_truth[["stock_code", "transaction_date"]].copy()
    keys["stock_code"] = keys["stock_code"].astype(str)
    keys["transaction_date"] = keys["transaction_date"].astype(str)
    combined["stock_code"] = combined["stock_code"].astype(str)
    combined["transaction_date"] = combined["transaction_date"].astype(str)
    filtered_pred = combined.merge(keys, on=["stock_code", "transaction_date"], how="inner")
    return filtered_pred


def _predict_parquet(filtered_truth: pd.DataFrame, root: str) -> pd.DataFrame:
    """Run the parquet ingest pipeline for every labeled (stock, day) and return predictions.

    Mirrors ``_predict_local`` but routes through ``ingest_parquet`` (the new
    English-schema corpus) and is **driven by the labeled keys only** — the real
    corpus is ~13 GB/day, so we never load the full universe (inventory §6).
    """
    from src import aggregate, label as label_mod, postprocess
    from src.ingest_parquet import load_parquet, read_cancel_frame_parquet

    dates = filtered_truth["transaction_date"].astype(str).unique().tolist()

    all_pred_rows = []
    for date in dates:
        keys = (
            filtered_truth.loc[
                filtered_truth["transaction_date"].astype(str) == str(date), "stock_code"
            ].astype(str).unique().tolist()
        )
        df = load_parquet(root, date, keys=keys)
        if df is None or df.empty:
            log.warning("_predict_parquet: no data for date %s under %s", date, root)
            continue

        # Cancel frames for the labeled keys → real CB features.
        cancel_lookup: dict = {}
        for code in keys:
            try:
                cancel_lookup[(code, str(date))] = read_cancel_frame_parquet(root, date, code)
            except Exception as exc:  # noqa: BLE001
                log.warning("_predict_parquet: cancel read failed for %s/%s: %s", date, code, exc)

        matrix = aggregate.build_feature_matrix(
            df, has_cancel_table=True, cancel_lookup=cancel_lookup
        )
        if matrix.empty:
            log.warning("_predict_parquet: empty feature matrix for date %s", date)
            continue

        weak = label_mod.weak_label_matrix(matrix)
        predict_df = postprocess.assemble_predict(weak)
        all_pred_rows.append(predict_df)

    if not all_pred_rows:
        return pd.DataFrame(columns=["stock_code", "transaction_date", "capital_type"])

    combined = pd.concat(all_pred_rows, ignore_index=True)

    keys_df = filtered_truth[["stock_code", "transaction_date"]].copy()
    keys_df["stock_code"] = keys_df["stock_code"].astype(str)
    keys_df["transaction_date"] = keys_df["transaction_date"].astype(str)
    combined["stock_code"] = combined["stock_code"].astype(str)
    combined["transaction_date"] = combined["transaction_date"].astype(str)
    return combined.merge(keys_df, on=["stock_code", "transaction_date"], how="inner")


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_result(result: dict[str, Any], labels_path: str, input_source: str, n_dropped: int):
    """Print the Track V proxy-F1 report to stdout."""
    print(f"Track V offline proxy-F1 — labels={labels_path}, input={input_source}")
    print(f"  scored n = {result['n']} (stock, day) pairs   "
          f"[dropped {n_dropped} EXAMPLE/low-confidence rows]")
    print(f"  weighted_f1 = {result['weighted_f1']:.4f}")
    print("  per class:")
    for cls in CAPITAL_TYPES:
        entry = result["per_class"].get(cls, {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0})
        print(f"    {cls:<4}  P={entry['precision']:.2f} R={entry['recall']:.2f} "
              f"F1={entry['f1']:.2f}  support={entry['support']}")


def _print_skip():
    """Print the 'no scorable labels' skip message."""
    print(
        "Track V offline proxy-F1 — no scorable labels "
        "(only EXAMPLE / zero-confidence rows, or no key overlap).\n"
        "Seed real rows via docs/human_guides/track_v_validation_labels.md (V.3). "
        "Skipping — not an error."
    )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def run(argv: list[str] | None = None) -> int:
    """Parse argv, run the harness, print results.  Returns exit code (0 or 1)."""
    parser = argparse.ArgumentParser(
        description="Track V offline proxy-F1 validation harness (offline / post-hoc only)."
    )
    parser.add_argument(
        "--labels",
        default=_DEFAULT_LABELS,
        help="Path to the truth CSV (default: tests/fixtures/validation_labels.csv)",
    )
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Prediction source.  Either 'local:<root>' to run the local ingest pipeline, "
            "or a path to a precomputed prediction CSV."
        ),
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        dest="min_confidence",
        help="Only score truth rows with confidence > this threshold (default 0.0).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Restrict scoring to a single date YYYYMMDD (optional).",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # --- Load truth ---
    if not os.path.isfile(args.labels):
        print(f"ERROR: labels file not found: {args.labels}", file=sys.stderr)
        return 1

    try:
        filtered_truth = load_truth_labels(args.labels, min_confidence=args.min_confidence)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to load labels: {exc}", file=sys.stderr)
        return 1

    # Optional date filter
    if args.date:
        filtered_truth = filtered_truth[
            filtered_truth["transaction_date"].astype(str) == str(args.date)
        ]

    # Count dropped rows (for the output report)
    try:
        raw_count = len(pd.read_csv(args.labels, encoding="utf-8", dtype=str))
    except Exception:  # noqa: BLE001
        raw_count = len(filtered_truth)  # fallback: no drop info
    n_dropped = raw_count - len(filtered_truth)

    # --- EXAMPLE-only / empty truth ---
    if filtered_truth.empty:
        _print_skip()
        return 0

    # --- Get predictions ---
    try:
        result = predict_for_keys(filtered_truth, args.input)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: prediction failed: {exc}", file=sys.stderr)
        return 1

    # --- Empty join after prediction ---
    if result["n"] == 0:
        _print_skip()
        return 0

    # --- Print results ---
    _print_result(result, args.labels, args.input, n_dropped)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
