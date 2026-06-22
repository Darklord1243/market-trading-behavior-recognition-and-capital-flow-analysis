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
    RETAIL_WIN_MARGIN,
    get_intention,
    score_capital_type,
)

YOUZI, QUANT, RETAIL = config.CAPITAL_TYPES  # index 0/1/2


def _base():
    """A neutral-ish feature dict (snapshot-only: no cancel table)."""
    return {
        "oss_mega_amount_pct": 0.2, "oss_mega_count_pct": 0.2,
        "oss_small_amount_pct": 0.2, "oss_small_count_pct": 0.2,
        "ap_active_buy_pct": 0.5,
        "ap_unilateral_intensity": 0.2, "pd_max_price_impact_pct": 0.2,
        "pi_time_concentration": 0.2, "obp_big_quote_share": 0.2,
        "rs_interval_cv": 0.2, "rs_burst_ratio": 0.2, "cb_available": 0.0,
        "trd_size_entropy": 0.2,    # NEW (B.2): neutral-ish, matches other base dims
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
    # Diffuse retail with both real classes weak: high small-count, few mega, neutral
    # cancel (no cancel table). 散户 beats both by margin -> wins.
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.9, "oss_mega_count_pct": 0.05,
        "ap_unilateral_intensity": 0.2, "pi_time_concentration": 0.2,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.2, "rs_interval_cv": 0.3,
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL
    assert scores[2] == max(scores)


def test_balanced_quant_not_stolen_by_retail():
    # Retail-ish count profile, but strong machine evidence (small-amount, burst, low
    # CV, balanced, HIGH fast-cancel). 量化 dominates; 散户 fails the win margin.
    feat = _base()
    feat.update({
        "cb_available": 1.0,
        "oss_small_count_pct": 0.8, "oss_mega_count_pct": 0.1,
        "cb_fast_cancel_ratio": 0.9,            # HIGH -> 量化; LOW-supports -> hurts 散户
        "oss_small_amount_pct": 0.9, "rs_burst_ratio": 0.9,
        "rs_interval_cv": 0.1, "ap_unilateral_intensity": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert label == QUANT, f"balanced quant leaked into retail: {scores}"


def test_strong_youzi_beats_close_retail():
    # 游资 strong; 散户 substantial but does NOT beat 游资 by the win margin -> 游资 wins.
    # (Under the old absolute gate this also resolved to 游资, but here the reason is the
    # RELATIVE margin: score_rt < score_yz, so 散户 is ineligible.)
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.6, "oss_mega_count_pct": 0.2,
        "oss_mega_amount_pct": 0.8, "ap_active_buy_pct": 0.8,
        "ap_unilateral_intensity": 0.8, "pd_max_price_impact_pct": 0.8,
        "pi_time_concentration": 0.8, "obp_big_quote_share": 0.8,
        "rs_interval_cv": 0.8,
    })
    label, scores = score_capital_type(feat)
    assert label == YOUZI
    assert scores[2] < max(scores[0], scores[1]) + RETAIL_WIN_MARGIN


def test_retail_max_but_within_margin_yields_runner_up():
    # 散户 is the RAW arg-max but only by < RETAIL_WIN_MARGIN over 量化 -> ineligible ->
    # 量化 (the runner-up) wins. Pins the relative-margin semantics from the other side.
    #
    # B.2 re-derivation: DIMS_RETAIL now has 4 dims. trd_size_entropy is set to the
    # OLD 3-dim score_rt value (~0.7833) so the 4-dim mean equals the old 3-dim mean,
    # preserving the boundary:
    #   score_rt = (0.95 + 0.90 + 0.5 + 0.7833) / 4 ≈ 0.783 (same as old 3-dim)
    #   score_qt = (0.8 + 0.8 + 0.8 + 0.8 + 0.5) / 5 = 0.74
    #   margin ≈ 0.783 - 0.74 = 0.043 < 0.05 → 量化 wins
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.95, "oss_mega_count_pct": 0.10,   # retail ~0.783
        "oss_small_amount_pct": 0.8, "rs_burst_ratio": 0.8,
        "rs_interval_cv": 0.2, "ap_unilateral_intensity": 0.2,     # quant ~0.74
        "trd_size_entropy": 0.7833,  # re-pin: preserves old 3-dim score_rt as 4-dim mean
    })
    label, scores = score_capital_type(feat)
    assert scores[2] == max(scores)                                # 散户 is raw max
    margin = scores[2] - max(scores[0], scores[1])
    assert 0.0 < margin < RETAIL_WIN_MARGIN                        # ...but within margin
    assert label == QUANT                                          # runner-up wins


def test_retail_wins_at_exact_win_margin():
    # Boundary: score_rt sits exactly at max(others)+RETAIL_WIN_MARGIN. The guard uses
    # >=, so 散户 stays eligible and wins. (If float representation makes this ambiguous,
    # nudge oss_small_count_pct up by 0.001 — the point is to pin the >= boundary.)
    #
    # B.2 re-derivation: DIMS_RETAIL now has 4 dims. trd_size_entropy is set to the
    # OLD 3-dim score_rt value (0.75) so the 4-dim mean equals the old 3-dim mean:
    #   score_rt = (0.90 + 0.85 + 0.5 + 0.75) / 4 = 0.75
    #   score_qt = (0.75 + 0.75 + 0.75 + 0.75 + 0.5) / 5 = 0.70
    #   margin = 0.75 - 0.70 = 0.05 = RETAIL_WIN_MARGIN → eligible → 散户 wins
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.90, "oss_mega_count_pct": 0.15,   # retail = 0.75
        "oss_small_amount_pct": 0.75, "rs_burst_ratio": 0.75,
        "rs_interval_cv": 0.25, "ap_unilateral_intensity": 0.25,   # quant = 0.70
        "trd_size_entropy": 0.75,  # re-pin: preserves old 3-dim score_rt as 4-dim mean
    })
    label, scores = score_capital_type(feat)
    assert scores[2] == max(scores)
    assert label == RETAIL


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


def test_retail_wins_on_limit_down_diffuse_flow():
    # The B.0 target case: a diffuse limit-down retail name. High small-order COUNT
    # share, few mega prints, low fast-cancel — but HIGH unilateral intensity (one-
    # sided limit-down). Under the OLD absolute gate, score_yz clears NEUTRAL+0.05
    # and VETOES 散户 -> 游资. Under the new relative win-margin guard, 散户 beats both
    # alternatives by > margin and wins. This test FAILS on the current code.
    #
    # B.2 re-derivation: DIMS_RETAIL now has 4 dims. trd_size_entropy is set to the
    # OLD 3-dim score_rt value (~0.933) so the 4-dim mean equals the old 3-dim mean,
    # preserving the large win margin over 游资 and 量化:
    #   score_rt = (0.95 + 0.90 + 0.95 + 0.933) / 4 ≈ 0.933
    #   score_yz ≈ 0.656, score_qt ≈ 0.15 → 散户 wins by large margin
    feat = _base()
    feat.update({
        "cb_available": 1.0,
        "oss_small_count_pct": 0.95, "oss_mega_count_pct": 0.10,
        "cb_fast_cancel_ratio": 0.05,
        # one-sided limit-down character feeds 游资 high / 量化 low:
        "oss_mega_amount_pct": 0.7, "ap_active_buy_pct": 0.7,
        "ap_unilateral_intensity": 0.9, "pd_max_price_impact_pct": 0.7,
        "pi_time_concentration": 0.7, "obp_big_quote_share": 0.7,
        "rs_interval_cv": 0.7, "cb_sell_cancel_ratio": 0.7,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.1,
        "trd_size_entropy": 0.933,  # re-pin: preserves old 3-dim score_rt as 4-dim mean
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL, f"limit-down retail misclassified: {scores}"
    assert scores[2] == max(scores)
    # The discriminator vs the old guard: 游资 is ABOVE the old absolute gate (0.55),
    # so the old code would have vetoed 散户. Pin that so a revert is caught.
    assert scores[0] > 0.55
