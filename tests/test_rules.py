"""Unit tests for the Stage-1 3-way capital-type scorer and the 散户 guard.

The scorer separates 游资 / 量化 / 散户 from synthetic feature dicts. The two
non-obvious invariants under test:
  * 量化 vs 散户 split is RHYTHM-based, not size-based (both are small-order).
  * 散户 is a GUARDED residual — it may only win when BOTH 游资 and 量化 are weak;
    a balanced, high-rhythm quant day must NOT fall into retail by default.
"""

import config
from src.label import _capital_confidence
from src.rules import (
    NEUTRAL,
    RETAIL_GATE_MARGIN,
    get_intention,
    score_capital_type,
)

YOUZI, QUANT, RETAIL = config.CAPITAL_TYPES  # index 0/1/2


def _base():
    """A neutral-ish feature dict (snapshot-only: no cancel table)."""
    return {
        "oss_mega_amount_pct": 0.2, "oss_mega_count_pct": 0.2,
        "oss_small_amount_pct": 0.2, "ap_active_buy_pct": 0.5,
        "ap_unilateral_intensity": 0.2, "pd_max_price_impact_pct": 0.2,
        "pi_time_concentration": 0.2, "obp_big_quote_share": 0.2,
        "rs_interval_cv": 0.2, "rs_burst_ratio": 0.2, "cb_available": 0.0,
    }


def test_returns_three_scores():
    label, scores = score_capital_type(_base())
    assert label in config.CAPITAL_TYPES
    assert len(scores) == 3
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_youzi_wins_on_size_and_aggression():
    feat = _base()
    feat.update({
        "oss_mega_amount_pct": 0.9, "oss_mega_count_pct": 0.9,
        "ap_active_buy_pct": 0.9, "ap_unilateral_intensity": 0.9,
        "pd_max_price_impact_pct": 0.9, "pi_time_concentration": 0.9,
        "obp_big_quote_share": 0.9, "rs_interval_cv": 0.9,
        "oss_small_amount_pct": 0.1, "rs_burst_ratio": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert label == YOUZI
    assert scores[0] == max(scores)


def test_quant_wins_on_machine_rhythm():
    # Small + dense burst + LOW interval CV + balanced -> 量化.
    feat = _base()
    feat.update({
        "oss_small_amount_pct": 0.9, "rs_burst_ratio": 0.9,
        "rs_interval_cv": 0.1, "ap_unilateral_intensity": 0.1,
        "pi_time_concentration": 0.1,
    })
    label, _ = score_capital_type(feat)
    assert label == QUANT


def test_retail_wins_when_youzi_and_quant_both_weak():
    # Small orders, NO cadence (high CV, low burst), low aggression, diffuse.
    feat = _base()
    feat.update({
        "oss_small_amount_pct": 0.7, "rs_interval_cv": 0.7,
        "rs_burst_ratio": 0.2, "ap_unilateral_intensity": 0.2,
        "pi_time_concentration": 0.2,
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL
    assert scores[2] == max(scores)


def test_retail_guard_suppresses_residual_for_balanced_quant():
    # The critical guard: same retail-ish base as above, but bump the rhythm to a
    # machine cadence (high burst, low interval CV). 量化 now clears the gate, so
    # 散户 is suppressed even though its raw residual score is non-trivial.
    feat = _base()
    feat.update({
        "oss_small_amount_pct": 0.7, "rs_interval_cv": 0.2,
        "rs_burst_ratio": 0.9, "ap_unilateral_intensity": 0.2,
        "pi_time_concentration": 0.2,
    })
    label, scores = score_capital_type(feat)
    assert label == QUANT, f"balanced quant day leaked into retail: {scores}"


def test_gate_boundary_youzi_above_suppresses_retail():
    # 游资 just CLEARS the gate (score > NEUTRAL + RETAIL_GATE_MARGIN); 量化 weak.
    # A real signal above the gate makes 散户 ineligible, so the arg-max is between
    # 游资/量化 only — never the residual.
    gate = NEUTRAL + RETAIL_GATE_MARGIN
    feat = _base()
    feat.update({
        "oss_mega_amount_pct": 0.56, "oss_mega_count_pct": 0.56,
        "ap_active_buy_pct": 0.56, "ap_unilateral_intensity": 0.56,
        "pd_max_price_impact_pct": 0.56, "pi_time_concentration": 0.56,
        "obp_big_quote_share": 0.56, "rs_interval_cv": 0.56,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.2,
    })
    label, scores = score_capital_type(feat)
    assert scores[0] > gate          # 游资 just above the gate
    assert scores[1] <= gate         # 量化 weak
    assert label != RETAIL           # residual suppressed
    assert label == YOUZI


def test_gate_boundary_quant_above_suppresses_retail_even_when_residual_is_max():
    # 量化 just clears the gate; 游资 weak. Here the RAW 散户 score is the highest of
    # the three, yet the guard still suppresses it: any real signal above the gate
    # makes 散户 ineligible, so 量化 wins. This is the guard's whole reason to exist.
    gate = NEUTRAL + RETAIL_GATE_MARGIN
    feat = _base()
    feat.update({
        "oss_small_amount_pct": 0.57, "rs_burst_ratio": 0.57,
        "rs_interval_cv": 0.43, "ap_unilateral_intensity": 0.43,
        "oss_mega_amount_pct": 0.1, "oss_mega_count_pct": 0.1,
        "ap_active_buy_pct": 0.1, "pd_max_price_impact_pct": 0.1,
        "pi_time_concentration": 0.1, "obp_big_quote_share": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert scores[1] > gate          # 量化 just above the gate
    assert scores[0] <= gate         # 游资 weak
    assert scores[2] == max(scores)  # 散户 raw score is the highest...
    assert label == QUANT            # ...but suppressed; 量化 wins


def test_gate_boundary_score_exactly_at_gate_keeps_retail_eligible():
    # The <= boundary: 量化 sits EXACTLY on the gate (0.55) and 游资 is below it, so
    # 散户 stays eligible (the gate test is <=, not <). With 散户 the raw arg-max it
    # wins. Were the guard a strict <, 量化-at-gate would suppress 散户 and 量化 would
    # win instead — so this case pins the boundary semantics.
    gate = NEUTRAL + RETAIL_GATE_MARGIN
    feat = _base()
    feat.update({
        "oss_small_amount_pct": 0.875, "rs_burst_ratio": 0.375,
        "rs_interval_cv": 0.75, "ap_unilateral_intensity": 0.25,
        "pi_time_concentration": 0.125,
        "oss_mega_amount_pct": 0.1, "oss_mega_count_pct": 0.1,
        "ap_active_buy_pct": 0.1, "pd_max_price_impact_pct": 0.1,
        "obp_big_quote_share": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert scores[1] == gate         # 量化 exactly on the gate boundary
    assert scores[0] <= gate         # 游资 at/below the gate
    assert scores[2] == max(scores)  # 散户 is the raw arg-max
    assert label == RETAIL           # <= keeps it eligible -> it wins


def test_absent_cb_dims_vote_neutral():
    # With no cancel table, CB dims (cb_sell_cancel_ratio / cb_fast_cancel_ratio)
    # must not tilt the result. Injecting a stray CB value while cb_available=0
    # leaves the label unchanged from the CB-free baseline.
    feat = _base()
    label_no_cb, scores_no_cb = score_capital_type(feat)
    feat["cb_sell_cancel_ratio"] = 1.0  # would scream 游资 if it counted
    feat["cb_fast_cancel_ratio"] = 1.0
    label_stray, scores_stray = score_capital_type(feat)
    assert label_stray == label_no_cb
    assert scores_stray == scores_no_cb


def test_confidence_is_top1_minus_top2_margin():
    # Decisive 游资 day -> large margin; near-tie -> small margin.
    feat = _base()
    feat.update({"oss_mega_amount_pct": 0.95, "oss_mega_count_pct": 0.95,
                 "ap_active_buy_pct": 0.95, "ap_unilateral_intensity": 0.95,
                 "pd_max_price_impact_pct": 0.95, "pi_time_concentration": 0.95,
                 "obp_big_quote_share": 0.95, "rs_interval_cv": 0.95})
    _, scores = score_capital_type(feat)
    conf = _capital_confidence(scores)
    top1, top2 = sorted(scores, reverse=True)[:2]
    assert conf == max(0.0, top1 - top2)
    assert 0.0 <= conf <= 1.0


def test_intention_gate_unchanged():
    buy = {"ap_active_buy_pct": 0.7, "book_imbalance": 0.5, "obp_imbalance_mean": 0.5}
    sell = {"ap_active_sell_pct": 0.7, "book_imbalance": -0.5, "obp_imbalance_mean": -0.5}
    flat = {"ap_active_buy_pct": 0.5, "ap_active_sell_pct": 0.5}
    assert get_intention(buy) == "买入"
    assert get_intention(sell) == "卖出"
    assert get_intention(flat) == "T0交易"
