"""Stage-1 soft-rule scorer: 游资 vs 量化机构 + intent gate.

Ports the baseline 11-dimension weighted scoring (baseline-guide.md L388-396) and
the `get_intention()` gate (L400-414) verbatim in behaviour. No labels are used —
this is rule-based discrimination grounded in A-share financial priors:
  * 游资 (hot money): large/aggressive/imbalanced, time-concentrated.
  * 量化机构 (quant): small/frequent/balanced.

These rules never reference a specific stock/date (compliance hard-rule #2) and use
intraday-only features.
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

# 11 normalised dimensions feeding the capital-type score. Each entry maps a feature
# key to whether a HIGH value leans 游资 (hot money). Quant score is the complement.
# Hot-money-leaning indices {large size, active buy, impact, time concentration} are
# the baseline's documented 游资 signals (baseline-guide.md L392).
SCORING_DIMS = [
    ("oss_mega_amount_pct", True),       # 0 large size -> 游资
    ("oss_small_amount_pct", False),     # 1 small size -> 量化
    ("rs_burst_ratio", False),           # 2 rapid even cadence -> 量化
    ("ap_active_buy_pct", True),         # 3 active buy -> 游资
    ("rs_interval_cv", True),            # 4 bursty/irregular -> 游资
    ("pd_max_price_impact_pct", True),   # 5 price impact -> 游资
    ("pi_time_concentration", True),     # 6 time concentration -> 游资
    ("ap_unilateral_intensity", True),   # 7 one-sided pressure -> 游资
    ("obp_big_quote_share", True),       # 8 big resting quotes -> 游资
    ("cb_sell_cancel_ratio", True),      # 9 sell-side cancels (spoofing) -> 游资
    ("oss_mega_count_pct", True),        # 10 large-order frequency -> 游资
]


def _clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def score_capital_type(feat: dict) -> tuple[str, float, float]:
    """Return (capital_type, score_youzi, score_quant).

    Scores are normalised dimension sums; the label is the arg-max, matching the
    baseline's ``return '游资' if score_yz >= score_qt else '量化机构'``.
    """
    score_yz = 0.0
    score_qt = 0.0
    for key, hot_high in SCORING_DIMS:
        v = _clip01(float(feat.get(key, 0.0)))
        if hot_high:
            score_yz += v
            score_qt += (1.0 - v)
        else:
            score_yz += (1.0 - v)
            score_qt += v
    capital_type = CAPITAL_TYPES[0] if score_yz >= score_qt else CAPITAL_TYPES[1]
    return capital_type, score_yz, score_qt


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
