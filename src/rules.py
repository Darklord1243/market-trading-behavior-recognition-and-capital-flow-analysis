"""Stage-1 soft-rule scorer: 游资 vs 量化 vs 散户 + intent gate.

Three-class rule-based discrimination grounded in A-share financial priors:
  * 游资 (hot money): large/aggressive/imbalanced orders, open/close
    time-concentrated, irregular *manual* rhythm.
  * 量化 (quant): small/frequent/balanced orders, machine cadence — LOW
    inter-event interval CV, HIGH burst ratio, high fast-cancel when a cancel
    table is present. Regular, dense, symmetric.
  * 散户 (retail): a guarded RESIDUAL — small orders but LOW order frequency,
    HIGH/irregular interval CV (no cadence), LOW unilateral aggression, diffuse
    timing (no open/close concentration), near-zero burst structure.

IMPORTANT — the 量化/散户 split is RHYTHM-based, not SIZE-based. Both are
small-order classes; what separates them is execution regularity/persistence
(量化 = machine cadence, 散户 = no cadence). Do not "fix" this back to order size.

These rules never reference a specific stock/date (compliance hard-rule #2) and use
intraday-only features. Per-feature normalisation is the existing z-score / rank
form; class weights are 1.0 stubs (equal) — only the dimension *routing* into the
three scores is real here, weight-tuning remains future work.
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

# 散户: retail residual — small orders, NO cadence (HIGH interval CV, LOW burst),
# LOW aggression, diffuse timing (LOW concentration). Inverse-of-aggression AND
# inverse-of-machine-rhythm: weak on every "someone is driving this name" axis.
DIMS_RETAIL = [
    ("oss_small_amount_pct", True, False),    # small-order dominance
    ("rs_interval_cv", True, False),          # HIGH/irregular CV -> no cadence
    ("rs_burst_ratio", False, False),         # LOW -> near-zero burst structure
    ("ap_unilateral_intensity", False, False),# LOW -> low aggression
    ("pi_time_concentration", False, False),  # LOW -> diffuse timing
]

NEUTRAL = 0.5  # an absent feature casts no vote: +0.5 to that class score
# 散户 is a GUARDED residual: it may only win the arg-max when BOTH 游资 and 量化
# are weak (neither score clears NEUTRAL by more than this margin on the same
# normalised scale). This stops a genuinely balanced, high-rhythm quant day (low
# directional imbalance) from falling into retail by default — the single most
# likely failure mode of a naive 3-way. Global constant, not a per-stock value.
RETAIL_GATE_MARGIN = 0.05


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
    散户 is suppressed unless BOTH 游资 and 量化 are weak (§ retail guard); if
    either shows real signal, the arg-max is between those two only. No hard
    thresholds beyond the residual gate — labels are produced in Stage-2.
    """
    cb_available = float(feat.get("cb_available", 0.0)) > 0.0
    score_yz = _class_score(feat, DIMS_YOUZI, cb_available)
    score_qt = _class_score(feat, DIMS_QUANT, cb_available)
    score_rt = _class_score(feat, DIMS_RETAIL, cb_available)
    scores = [score_yz, score_qt, score_rt]

    # Retail guard: 散户 eligible only when neither 游资 nor 量化 has real signal.
    gate = NEUTRAL + RETAIL_GATE_MARGIN
    retail_eligible = (score_yz <= gate) and (score_qt <= gate)
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
