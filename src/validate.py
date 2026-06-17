"""Offline weighted-F1 proxy scorer for Task-2 capital_type predictions.

**Offline / post-hoc only.** This module MUST NOT be imported by main.py or
any inference-path module.  Validation labels are public post-market data and
must never enter the feature pipeline (compliance #1: no post-close data in
features; compliance #3: no answer-feedback tuning).

Public API
----------
weighted_f1(pred_df, truth_df) -> dict
    Inner-join on (stock_code, transaction_date), compute weighted F1 and
    per-class precision / recall / F1 / support over capital_type.
    Returns {"weighted_f1": float, "n": int, "per_class": {label: {...}}}.
    Empty join → {"weighted_f1": 0.0, "n": 0, "per_class": {label: zeros}}.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from config import CAPITAL_TYPES  # locked 3-class set: {游资, 量化, 散户}

# Column names used for the inner join key.
_JOIN_KEYS: list[str] = ["stock_code", "transaction_date"]

# Column containing the label to score.
_LABEL_COL: str = "capital_type"


def weighted_f1(
    pred_df: pd.DataFrame,
    truth_df: pd.DataFrame,
) -> dict[str, Any]:
    """Compute offline weighted F1 of predicted capital_type vs a truth set.

    Parameters
    ----------
    pred_df : pd.DataFrame
        Pipeline output rows.  Required columns: stock_code, transaction_date,
        capital_type.
    truth_df : pd.DataFrame
        Hand-labeled truth rows.  Same required columns.

    Returns
    -------
    dict with keys:
        "weighted_f1" : float — sklearn-compatible weighted average F1.
        "n"           : int   — number of (stock, date) pairs scored (join size).
        "per_class"   : dict[str, dict] — per label: precision, recall, f1, support.

    Edge behaviour
    --------------
    Empty inner join (no common keys) → weighted_f1=0.0, n=0, per_class with
    zeros for every class.  Does NOT raise.

    No hard-coding: operates over config.CAPITAL_TYPES generically.
    Pure & offline: no network, no file I/O of board answers.
    """
    # ------------------------------------------------------------------
    # 1. Inner-join on (stock_code, transaction_date)
    # ------------------------------------------------------------------
    merged = pred_df[_JOIN_KEYS + [_LABEL_COL]].merge(
        truth_df[_JOIN_KEYS + [_LABEL_COL]],
        on=_JOIN_KEYS,
        how="inner",
        suffixes=("_pred", "_truth"),
    )

    n = len(merged)

    # ------------------------------------------------------------------
    # 2. Build per-class zeroed template (covers all classes even if absent)
    # ------------------------------------------------------------------
    per_class: dict[str, dict[str, float]] = {
        label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
        for label in CAPITAL_TYPES
    }

    if n == 0:
        return {"weighted_f1": 0.0, "n": 0, "per_class": per_class}

    # ------------------------------------------------------------------
    # 3. Compute per-class counts: TP, FP, FN
    # ------------------------------------------------------------------
    y_pred = merged[f"{_LABEL_COL}_pred"].tolist()
    y_true = merged[f"{_LABEL_COL}_truth"].tolist()

    # Count support (number of true instances per class)
    support: dict[str, int] = defaultdict(int)
    for label in y_true:
        support[label] += 1

    # Count TP (predicted == true == class) and FP (predicted == class, true != class)
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)

    for pred_label, true_label in zip(y_pred, y_true):
        if pred_label == true_label:
            tp[pred_label] += 1
        else:
            fp[pred_label] += 1

    # Compute precision, recall, F1 and support per class
    for label in CAPITAL_TYPES:
        s = support[label]
        precision_denom = tp[label] + fp[label]
        recall_denom = s  # == support[label]

        precision = tp[label] / precision_denom if precision_denom > 0 else 0.0
        recall = tp[label] / recall_denom if recall_denom > 0 else 0.0
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

    # ------------------------------------------------------------------
    # 4. Weighted F1: weighted by support (matches sklearn average="weighted")
    #    weight = support[label] / n  (labels with support 0 contribute 0)
    # ------------------------------------------------------------------
    wf1 = sum(
        per_class[label]["f1"] * per_class[label]["support"]
        for label in CAPITAL_TYPES
    ) / n

    return {"weighted_f1": wf1, "n": n, "per_class": per_class}
