"""Stage-1 soft-rule scorer: 游资 vs 量化 vs 散户 + intent gate.

Three-class rule-based discrimination grounded in A-share financial priors:
  * 游资 (hot money): large/aggressive/imbalanced orders, open/close
    time-concentrated, irregular *manual* rhythm.
  * 量化 (quant): small/frequent/balanced orders, machine cadence — LOW
    inter-event interval CV, HIGH burst ratio, high fast-cancel when a cancel
    table is present. Regular, dense, symmetric.
  * 散户 (retail): diffuse order flow — many small orders by COUNT (not amount),
    few mega prints, and (CB-gated) a LOW fast-cancel rate (retail is not an
    algo). These are the diagnostic-confirmed separators (design spec §1.1);
    requires a positive win margin over BOTH 游资 and 量化 to be assigned.

These rules never reference a specific stock/date (compliance hard-rule #2) and use
intraday-only features. NOTE: there is NO cross-sample normalisation yet — `_class_score`
applies `_clip01(raw)` directly, so any feature outside [0, 1] saturates (e.g.
`rs_interval_cv`). Rank/quantile normalisation across the daily stock panel is the planned
fix (see docs/LIS.md Phase 1, `src/normalize.py`); class weights are 1.0 stubs (equal) —
only the dimension *routing* into the three scores is real here, weight-tuning remains
future work.
"""

from __future__ import annotations

from config import (
    CAPITAL_TYPES,
    IMBALANCE_FULLDAY_WEIGHT,
    IMBALANCE_SNAPSHOT_WEIGHT,
    INTENT_BUY_PCT,
    INTENT_IMBALANCE,
    INTENT_SELL_PCT,
    INTENTION_CLASSES,
)

# Per-class scoring dimensions. Each entry: (feature_key, high_supports, is_cb).
#   high_supports=True  -> a HIGH normalised value supports the class (add v)
#   high_supports=False -> a LOW  normalised value supports the class (add 1 - v)
#   is_cb=True          -> Cancel-Behaviour dim, valid ONLY when a tick-cancel
#                          table is present (cb_available); otherwise absent.
# An absent dim votes NEUTRALLY (+0.5) so it never tilts a class score.

# 游资: mega/large dominance, active-buy aggression, price impact, big resting
# quotes, open/close concentration, sell-side spoofing cancels, and irregular
# *manual* rhythm (high interval CV).
DIMS_YOUZI = [
    ("oss_mega_amount_pct", True, False),     # mega-order size dominance
    ("oss_mega_count_pct", True, False),      # mega-order frequency
    ("ap_active_buy_pct", True, False),       # active-buy aggression
    ("ap_unilateral_intensity", True, False), # one-sided book pressure
    ("pd_max_price_impact_pct", True, False), # price impact
    ("pi_time_concentration", True, False),   # open/close time concentration
    ("obp_big_quote_share", True, False),     # big resting quotes
    ("rs_interval_cv", True, False),          # irregular manual rhythm
    ("cb_sell_cancel_ratio", True, True),     # sell-side cancels (spoofing) [CB]
]

# 量化: small frequent orders, machine cadence (LOW interval CV, HIGH burst),
# two-sided balance (LOW unilateral intensity), high fast-cancel [CB].
DIMS_QUANT = [
    ("oss_small_amount_pct", True, False),    # small-order dominance
    ("rs_burst_ratio", True, False),          # dense burst cadence
    ("rs_interval_cv", False, False),         # LOW CV -> regular machine cadence
    ("ap_unilateral_intensity", False, False),# LOW -> two-sided / balanced
    ("cb_fast_cancel_ratio", True, True),     # fast cancels (HFT) [CB]
]

# 散户: retail DIFFUSENESS — positive signal (not an inverse residual). Many small
# orders by COUNT, few mega prints, heterogeneous (non-clipped) trade-size distribution,
# and (CB-gated) a LOW fast-cancel rate (retail is not an algo). These are the
# diagnostic-confirmed separators (see design spec §1.1); the old rhythm/inverse dims
# (rs_*, ap_unilateral LOW, oss_small_amount) were dead or anti-signal on the real
# cross-section and were removed.
DIMS_RETAIL = [
    ("oss_small_count_pct", True, False),     # many small orders by count
    ("oss_mega_count_pct", False, False),     # few mega prints
    ("cb_fast_cancel_ratio", False, True),    # retail rarely fast-cancels [CB]
    ("trd_size_entropy", True, False),        # heterogeneous human print sizes (B.2)
]

NEUTRAL = 0.5  # an absent feature casts no vote: +0.5 to that class score
# 散户 wins only when its OWN evidence beats BOTH 游资 and 量化 by this margin (a
# RELATIVE win margin, not an absolute veto). This preserves the "no accidental
# residual win" hedge while removing the obsolete absolute gate, which mis-fired on
# limit-down names (high ap_unilateral_intensity pushed score_yz above the old gate
# and vetoed a genuine 散户). OQ-1 resolved the 3-class question, so the absolute
# hedge is no longer needed. Global constant; value carried from the old gate margin
# and is NOT fitted to labels.
RETAIL_WIN_MARGIN = 0.05


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _class_score(feat: dict, dims: list, cb_available: bool) -> float:
    """Mean normalised vote across a class's dimensions, in [0, 1].

    Absent dims (missing/NaN key, or a CB dim with no cancel table) vote NEUTRAL
    so the score stays comparable across classes regardless of dim count.
    """
    total = 0.0
    for key, high_supports, is_cb in dims:
        raw = feat.get(key, None)
        absent = (raw is None) or (raw != raw) or (is_cb and not cb_available)
        if absent:
            total += NEUTRAL
            continue
        v = _clip01(float(raw))
        total += v if high_supports else (1.0 - v)
    return total / len(dims)


def score_capital_type(feat: dict) -> tuple[str, list]:
    """Return (capital_type, [score_youzi, score_quant, score_retail]).

    Three continuous class scores (each in [0, 1]) and their guarded arg-max.
    散户 wins only when score_rt beats BOTH 游资 and 量化 by RETAIL_WIN_MARGIN;
    otherwise the arg-max is between 游资/量化 only. No per-stock thresholds —
    labels are produced in Stage-2.
    """
    cb_available = float(feat.get("cb_available", 0.0)) > 0.0
    score_yz = _class_score(feat, DIMS_YOUZI, cb_available)
    score_qt = _class_score(feat, DIMS_QUANT, cb_available)
    score_rt = _class_score(feat, DIMS_RETAIL, cb_available)
    scores = [score_yz, score_qt, score_rt]

    # Retail guard (relative): 散户 eligible only when its score beats BOTH 游资 and
    # 量化 by RETAIL_WIN_MARGIN. Otherwise the arg-max is between 游资/量化 only.
    retail_eligible = score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN
    eligible = [0, 1, 2] if retail_eligible else [0, 1]

    best = max(eligible, key=lambda i: scores[i])
    return CAPITAL_TYPES[best], scores


def get_intention(feat: dict) -> str:
    """Intent gate (baseline get_intention, verbatim thresholds).

    Dual-source book imbalance = 0.4*first-snapshot + 0.6*full-day mean.
    """
    buy_pct = feat.get("ap_active_buy_pct", 0.5)
    sell_pct = feat.get("ap_active_sell_pct", 0.5)
    imbalance = (
        IMBALANCE_SNAPSHOT_WEIGHT * feat.get("book_imbalance", 0.0)
        + IMBALANCE_FULLDAY_WEIGHT * feat.get("obp_imbalance_mean", 0.0)
    )
    if buy_pct > INTENT_BUY_PCT and imbalance > INTENT_IMBALANCE:
        return INTENTION_CLASSES[0]   # 买入
    if sell_pct > INTENT_SELL_PCT and imbalance < -INTENT_IMBALANCE:
        return INTENTION_CLASSES[1]   # 卖出
    return INTENTION_CLASSES[2]       # T0交易
