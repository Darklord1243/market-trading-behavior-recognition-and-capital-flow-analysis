"""Stage-2 weak labels + confidence.

Wraps the Stage-1 soft rules into a per-(stock, day) weak label with a confidence
score. Confidence is the rule's own margin (how decisively the top score separated
from the runner-up across the three capital types, and how far the intent signals
cleared their gates) — it is the
hook the Stage-3 model head (model.py) will later use to weight / filter training
rows. No platform evaluation labels are used anywhere (compliance hard-rule #3).
"""

from __future__ import annotations

import logging

import pandas as pd

from config import (
    IMBALANCE_FULLDAY_WEIGHT,
    IMBALANCE_SNAPSHOT_WEIGHT,
    INTENT_IMBALANCE,
)
from src.normalize import normalize_matrix
from src.rules import get_intention, score_capital_type

log = logging.getLogger(__name__)


def _capital_confidence(scores: list) -> float:
    """3-class softmax-style margin: top1 − top2 over the class scores, in [0, 1].

    Generalises the old binary boundary-distance to three classes. A decisive
    label has a large gap between its winning score and the runner-up; a tie
    sits near 0 and is flagged low-confidence downstream.
    """
    if not scores:
        return 0.0
    top1, top2 = sorted(scores, reverse=True)[:2]
    return float(max(0.0, top1 - top2))


def _intent_confidence(feat: dict) -> float:
    """How far the dual-source imbalance cleared the +/- gate, in [0, 1]."""
    imbalance = (
        IMBALANCE_SNAPSHOT_WEIGHT * feat.get("book_imbalance", 0.0)
        + IMBALANCE_FULLDAY_WEIGHT * feat.get("obp_imbalance_mean", 0.0)
    )
    return float(min(1.0, abs(imbalance) / max(INTENT_IMBALANCE, 1e-9)))


def weak_label_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    """Produce weak labels + confidence for every (stock, day) feature row.

    Capital-type scoring runs on rank-normalized values (cross-sample within-day,
    via normalize_matrix) so features are comparable across stocks. Intent gate
    thresholds are absolute, so get_intention and _intent_confidence use the
    original raw matrix rows unchanged.

    Returns a frame indexed like `matrix` with columns:
    capital_type, capital_intention, capital_confidence, intent_confidence.
    """
    norm = normalize_matrix(matrix)
    records = []
    for idx, row in norm.iterrows():
        feat_norm = row.to_dict()
        feat_raw = matrix.loc[idx].to_dict()
        capital_type, scores = score_capital_type(feat_norm)
        intention = get_intention(feat_raw)
        records.append({
            "capital_type": capital_type,
            "capital_intention": intention,
            "capital_confidence": _capital_confidence(scores),
            "intent_confidence": _intent_confidence(feat_raw),
        })
    out = pd.DataFrame(records, index=matrix.index)
    log.info("weak labels: %s", out["capital_type"].value_counts().to_dict())
    return out
