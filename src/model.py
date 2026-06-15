"""Stage-3 supervised heads (LightGBM/XGBoost) — STUB.

The final design trains gradient-boosted heads on the Stage-2 weak labels (weighted
by confidence) to smooth the rule output. That training is intentionally NOT built
yet (brief: "Do NOT implement the real LightGBM training yet"). This stub passes the
Stage-2 weak labels through unchanged so the end-to-end pipeline emits valid output.

The seam is real: `CapitalTypeHead.fit/predict` already have the right signature, so
swapping in a trained LightGBM head later is a localised change. No LLM call lives in
this inference path (brief §9).
"""

from __future__ import annotations

import logging

import pandas as pd

from config import CAPITAL_TYPES, RANDOM_SEED

log = logging.getLogger(__name__)


class CapitalTypeHead:
    """Pass-through stub for the Stage-3 capital-type model (3-class).

    Replace the body of `fit`/`predict` with a real LightGBM/XGBoost head trained on
    weak labels weighted by `capital_confidence`. Until then, predictions == weak
    labels, so output format and the audit contract are exercised end-to-end.

    `n_classes` is 3 (游资 / 量化 / 散户) so that when the real head lands it trains a
    3-class classifier over the locked `CAPITAL_TYPES` label space.
    """

    n_classes = len(CAPITAL_TYPES)  # 3 — capital_type is a 3-class problem

    def __init__(self, random_state: int = RANDOM_SEED):
        self.random_state = random_state
        self.classes_ = list(CAPITAL_TYPES)
        self._fitted = False

    def fit(self, features: pd.DataFrame, weak_labels: pd.DataFrame) -> "CapitalTypeHead":
        # STUB: a trained head would fit here using weak_labels + sample weights.
        log.info("CapitalTypeHead.fit: STUB (pass-through, no training) on %d rows",
                 len(features))
        self._fitted = True
        return self

    def predict(self, features: pd.DataFrame, weak_labels: pd.DataFrame) -> pd.Series:
        # STUB: return the weak labels unchanged.
        return weak_labels["capital_type"].copy()


def apply_model(features: pd.DataFrame, weak_labels: pd.DataFrame) -> pd.DataFrame:
    """Run the Stage-3 head (stub) and return final capital_type/intention.

    Intent is carried through from the rule stage; only capital_type passes the head.
    """
    head = CapitalTypeHead().fit(features, weak_labels)
    out = weak_labels.copy()
    out["capital_type"] = head.predict(features, weak_labels)
    return out[["capital_type", "capital_intention"]]
