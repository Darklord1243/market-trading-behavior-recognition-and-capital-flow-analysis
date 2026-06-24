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
from src.normalize import normalize_matrix, EXCLUDE

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Centroid-driven naming vocabulary (P5.1b: relative dominance)
# ---------------------------------------------------------------------------
# Naming is driven by RELATIVE dominance: for each cluster, the dominant feature
# is argmax(centroid_mean - global_mean), i.e. the feature on which this cluster
# sits furthest ABOVE the cross-sectional average.  A single-feature substring
# lexicon maps that dominant feature to a finance-grounded Chinese label.

FALLBACK_PATTERN_TYPE = "机构长线配置"
FALLBACK_EXPLANATION  = "各特征无明显极值方向，推断为机构长线低调建仓或均衡持仓"

# Single-feature substring lexicon: list of (substring, pattern_type, explanation_template).
# The explanation_template uses {feat} as a placeholder for the actual dominant feature name.
# Order matters only as a priority fallback when multiple substrings could match the same
# feature name (first match wins).  Fallback is 机构长线配置.
_SUBSTR_LEXICON: list[tuple[str, str, str]] = [
    (
        "mega_amount",
        "游资强势拉升",
        "超大单占比显著高于市场均值（主导特征: {feat}），符合游资短线强势拉升特征",
    ),
    (
        "mega_count",
        "游资强势拉升",
        "超大单笔数显著高于市场均值（主导特征: {feat}），符合游资短线强势拉升特征",
    ),
    (
        "large_amount",
        "主力资金吸筹建仓",
        "大单占比显著高于市场均值（主导特征: {feat}），符合主力资金低调吸筹建仓特征",
    ),
    (
        "active_net_direction",
        "主力资金吸筹建仓",
        "主动净买入方向显著偏多（主导特征: {feat}），符合主力资金定向建仓特征",
    ),
    (
        "book_imbalance",
        "主力资金吸筹建仓",
        "盘口买卖挂单失衡显著（主导特征: {feat}），符合主力吸筹盘口特征",
    ),
    (
        "small_amount",
        "量化高频T0套利",
        "小单占比显著高于市场均值（主导特征: {feat}），符合量化高频日内套利特征",
    ),
    (
        "burst_ratio",
        "高频脉冲交易",
        "成交节奏脉冲比率显著高于市场均值（主导特征: {feat}），符合高频脉冲交易特征",
    ),
    (
        "active_buy",
        "买盘主动占优",
        "主动买入比例显著高于市场均值（主导特征: {feat}），买盘力量占主导",
    ),
    (
        "active_sell",
        "卖压主动出货",
        "主动卖出比例显著高于市场均值（主导特征: {feat}），卖压主动出货特征明显",
    ),
    (
        "cb_buy_cancel",
        "盘口撤单博弈",
        "买方撤单频率显著高于市场均值（主导特征: {feat}），盘口撤单博弈明显",
    ),
    (
        "cb_sell_cancel",
        "盘口撤单博弈",
        "卖方撤单频率显著高于市场均值（主导特征: {feat}），盘口撤单博弈明显",
    ),
    (
        "cancel",
        "盘口撤单博弈",
        "撤单行为显著高于市场均值（主导特征: {feat}），盘口撤单博弈明显",
    ),
    (
        "big_quote_share",
        "盘口诱多挂单",
        "大额挂单占比显著高于市场均值（主导特征: {feat}），疑似盘口诱多挂单操作",
    ),
    (
        "time_concentration",
        "尾盘/开盘成交集中",
        "成交时间集中度显著高于市场均值（主导特征: {feat}），符合尾盘或开盘集中交易特征",
    ),
]


def _dominant_feature_to_name(dominant_feat: str, delta_val: float) -> tuple[str, str]:
    """Map a single dominant feature name to (pattern_type, explanation).

    Uses substring matching on the lexicon; first match wins.
    Falls back to FALLBACK_PATTERN_TYPE if no substring matches.

    Parameters
    ----------
    dominant_feat : str
        Column name of the feature with the highest (centroid - global_mean) delta.
    delta_val : float
        The actual delta value (for context in explanations, not used currently).
    """
    feat_display = dominant_feat.replace("_", " ")[:40]
    for substr, pattern_type, explanation_tpl in _SUBSTR_LEXICON:
        if substr in dominant_feat:
            explanation = explanation_tpl.format(feat=feat_display)
            # Guard ≤ 200 chars
            if len(explanation) > 200:
                explanation = explanation[:197] + "..."
            return pattern_type, explanation

    # Fallback
    explanation = f"{FALLBACK_EXPLANATION}（实际主导: {feat_display}）"
    if len(explanation) > 200:
        explanation = FALLBACK_EXPLANATION[:197] + "..."
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

    # Drop EXCLUDE columns (imported from src.normalize — not hard-coded) so that
    # raw-scale columns like n_ticks (~thousands) do not dominate Euclidean distance
    # in KMeans, and do not appear as dominant features in centroid naming.
    clustering_feats = normed.drop(columns=[c for c in EXCLUDE if c in normed.columns])
    X = clustering_feats.values

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

    # --- Centroid-driven naming (uses clustering_feats, not normed, so EXCLUDE cols
    #     are invisible to argmax and lexicon matching) ---
    col_names = list(clustering_feats.columns)

    # P5.1b: compute global mean over ALL rows for relative dominance naming
    global_mean_arr = clustering_feats.values.mean(axis=0) if n > 0 else np.zeros(len(col_names))
    global_mean_dict = {col: float(global_mean_arr[i]) for i, col in enumerate(col_names)}

    # First pass: assign each cluster its primary relative-dominant label
    unique_cids = list(np.unique(labels))
    # Per-cluster info: centroid dict and sorted delta list (descending by delta value)
    cluster_info: dict[int, tuple[dict[str, float], list[tuple[str, float]]]] = {}
    for cid in unique_cids:
        members = clustering_feats.values[labels == cid]
        centroid_mean = members.mean(axis=0)
        centroid_dict = {col: float(centroid_mean[i]) for i, col in enumerate(col_names)}
        # Delta vs global mean, sorted descending by delta value
        delta_sorted = sorted(
            ((col, centroid_dict[col] - global_mean_dict[col]) for col in col_names),
            key=lambda kv: kv[1],
            reverse=True,
        )
        cluster_info[cid] = (centroid_dict, delta_sorted)

    # Assign initial names using the primary dominant feature (axis index 0)
    name_map: dict[int, tuple[str, str]] = {}
    for cid in unique_cids:
        centroid_dict, delta_sorted = cluster_info[cid]
        dominant_feat, dominant_delta = delta_sorted[0]
        name, explanation = _dominant_feature_to_name(dominant_feat, dominant_delta)
        name_map[cid] = (name, explanation)

    # P5.1b: guarantee ≥2 distinct pattern_type when K≥2 (deterministic tie-break)
    # If all K≥2 clusters mapped to the same label, reassign the cluster whose
    # SECONDARY |delta| is largest to its secondary-axis label, repeat until ≥2 distinct
    # (or all secondary axes exhausted).
    if len(unique_cids) >= 2:
        axis_idx = 1  # start at secondary axis
        while len({nm for nm, _ in name_map.values()}) < 2:
            # Find cluster with the largest |delta| at axis_idx
            candidates = []
            for cid in unique_cids:
                _, delta_sorted = cluster_info[cid]
                if axis_idx < len(delta_sorted):
                    feat, dval = delta_sorted[axis_idx]
                    candidates.append((abs(dval), cid, feat, dval))
            if not candidates:
                break  # axes exhausted — cannot diversify further
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, reassign_cid, feat, dval = candidates[0]
            new_name, new_expl = _dominant_feature_to_name(feat, dval)
            name_map[reassign_cid] = (new_name, new_expl)
            axis_idx += 1

    out = pd.DataFrame(
        {
            "pattern_type": [name_map[c][0] for c in labels],
            "pattern_explanation": [name_map[c][1] for c in labels],
        },
        index=matrix.index,
    )
    log.info("pattern distribution: %s", out["pattern_type"].value_counts().to_dict())
    return out
