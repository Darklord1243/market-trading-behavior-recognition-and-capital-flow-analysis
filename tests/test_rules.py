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


# ---------------------------------------------------------------------------
# B.3 — limit-UP regime de-contamination rules tests
# ---------------------------------------------------------------------------

def _limit_up_contaminated_feat():
    """A feature dict that falsely favors 量化 due to limit-up regime contamination.

    The contaminated dims mimic a 游资 stock sealed at the upper limit:
      * rs_interval_cv is LOW (0.05) — mechanically regular sealed-book arrival;
        normally this would be a strong 量化 signal but here it's regime-driven.
      * pd_max_price_impact_pct is LOW (0.05) — price doesn't move when sealed;
        normally this would suppress 游资 but here it's regime-driven.
    Other 游资 dims are modest (not overwhelming), so the two contaminated dims
    tip the balance: score_qt > score_yz without the branch.

    Hand-computed scores (cb_available=0, so CB dims vote NEUTRAL=0.5):

    DIMS_YOUZI (9 dims): oss_mega_amount_pct(T), oss_mega_count_pct(T),
        ap_active_buy_pct(T), ap_unilateral_intensity(T), pd_max_price_impact_pct(T),
        pi_time_concentration(T), obp_big_quote_share(T), rs_interval_cv(T),
        cb_sell_cancel_ratio(CB → NEUTRAL 0.5)
    score_yz = (0.55 + 0.55 + 0.6 + 0.55 + 0.05 + 0.55 + 0.5 + 0.05 + 0.5) / 9
             = 3.9 / 9 ≈ 0.4333

    DIMS_QUANT (5 dims): oss_small_amount_pct(T), rs_burst_ratio(T),
        rs_interval_cv(F), ap_unilateral_intensity(F), cb_fast_cancel_ratio(CB → 0.5)
    score_qt = (0.5 + 0.5 + (1-0.05) + (1-0.55) + 0.5) / 5
             = (0.5 + 0.5 + 0.95 + 0.45 + 0.5) / 5
             = 2.9 / 5 = 0.58

    → score_qt (0.58) > score_yz (0.433) without branch: 量化 wins ✓

    After neutralizing (seal_up >= LIMIT_SEAL_MIN):
      skip_qt = {rs_interval_cv}: score_qt = (0.5 + 0.5 + 0.5 + 0.45 + 0.5) / 5 = 2.45/5 = 0.49
      skip_yz = {pd_max_price_impact_pct}: score_yz = (0.55+0.55+0.6+0.55+0.5+0.55+0.5+0.05+0.5)/9
              = 4.35/9 ≈ 0.483
    → score_yz (0.483) < score_qt (0.49) ... still marginal. Let me adjust further.

    With slightly stronger 游资 dims (0.6 each) and rs_burst_ratio=0.6 for quant:
      score_yz_no_branch = (0.6+0.6+0.65+0.6+0.05+0.6+0.55+0.05+0.5)/9 = 4.2/9 ≈ 0.467
      score_qt_no_branch = (0.5+0.6+(1-0.05)+(1-0.6)+0.5)/5 = (0.5+0.6+0.95+0.4+0.5)/5 = 2.95/5=0.59

    After neutralizing:
      score_qt_corrected = (0.5+0.6+0.5+(1-0.6)+0.5)/5 = (0.5+0.6+0.5+0.4+0.5)/5 = 2.5/5=0.50
      score_yz_corrected = (0.6+0.6+0.65+0.6+0.5+0.6+0.55+0.05+0.5)/9 = 4.65/9 ≈ 0.517

    → score_yz (0.517) > score_qt (0.50) with branch: 游资 wins ✓
    """
    return {
        # 游资-supporting dims (genuine but moderate, not overwhelming)
        "oss_mega_amount_pct": 0.60,
        "oss_mega_count_pct": 0.60,
        "ap_active_buy_pct": 0.65,
        "ap_unilateral_intensity": 0.60,
        "pi_time_concentration": 0.60,
        "obp_big_quote_share": 0.55,
        "rs_interval_cv": 0.05,           # CONTAMINATED: falsely low (sealed book)
        "pd_max_price_impact_pct": 0.05,  # CONTAMINATED: falsely low (price sealed)
        # 量化-supporting dims
        "oss_small_amount_pct": 0.50,
        "rs_burst_ratio": 0.60,
        # 散户 dims (low to keep retail ineligible)
        "oss_small_count_pct": 0.30,
        "trd_size_entropy": 0.20,
        # CB not available
        "cb_available": 0.0,
    }


def test_limit_up_branch_flips_contaminated_to_youzi():
    """B.3.R1 — With seal_up=0.9 (regime-gated), contaminated feat -> 游资.

    The dict's contaminated dims (low rs_interval_cv, low pd_max_price_impact_pct)
    falsely favor 量化 when no limit-up branch is active. With seal_up >= 0.5,
    those dims are neutralized and 游资's other strong evidence wins.

    This is the primary regression guard: if the branch is removed, this FAILS.
    """
    feat = _limit_up_contaminated_feat()
    feat["limit_seal_up_ratio"] = 0.9   # majority sealed -> branch fires

    label, scores = score_capital_type(feat)
    assert label == YOUZI, (
        f"Sealed limit-up contaminated feat must predict 游资; got {label}, scores={scores}"
    )
    assert scores[0] > scores[1], (
        f"score_yz ({scores[0]:.4f}) must exceed score_qt ({scores[1]:.4f}) "
        "after neutralizing contaminated dims"
    )


def test_limit_up_branch_absent_or_below_min_stays_quant():
    """B.3.R2 — Without seal (absent key or < 0.5), contaminated feat stays 量化.

    The identical contaminated dict, WITHOUT limit_seal_up_ratio >= LIMIT_SEAL_MIN,
    must still predict 量化. This proves the branch is regime-GATED, not a blanket
    游资 bias: removing the seal key reverts to the contaminated (wrong) prediction.
    """
    feat_absent = _limit_up_contaminated_feat()
    # No seal key at all
    label_absent, scores_absent = score_capital_type(feat_absent)
    assert label_absent == QUANT, (
        f"Without seal key, contaminated feat must predict 量化 (baseline); "
        f"got {label_absent}, scores={scores_absent}"
    )

    feat_low = _limit_up_contaminated_feat()
    feat_low["limit_seal_up_ratio"] = 0.3   # below LIMIT_SEAL_MIN=0.5
    label_low, scores_low = score_capital_type(feat_low)
    assert label_low == QUANT, (
        f"With seal_up=0.3 (< LIMIT_SEAL_MIN), contaminated feat must still predict 量化; "
        f"got {label_low}, scores={scores_low}"
    )


def test_limit_up_branch_does_not_bias_retail():
    """B.3.R3 — The limit-UP branch must not affect score_rt or the retail guard.

    A strong retail dict with seal_up=0.9 must still win as 散户 (the branch only
    touches score_yz and score_qt, not score_rt or the RETAIL_WIN_MARGIN check).
    """
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.95, "oss_mega_count_pct": 0.05,
        "trd_size_entropy": 0.8,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.2,
        "rs_interval_cv": 0.3, "ap_unilateral_intensity": 0.2,
        "limit_seal_up_ratio": 0.9,   # seal present — should not veto retail
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL, (
        f"Limit-UP branch must not block retail win; got {label}, scores={scores}"
    )


def test_limit_up_branch_exact_min_boundary():
    """B.3.R4 — At seal_up exactly == LIMIT_SEAL_MIN (0.5), branch must fire (>=).

    Uses >= comparison so the boundary is inclusive. This pins the boundary
    semantics so a future change from >= to > would be caught.
    """
    from src.rules import LIMIT_SEAL_MIN
    feat = _limit_up_contaminated_feat()
    feat["limit_seal_up_ratio"] = LIMIT_SEAL_MIN   # exactly at boundary

    label, scores = score_capital_type(feat)
    assert label == YOUZI, (
        f"At seal_up==LIMIT_SEAL_MIN={LIMIT_SEAL_MIN}, branch must fire (>=); "
        f"got {label}, scores={scores}"
    )
