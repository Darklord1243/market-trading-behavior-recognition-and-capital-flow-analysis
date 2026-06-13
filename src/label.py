"""Stage-2 weak labels + confidence.

Wraps the Stage-1 soft rules into a per-(stock, day) weak label with a confidence
score. Confidence is the rule's own margin (how decisively the score separated the
two capital types, and how far the intent signals cleared their gates) — it is the
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
from src.rules import get_intention, score_capital_type

log = logging.getLogger(__name__)


def _capital_confidence(score_yz: float, score_qt: float) -> float:
    """Normalised margin between the two capital scores in [0, 1]."""
    total = score_yz + score_qt
    if total <= 0:
        return 0.0
    return float(abs(score_yz - score_qt) / total)


def _intent_confidence(feat: dict) -> float:
    """How far the dual-source imbalance cleared the +/- gate, in [0, 1]."""
    imbalance = (
        IMBALANCE_SNAPSHOT_WEIGHT * feat.get("book_imbalance", 0.0)
        + IMBALANCE_FULLDAY_WEIGHT * feat.get("obp_imbalance_mean", 0.0)
    )
    return float(min(1.0, abs(imbalance) / max(INTENT_IMBALANCE, 1e-9)))


def weak_label_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    """Produce weak labels + confidence for every (stock, day) feature row.

    Returns a frame indexed like `matrix` with columns:
    capital_type, capital_intention, capital_confidence, intent_confidence.
    """
    records = []
    for idx, row in matrix.iterrows():
        feat = row.to_dict()
        capital_type, s_yz, s_qt = score_capital_type(feat)
        intention = get_intention(feat)
        records.append({
            "capital_type": capital_type,
            "capital_intention": intention,
            "capital_confidence": _capital_confidence(s_yz, s_qt),
            "intent_confidence": _intent_confidence(feat),
        })
    out = pd.DataFrame(records, index=matrix.index)
    log.info("weak labels: %s", out["capital_type"].value_counts().to_dict())
    return out
