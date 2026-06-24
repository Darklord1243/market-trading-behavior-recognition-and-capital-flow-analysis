"""Tests for src/label.py — Phase 1b: normalize_matrix wired into weak_label_matrix.

Panel tests use ≥10-row synthetic DataFrames to prove the scorer responds to
normalized inputs. The n=1 fixture cannot prove this (single row → all-0.5 tie
after normalization → arbitrary tie-break result).
"""

from __future__ import annotations

import pandas as pd
import pytest

import config
from src.label import weak_label_matrix

YOUZI, QUANT, RETAIL = config.CAPITAL_TYPES  # index 0/1/2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neutral_row() -> dict:
    """A neutral-ish base row — all features mid-range so no class dominates."""
    return {
        # OSS
        "oss_mega_amount_pct": 0.3,
        "oss_mega_count_pct": 0.3,
        "oss_small_amount_pct": 0.3,
        # AP
        "ap_active_buy_pct": 0.4,
        "ap_active_sell_pct": 0.4,
        "ap_unilateral_intensity": 0.3,
        # PD
        "pd_max_price_impact_pct": 0.3,
        # PI
        "pi_time_concentration": 0.3,
        # OBP
        "obp_big_quote_share": 0.3,
        "obp_imbalance_mean": 0.0,
        # RS
        "rs_interval_cv": 0.3,
        "rs_burst_ratio": 0.3,
        # CB (flag + ratios)
        "cb_available": 0.0,
        "cb_sell_cancel_ratio": 0.0,
        "cb_fast_cancel_ratio": 0.0,
        # intent
        "book_imbalance": 0.0,
        # misc
        "n_ticks": 100,
    }


def _build_panel() -> pd.DataFrame:
    """Build a ≥10-row synthetic cross-section with out-of-[0,1] raw feature values.

    Row layout:
      idx 0  — 游资 archetype: highest raw values on mega/aggression/CV dims
      idx 1  — 量化 archetype: highest raw values on small/burst dims, LOWEST on CV
      idx 2–9 — filler rows with intermediate out-of-[0,1] values to fill rank space

    WHY out-of-[0,1] raw values? This panel is designed to be a GENUINE discriminator
    (LIS §6 Phase 1b red-first requirement):

    * RAW scoring: score_capital_type applies clip01() to every feature. When all row
      values exceed 1.0 on a shared dimension (e.g. rs_interval_cv: 15.0, 2.0, 4.0…),
      clip01 saturates every one to 1.0. The youzi and quant archetypes receive
      identical clipped votes on those dims → raw arg-max cannot distinguish row 0 from
      row 1 → both score as 游资 (raw scoring FAILS the test).

    * NORMALIZED scoring: normalize_matrix() rank-normalizes values across rows before
      clip01 sees them. The rank ordering of 15.0 > 11.0 > … > 2.0 maps to distinct
      [0,1] values (1.0 and 0.0 for rows 0 and 1 on rs_interval_cv), so the score
      function cleanly separates the archetypes → row 0 → 游资, row 1 → 量化.

    Production-realistic magnitudes used for rs_interval_cv (~13.48 observed), and
    similar scale for other dims. cb_available=0 for all rows (no cancel table).
    """
    rows = []

    # Row 0: 游资 archetype — highest raw values on mega/aggression dims and CV,
    # lowest raw values on small-order and burst dims (still above 1.0 so clip01=1.0
    # on both, but rank places them at the extremes after normalize_matrix).
    youzi_row = _neutral_row()
    youzi_row.update({
        "oss_mega_amount_pct":     12.0,   # rank-highest → norm≈1.0 → strong youzi vote
        "oss_mega_count_pct":      11.0,
        "ap_active_buy_pct":        9.0,
        "ap_unilateral_intensity":  8.0,
        "pd_max_price_impact_pct": 10.0,
        "pi_time_concentration":    7.0,
        "obp_big_quote_share":      9.5,
        "rs_interval_cv":          15.0,   # rank-highest → norm=1.0 → youzi dim (high_supports=True)
                                           #                            quant dim (high_supports=False) → 1-1.0=0.0 (bad for quant)
        "oss_small_amount_pct":     1.2,   # rank-lowest → norm≈0.0 → small vote ~0 (bad for quant)
        "rs_burst_ratio":           1.1,   # rank-lowest → norm≈0.0 → burst vote ~0 (bad for quant)
    })
    rows.append(youzi_row)

    # Row 1: 量化 archetype — highest raw values on small/burst dims, LOWEST on CV.
    # All values still > 1.0 so clip01 gives same 1.0 as row 0 on each dim; only
    # rank ordering (via normalize_matrix) reveals the intended separation.
    quant_row = _neutral_row()
    quant_row.update({
        "oss_small_amount_pct":     8.0,   # rank-highest → norm=1.0 → strong quant vote
        "rs_burst_ratio":          10.0,   # rank-highest → norm=1.0 → strong quant vote
        "rs_interval_cv":           2.0,   # rank-LOWEST  → norm=0.0 → quant dim 1-0.0=1.0 (quant high_supports=False)
        "ap_unilateral_intensity":  1.3,   # low → norm near 0 → 1-v near 1.0 (quant vote)
        "pi_time_concentration":    1.4,
        "oss_mega_amount_pct":      1.5,   # rank-lowest → norm≈0.0 → youzi dim vote ~0
        "oss_mega_count_pct":       1.4,
        "ap_active_buy_pct":        1.3,
        "pd_max_price_impact_pct":  1.5,
        "obp_big_quote_share":      1.3,
    })
    rows.append(quant_row)

    # Rows 2–9: filler with intermediate out-of-[0,1] values to populate the rank space
    # so normalize_matrix has real contrast (avoids constant-column fallback).
    for i in range(8):
        filler = _neutral_row()
        filler["oss_mega_amount_pct"]     = 3.0 + 0.5 * i
        filler["oss_mega_count_pct"]      = 2.5 + 0.5 * i
        filler["ap_active_buy_pct"]       = 2.0 + 0.5 * i
        filler["ap_unilateral_intensity"] = 2.0 + 0.4 * i
        filler["pd_max_price_impact_pct"] = 2.5 + 0.5 * i
        filler["pi_time_concentration"]   = 2.0 + 0.3 * i
        filler["obp_big_quote_share"]     = 2.0 + 0.5 * i
        filler["rs_interval_cv"]          = 4.0 + 1.0 * i   # spans 4–11, between rows 0 and 1
        filler["oss_small_amount_pct"]    = 2.0 + 0.5 * i
        filler["rs_burst_ratio"]          = 2.0 + 0.8 * i
        rows.append(filler)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Phase 1b test 1: capital scoring uses normalized matrix
# ---------------------------------------------------------------------------

def test_weak_label_uses_normalized_capital_scoring():
    """≥10-row synthetic panel: planted 游资 row → 游资, planted 量化 row → 量化.

    This is the genuine discriminating proof (LIS §6 Phase 1b red-first):

    The panel uses out-of-[0,1] raw feature values (e.g. rs_interval_cv=15.0 for
    row 0 and 2.0 for row 1; all filler rows between 4.0–11.0). When label.py
    applies score_capital_type to RAW rows, clip01() saturates every value > 1.0
    to 1.0 — both the 游资 and 量化 archetypes receive identical clipped votes on
    all discriminating dims → both score as 游资 → the 量化 archetype is mis-labelled.
    This means the test FAILS if label.py reverts to raw-row scoring.

    When label.py applies score_capital_type to NORMALIZED rows (via normalize_matrix),
    rank ordering is preserved: rs_interval_cv rank-maps 15.0→1.0 and 2.0→0.0, giving
    row 0 a strong youzi vote (high_supports=True, v=1.0) and row 1 a strong quant vote
    (high_supports=False, 1-v=1.0). The other discriminating dims follow the same
    pattern → row 0 → 游资, row 1 → 量化.
    """
    m = _build_panel()
    labels = weak_label_matrix(m)

    assert labels.loc[0, "capital_type"] == YOUZI, (
        f"Row 0 (游资 archetype) scored {labels.loc[0, 'capital_type']} — "
        f"normalize_matrix may not be wired into weak_label_matrix"
    )
    assert labels.loc[1, "capital_type"] == QUANT, (
        f"Row 1 (量化 archetype) scored {labels.loc[1, 'capital_type']} — "
        f"normalize_matrix may not be wired into weak_label_matrix"
    )


# ---------------------------------------------------------------------------
# Phase 1b test 2: intent gate uses RAW matrix
# ---------------------------------------------------------------------------

def test_intent_uses_raw_matrix():
    """Intent confidence and capital_intention follow RAW imbalance, not normalized.

    Plant a row with a strong raw buy signal (book_imbalance=0.5,
    obp_imbalance_mean=0.5, ap_active_buy_pct=0.8) embedded in a panel where
    after rank normalization those values happen to be mid-range (other rows are
    also high). The intent should still fire '买入' and intent_confidence should
    be well above zero — proving it reads raw, not normalized, values.
    """
    # Build a panel where the planted row has a clear raw buy signal.
    # We pad with rows that also have high imbalance so the normalized value
    # for book_imbalance at row 0 would be mid-range, NOT necessarily ~1.0.
    rows = []
    for i in range(10):
        r = _neutral_row()
        # All rows get a strong positive imbalance (normalized → mid-range for most)
        r["book_imbalance"] = 0.4 + 0.01 * i
        r["obp_imbalance_mean"] = 0.4 + 0.01 * i
        r["ap_active_buy_pct"] = 0.75 + 0.01 * i
        rows.append(r)

    # Row 0 has the weakest (but still clearly above threshold) raw imbalance.
    # After normalization book_imbalance at row 0 maps to ~0 (rank 1 of 10),
    # which would suppress intent if intent used normalized values. But since
    # intent uses RAW values (book_imbalance=0.4, obp_imbalance_mean=0.4,
    # ap_active_buy_pct=0.75), it clears INTENT_IMBALANCE (0.08) and
    # INTENT_BUY_PCT (0.6) → should still emit 买入.
    m = pd.DataFrame(rows)
    labels = weak_label_matrix(m)

    from config import IMBALANCE_SNAPSHOT_WEIGHT, IMBALANCE_FULLDAY_WEIGHT, INTENT_IMBALANCE
    raw_imbalance_row0 = (
        IMBALANCE_SNAPSHOT_WEIGHT * m.loc[0, "book_imbalance"]
        + IMBALANCE_FULLDAY_WEIGHT * m.loc[0, "obp_imbalance_mean"]
    )
    # The raw imbalance clears the gate
    assert raw_imbalance_row0 > INTENT_IMBALANCE, (
        f"Test setup error: raw imbalance {raw_imbalance_row0} <= threshold {INTENT_IMBALANCE}"
    )
    # Intent must follow raw signal (买入)
    assert labels.loc[0, "capital_intention"] == "买入", (
        f"Row 0 intent={labels.loc[0, 'capital_intention']} but raw imbalance "
        f"({raw_imbalance_row0:.3f}) clears the threshold — intent must use raw values"
    )
    # Intent confidence must reflect the raw clearance distance (> 0)
    assert labels.loc[0, "intent_confidence"] > 0.0, (
        "intent_confidence is 0 despite raw imbalance clearing the gate"
    )


# ---------------------------------------------------------------------------
# Structural / regression tests
# ---------------------------------------------------------------------------

def test_weak_label_columns_present():
    """Output always has the four required columns."""
    m = _build_panel()
    labels = weak_label_matrix(m)
    for col in ("capital_type", "capital_intention", "capital_confidence", "intent_confidence"):
        assert col in labels.columns, f"Missing column: {col}"


def test_weak_label_index_preserved():
    """Output index matches input index."""
    m = _build_panel()
    labels = weak_label_matrix(m)
    assert list(labels.index) == list(m.index)


def test_weak_label_capital_types_valid():
    """All emitted capital_type values are in the locked vocabulary."""
    m = _build_panel()
    labels = weak_label_matrix(m)
    bad = set(labels["capital_type"]) - set(config.CAPITAL_TYPES)
    assert not bad, f"Invalid capital_type values: {bad}"


def test_weak_label_intention_valid():
    """All emitted capital_intention values are in the locked vocabulary."""
    m = _build_panel()
    labels = weak_label_matrix(m)
    bad = set(labels["capital_intention"]) - set(config.INTENTION_CLASSES)
    assert not bad, f"Invalid capital_intention values: {bad}"


def test_confidence_in_unit_interval():
    """Both confidence columns are in [0, 1] for all rows."""
    m = _build_panel()
    labels = weak_label_matrix(m)
    assert (labels["capital_confidence"] >= 0.0).all()
    assert (labels["capital_confidence"] <= 1.0).all()
    assert (labels["intent_confidence"] >= 0.0).all()
    assert (labels["intent_confidence"] <= 1.0).all()
