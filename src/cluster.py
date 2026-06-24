"""Task-1 bounded-K clustering + centroid-driven pattern naming (Phase 5 P5.1).

Replaces the stub _choose_k (fixed DEFAULT_K clamp) and fixed-predicate naming with:
  1. Rank-normalization of the feature matrix via normalize_matrix (H1 seam).
  2. Bounded-K sweep over config.K_RANGE: fit KMeans at each feasible k, score by
     silhouette (tie-break Calinski-Harabasz), select the best k.
  3. Centroid-driven open-vocabulary naming: dominant (and weakest) feature axes of
     each cluster centroid map to a finance-grounded Chinese (pattern_type, explanation).

Deferred (Task 5 note): DTW / tslearn.TimeSeriesKMeans and HDBSCAN are NOT implemented
here. They are deferred because no offline-installed, network-free implementation is
available in the conda base environment; tslearn is explicitly forbidden (network pull
at runtime). The bounded-K KMeans sweep on the rank-normalized matrix is used as the
metric-aligned proxy.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, silhouette_score

from config import K_RANGE, RANDOM_SEED
from src.normalize import normalize_matrix

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Centroid-driven naming vocabulary
# ---------------------------------------------------------------------------
# Each entry is (pattern_type, high_features, low_features, explanation_template).
# high_features: feature substrings whose centroid rank should be high (≥ threshold).
# low_features:  feature substrings whose centroid rank should be low.
# The FIRST entry whose high_features all score above HIGH_THRESH (and low_features
# all score below LOW_THRESH) wins; fallback is always last.
# This list is a seed lexicon — selection is driven by which features actually
# dominate the centroid (centroid-driven, not rigid AND-predicate on exact keys).

HIGH_THRESH = 0.60   # centroid rank considered "high" in normalized [0,1] space
LOW_THRESH  = 0.40   # centroid rank considered "low"

FALLBACK_PATTERN_TYPE = "机构长线配置"
FALLBACK_EXPLANATION  = "各特征无明显极值方向，推断为机构长线低调建仓或均衡持仓"

# (pattern_type, high_substrings, low_substrings, explanation)
_CENTROID_RULES: list[tuple[str, list[str], list[str], str]] = [
    (
        "游资强势连板拉升",
        ["mega_amount_pct", "active_buy_pct", "time_concentration"],
        [],
        "超大单占比高、主动买入比例高、尾盘/开盘成交集中，符合游资短线强势拉升特征",
    ),
    (
        "量化高频T0套利",
        ["small_amount_pct", "burst_ratio"],
        [],
        "小单占比高、成交节奏密集，买卖方向均衡，符合量化高频日内套利特征",
    ),
    (
        "主力资金吸筹建仓",
        ["active_net_direction", "book_imbalance", "large_amount_pct"],
        [],
        "大单净买入主导、盘口买盘占优，符合主力资金低调吸筹建仓特征",
    ),
    (
        "盘口诱多撤单",
        ["big_quote_share"],
        ["active_buy_pct"],
        "大额挂单占比高但主动买入偏弱，疑似盘口诱多撤单操作",
    ),
    (
        "散户情绪跟风买入",
        ["active_buy_pct"],
        ["mega_amount_pct", "large_amount_pct"],
        "主动买入比例较高但大单占比低，符合散户跟风情绪买入特征",
    ),
    (
        "对敲洗盘压制",
        ["small_amount_pct"],
        ["book_imbalance", "active_net_direction"],
        "小单频繁、盘口方向模糊，疑似对敲洗盘或压制出货",
    ),
]


def _centroid_to_name(centroid: dict[str, float]) -> tuple[str, str]:
    """Map a centroid mean-feature dict to (pattern_type, explanation).

    Pure function of centroid values (no randomness, deterministic). Iterates
    the lexicon and returns the first rule whose high-feature substrings all
    score >= HIGH_THRESH and low-feature substrings all score <= LOW_THRESH
    in the centroid. Falls back to FALLBACK_PATTERN_TYPE if no rule matches.

    Parameters
    ----------
    centroid : dict[str, float]
        Mean of member rows in normalized [0,1] feature space.
    """
    for pattern_type, high_subs, low_subs, explanation in _CENTROID_RULES:
        high_vals = [v for k, v in centroid.items() if any(s in k for s in high_subs)]
        low_vals  = [v for k, v in centroid.items() if any(s in k for s in low_subs)]

        high_ok = all(v >= HIGH_THRESH for v in high_vals) if high_vals else False
        low_ok  = all(v <= LOW_THRESH  for v in low_vals)  if low_vals  else True

        if high_ok and low_ok:
            # Build a terse explanation augmented with the actual dominant feature
            dominant = max(
                ((k, v) for k, v in centroid.items() if v == v),  # skip NaN
                key=lambda kv: kv[1],
                default=("unknown", 0.0),
            )
            short_dom = dominant[0].replace("_", " ")[:30]
            aug = f"（主导特征: {short_dom}）"
            # Keep total ≤ 200 chars
            base = explanation
            full = base + aug if len(base) + len(aug) <= 200 else base
            return pattern_type, full

    # Fallback: describe the actual dominant axis so the explanation is non-empty
    if centroid:
        dominant = max(centroid.items(), key=lambda kv: kv[1])
        dom_name = dominant[0].replace("_", " ")[:30]
        explanation = f"{FALLBACK_EXPLANATION}（实际主导: {dom_name}）"
        # Guard length
        if len(explanation) > 200:
            explanation = FALLBACK_EXPLANATION[:197] + "..."
    else:
        explanation = FALLBACK_EXPLANATION

    return FALLBACK_PATTERN_TYPE, explanation


def _sweep_k(X: np.ndarray, k_range: tuple[int, int] | None = None) -> int:
    """Select the best K in k_range using silhouette (tie-break Calinski-Harabasz).

    Parameters
    ----------
    X : np.ndarray
        Feature matrix (already normalized), shape (n_samples, n_features).
    k_range : (min_k, max_k) inclusive, default config.K_RANGE.
        Enables tests to plant a known K inside a custom range.

    Returns
    -------
    int
        Best k; falls back to 1 if no feasible k>=2 exists.
    """
    if k_range is None:
        k_range = K_RANGE

    n = X.shape[0]
    lo, hi = k_range
    # Clamp sweep range to feasible [2, n-1] (silhouette needs k < n)
    lo_eff = max(lo, 2)
    hi_eff = min(hi, n - 1)

    if lo_eff > hi_eff:
        log.info("No feasible k>=2 in range %s for n=%d; using K=1", k_range, n)
        return 1

    best_k = lo_eff
    best_sil = -2.0
    best_ch = 0.0

    for k in range(lo_eff, hi_eff + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(X)
        # silhouette_score requires at least 2 distinct labels
        if len(np.unique(labels)) < 2:
            continue
        sil = silhouette_score(X, labels)
        ch  = calinski_harabasz_score(X, labels)

        if sil > best_sil or (sil == best_sil and ch > best_ch):
            best_sil = sil
            best_ch  = ch
            best_k   = k

    log.info("K sweep %s → best K=%d (sil=%.4f, CH=%.1f)", k_range, best_k, best_sil, best_ch)
    return best_k


def cluster_patterns(
    matrix: pd.DataFrame,
    k_range: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Cluster (stock, day) rows and assign an interpretable pattern per row.

    Applies rank-normalization (normalize_matrix) before clustering to make
    features cross-sectionally comparable in [0,1] space.

    Parameters
    ----------
    matrix : pd.DataFrame
        Feature matrix; rows are (stock, day) observations.
    k_range : (min_k, max_k) inclusive, optional.
        Override the K sweep range; default is config.K_RANGE.
        Exposed here so callers (mainly tests) can plant a known K.

    Returns
    -------
    pd.DataFrame
        Same index as `matrix`; columns: pattern_type, pattern_explanation.
    """
    n = len(matrix)
    feats = matrix.select_dtypes("number").fillna(0.0)

    # --- Rank-normalize (H1 dependency) ---
    normed = normalize_matrix(feats).select_dtypes("number").fillna(0.0)
    X = normed.values

    # --- K=1 fast path ---
    if n <= 1:
        log.info("n=%d ≤ 1; K=1 path", n)
        labels = np.zeros(n, dtype=int)
    else:
        k = _sweep_k(X, k_range=k_range)
        if k <= 1:
            labels = np.zeros(n, dtype=int)
        else:
            km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
            labels = km.fit_predict(X)
            log.info("KMeans: %d clusters over %d samples", k, n)

    # --- Centroid-driven naming ---
    records: list[tuple[int, str, str]] = []
    col_names = list(normed.columns)

    for cid in np.unique(labels):
        members = normed.values[labels == cid]
        centroid_mean = members.mean(axis=0)
        centroid_dict = {col: float(centroid_mean[i]) for i, col in enumerate(col_names)}
        name, explanation = _centroid_to_name(centroid_dict)
        records.append((cid, name, explanation))

    name_map = {cid: (nm, ex) for cid, nm, ex in records}

    out = pd.DataFrame(
        {
            "pattern_type": [name_map[c][0] for c in labels],
            "pattern_explanation": [name_map[c][1] for c in labels],
        },
        index=matrix.index,
    )
    log.info("pattern distribution: %s", out["pattern_type"].value_counts().to_dict())
    return out
