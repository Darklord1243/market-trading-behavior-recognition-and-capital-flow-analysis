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
from scipy.stats import wasserstein_distance
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import calinski_harabasz_score, silhouette_score

import config
from config import (
    K_RANGE,
    RANDOM_SEED,
    TASK1_MIN_CLUSTER_SIZE,
    TASK1_MAX_CLUSTER_SHARE,
)
from src.intraday_trajectory import SUMMARY_COLS, N_SERIES, summary_features
from src.normalize import normalize_matrix, EXCLUDE

# Composite K-sweep weights (P5, Slice 1). Fixed global constants — NOT tuned to
# any label or board score (docs/hypotheses/p5-task1-metric-alignment.md §2.5).
# Euclidean silhouette stays the primary term; the two intraday board components
# (Wasserstein / DTW separation) are equal secondary nudges.
_WASS_WEIGHT = 0.25
_DTW_WEIGHT = 0.25

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


# ---------------------------------------------------------------------------
# Trajectory-shape naming vocabulary (P5.7 — dtw-complete production path)
# ---------------------------------------------------------------------------
# Keyed on (SUMMARY_COL, direction) where direction ∈ {"high","low"} is the SIGN
# of (cluster_centroid − market_mean) on that shape axis.  SUMMARY_COLS is a
# small closed set of 6 intraday PRICE-PATH shape features (from
# src.intraday_trajectory); each axis therefore yields TWO opposed, still
# quantitatively-grounded 行情阶段-flavored names — 12 total, enough to give a
# DISTINCT name to every cluster up to the K=8 sweep ceiling.  The naming step
# (P5.7b) assigns these injectively across a day's clusters, so distinct
# trajectory clusters never collapse into one pattern_type (fixes the P5.7
# n_pat<3 / top_share>0.65 naming degeneracy WITHOUT touching the frozen,
# gated clustering).  {feat} = dominant axis name, {delta} = signed magnitude
# (cluster mean − market mean) so the explanation is literally quantitative.
_TRAJ_SHAPE_NAMES: dict[tuple[str, str], tuple[str, str]] = {
    ("traj_turnover_front_load", "high"): (
        "全天单边拉升",
        "早盘成交占比高出市场均值{delta}（主导轴: {feat}），资金早盘抢筹、全天单边拉升特征",
    ),
    ("traj_turnover_front_load", "low"): (
        "低开缩量筑底",
        "早盘成交占比低于市场均值{delta}（主导轴: {feat}），早盘清淡、缩量筑底特征",
    ),
    ("traj_turnover_back_load", "high"): (
        "尾盘集中放量",
        "尾盘成交占比高出市场均值{delta}（主导轴: {feat}），尾盘集中放量、资金尾市进场特征",
    ),
    ("traj_turnover_back_load", "low"): (
        "高开高走衰竭",
        "尾盘成交占比低于市场均值{delta}（主导轴: {feat}），成交前置、尾盘动能衰竭特征",
    ),
    ("traj_turnover_concentration", "high"): (
        "脉冲式单点爆量",
        "单一时段成交占比高出市场均值{delta}（主导轴: {feat}），脉冲式单点爆量特征",
    ),
    ("traj_turnover_concentration", "low"): (
        "横盘均衡震荡",
        "各时段成交分布低于集中度均值{delta}（主导轴: {feat}），成交均匀、横盘均衡震荡特征",
    ),
    ("traj_imbalance_mean", "high"): (
        "买盘主动控盘",
        "日内盘口失衡均值高出市场{delta}（主导轴: {feat}），买盘主动、主力控盘特征",
    ),
    ("traj_imbalance_mean", "low"): (
        "卖压主导出货",
        "日内盘口失衡均值低于市场{delta}（主导轴: {feat}），卖压主导、持续出货特征",
    ),
    ("traj_imbalance_trend", "high"): (
        "尾盘买盘转强",
        "盘口失衡走势尾盘上行、高出市场{delta}（主导轴: {feat}），尾盘买盘转强特征",
    ),
    ("traj_imbalance_trend", "low"): (
        "尾盘抛压加剧",
        "盘口失衡走势尾盘下行、低于市场{delta}（主导轴: {feat}），尾盘抛压加剧特征",
    ),
    ("traj_return_amplitude", "high"): (
        "冲高回落出货",
        "日内价格波动幅度高出市场均值{delta}（主导轴: {feat}），冲高回落、高位出货特征",
    ),
    ("traj_return_amplitude", "low"): (
        "窄幅缩量整理",
        "日内价格波动幅度低于市场均值{delta}（主导轴: {feat}），窄幅缩量、横盘整理特征",
    ),
}


def _traj_axis_to_name(col: str, delta_val: float) -> tuple[str, str]:
    """Map a (shape axis, signed delta) to (pattern_type, explanation).

    Direction is the sign of *delta_val* (cluster centroid − market mean on this
    axis).  Falls back to FALLBACK_PATTERN_TYPE only if the axis is unrecognised
    (should not happen; SUMMARY_COLS is closed).
    """
    feat_display = col.replace("_", " ")[:40]
    direction = "high" if delta_val >= 0 else "low"
    entry = _TRAJ_SHAPE_NAMES.get((col, direction))
    if entry is None:
        explanation = f"{FALLBACK_EXPLANATION}（实际主导: {feat_display}）"
        if len(explanation) > 200:
            explanation = FALLBACK_EXPLANATION[:197] + "..."
        return FALLBACK_PATTERN_TYPE, explanation
    pattern_type, explanation_tpl = entry
    explanation = explanation_tpl.format(feat=feat_display, delta=f"{abs(delta_val):.3f}")
    if len(explanation) > 200:
        explanation = explanation[:197] + "..."
    return pattern_type, explanation


def _assign_traj_names(
    feats: pd.DataFrame,
    labels: np.ndarray,
) -> dict[int, tuple[str, str]]:
    """Assign a (near-)INJECTIVE trajectory-shape name to every cluster (P5.7b).

    For each cluster, rank its shape axes by ``|centroid − market_mean|``
    descending (each axis carries its sign → a "high"/"low" name).  Then assign
    names greedily: the MOST-distinctive cluster (largest top-|delta|) gets first
    pick of its highest-preference name; each subsequent cluster takes the
    highest-preference (axis, direction) name not already used.  With 12 signed
    names available and at most K=8 clusters, distinct clusters always receive
    distinct names → ``n_pattern_type == n_clusters`` and the top pattern_type
    row-share equals the max CLUSTER row-share (already gated ≤ 0.60), resolving
    the P5.7 naming degeneracy.

    Deterministic and label-free — driven only by centroid SUMMARY_COLS.  Never
    alters ``labels`` (clustering is frozen); only names them.
    """
    col_names = list(feats.columns)
    n = len(feats)
    global_mean_arr = feats.values.mean(axis=0) if n > 0 else np.zeros(len(col_names))

    unique_cids = list(np.unique(labels))
    # Per-cluster preference list: (col, delta) sorted by |delta| desc.
    prefs: dict[int, list[tuple[str, float]]] = {}
    top_absdelta: dict[int, float] = {}
    for cid in unique_cids:
        members = feats.values[labels == cid]
        centroid = members.mean(axis=0) if len(members) else np.zeros(len(col_names))
        deltas = [(col, float(centroid[i] - global_mean_arr[i])) for i, col in enumerate(col_names)]
        deltas.sort(key=lambda cd: abs(cd[1]), reverse=True)
        prefs[cid] = deltas
        top_absdelta[cid] = abs(deltas[0][1]) if deltas else 0.0

    # Most-distinctive cluster picks first; deterministic tie-break by cid.
    order = sorted(unique_cids, key=lambda c: (-top_absdelta[c], int(c)))

    used_names: set[str] = set()
    name_map: dict[int, tuple[str, str]] = {}
    for cid in order:
        chosen = None
        for col, delta in prefs[cid]:
            name, expl = _traj_axis_to_name(col, delta)
            if name not in used_names:
                chosen = (name, expl)
                break
        if chosen is None:
            # All preferred names taken (only if #clusters > #names, impossible
            # for K<=8 with 12 names) — fall back to the cluster's primary axis
            # name suffixed so it stays distinct and non-empty.
            col, delta = prefs[cid][0]
            base_name, base_expl = _traj_axis_to_name(col, delta)
            name = f"{base_name}·{int(cid)}"
            chosen = (name, base_expl)
        used_names.add(chosen[0])
        name_map[cid] = chosen
    return name_map


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


def _sweep_k_constrained(
    X: np.ndarray,
    k_range: tuple[int, int] | None = None,
    min_size: int | None = None,
    max_share: float | None = None,
) -> tuple[int, dict]:
    """Balance-first K-sweep (P5 Slice-6): argmax silhouette over FEASIBLE K only.

    Identical to :func:`_sweep_k` (same KMeans fit, ``RANDOM_SEED``, ``n_init=10``,
    silhouette-then-CH tie-break) except a candidate K is **rejected before its
    silhouette is compared** when its partition is degenerate:

      * fewer than 2 distinct clusters (KMeans collapsed labels), OR
      * ``min(cluster_sizes) < min_size`` (a singleton is not a behavioral mode), OR
      * ``max(cluster_sizes) / n > max_share`` (one dominant cluster — the Slice-4
        degeneracy pathology in Euclidean space).

    Because the feasible set is a **subset** of the K :func:`_sweep_k` ranks, the
    selected silhouette is ≤ the legacy silhouette pointwise (never higher — see the
    hypothesis doc §2.2).  This selects for *non-degeneracy*, not for a higher score.

    Parameters
    ----------
    X : np.ndarray
        Rank-normalized daily feature matrix, shape (n_samples, n_features).
    k_range : (min_k, max_k) inclusive, default config.K_RANGE.
    min_size : smallest admissible cluster, default config.TASK1_MIN_CLUSTER_SIZE.
    max_share : max admissible single-cluster share of n, default
        config.TASK1_MAX_CLUSTER_SHARE.

    Returns
    -------
    (best_k, info)
        ``best_k`` — the feasible argmax-silhouette K, or 1 if NO K is feasible.
        ``info`` — dict with ``feasible_k_count`` (int), ``rejected_reason``
        (str|None — set only when best_k falls back to 1), ``silhouette``, ``ch``,
        ``cluster_sizes`` (of the selected K; ``[n]`` when best_k == 1).
    """
    if k_range is None:
        k_range = K_RANGE
    if min_size is None:
        min_size = TASK1_MIN_CLUSTER_SIZE
    if max_share is None:
        max_share = TASK1_MAX_CLUSTER_SHARE

    n = X.shape[0]
    lo, hi = k_range
    lo_eff = max(lo, 2)
    hi_eff = min(hi, n - 1)

    def _fallback(reason: str) -> tuple[int, dict]:
        return 1, {
            "feasible_k_count": 0,
            "rejected_reason": reason,
            "silhouette": -1.0,
            "ch": 0.0,
            "cluster_sizes": [n],
        }

    if lo_eff > hi_eff:
        log.info("Constrained sweep: no k>=2 in range %s for n=%d; K=1", k_range, n)
        return _fallback(f"no k>=2 feasible in range {k_range} for n={n}")

    best_k = None
    best_sil = -2.0
    best_ch = 0.0
    best_sizes: list[int] = [n]
    feasible = 0
    rejects: list[str] = []

    for k in range(lo_eff, hi_eff + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(X)
        _, sizes = np.unique(labels, return_counts=True)
        if len(sizes) < 2:
            rejects.append(f"k={k}: collapsed to {len(sizes)} cluster(s)")
            continue
        if int(sizes.min()) < min_size:
            rejects.append(f"k={k}: min_size {int(sizes.min())}<{min_size}")
            continue
        if float(sizes.max()) / n > max_share:
            rejects.append(f"k={k}: max_share {sizes.max()/n:.2f}>{max_share:.2f}")
            continue

        feasible += 1
        sil = silhouette_score(X, labels)
        ch = calinski_harabasz_score(X, labels)
        if sil > best_sil or (sil == best_sil and ch > best_ch):
            best_sil = sil
            best_ch = ch
            best_k = k
            best_sizes = sorted(sizes.tolist())

    if best_k is None:
        reason = "; ".join(rejects) or "all candidate K rejected by balance constraints"
        log.info("Constrained sweep %s → NO feasible K (%s); K=1", k_range, reason)
        return _fallback(reason)

    log.info(
        "Constrained sweep %s → best K=%d (sil=%.4f, CH=%.1f, feasible=%d, sizes=%s)",
        k_range, best_k, best_sil, best_ch, feasible, best_sizes,
    )
    return best_k, {
        "feasible_k_count": feasible,
        "rejected_reason": None,
        "silhouette": float(best_sil),
        "ch": float(best_ch),
        "cluster_sizes": best_sizes,
    }


# ---------------------------------------------------------------------------
# P5 Slice-1: intraday metric alignment (DTW / Wasserstein) + enrichment
# ---------------------------------------------------------------------------


def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Classic O(n²) multivariate DTW between two ``(T, D)`` trajectories.

    Local cost is the Euclidean distance between per-bin vectors; pure numpy,
    no external dependency.  Identical series → 0; a time-shifted copy → > 0.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = a.shape[0], b.shape[0]
    if na == 0 or nb == 0:
        return 0.0
    acc = np.full((na + 1, nb + 1), np.inf)
    acc[0, 0] = 0.0
    for i in range(1, na + 1):
        ai = a[i - 1]
        for j in range(1, nb + 1):
            cost = float(np.linalg.norm(ai - b[j - 1]))
            acc[i, j] = cost + min(acc[i - 1, j], acc[i, j - 1], acc[i - 1, j - 1])
    return float(acc[na, nb])


def _cluster_dtw_separation(traj_arr: np.ndarray, labels: np.ndarray) -> float:
    """Mean pairwise DTW between cluster **centroid** trajectories (↑ = better).

    Centroid = per-bin mean trajectory of the cluster's members.  Returns 0.0
    when fewer than 2 clusters exist.
    """
    cids = [c for c in np.unique(labels)]
    if len(cids) < 2:
        return 0.0
    centroids = [traj_arr[labels == c].mean(axis=0) for c in cids]
    dists = [
        _dtw_distance(centroids[i], centroids[j])
        for i in range(len(centroids))
        for j in range(i + 1, len(centroids))
    ]
    return float(np.mean(dists)) if dists else 0.0


def _cluster_wasserstein_separation(traj_arr: np.ndarray, labels: np.ndarray) -> float:
    """Mean pairwise Wasserstein distance between cluster turnover-share
    distributions (trajectory series 0), ↑ = better.  0.0 if < 2 clusters.
    """
    cids = [c for c in np.unique(labels)]
    if len(cids) < 2:
        return 0.0
    pooled = [traj_arr[labels == c][:, :, 0].ravel() for c in cids]
    dists = [
        wasserstein_distance(pooled[i], pooled[j])
        for i in range(len(pooled))
        for j in range(i + 1, len(pooled))
    ]
    return float(np.mean(dists)) if dists else 0.0


# ---------------------------------------------------------------------------
# P5 Slice-4: cluster ON a precomputed DTW distance (Slice 1b)
# docs/hypotheses/p5-task1-dtw-precomputed.md
# ---------------------------------------------------------------------------


def _dtw_distance_matrix(traj_arr: np.ndarray) -> np.ndarray:
    """Symmetric ``(n, n)`` pairwise DTW distance matrix over ``(n, T, D)`` trajectories.

    Zero diagonal; ``D[i, j] == D[j, i] == _dtw_distance(traj_i, traj_j)``.  Built
    once per day and reused across the precomputed K-sweep (O(n²·T²) — see the
    fallback note in the hypothesis doc §6 if this is too slow on the panel).
    """
    traj_arr = np.asarray(traj_arr, dtype=float)
    n = traj_arr.shape[0]
    D = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            dist = _dtw_distance(traj_arr[i], traj_arr[j])
            D[i, j] = dist
            D[j, i] = dist
    return D


def _dtw_precomputed_sweep(
    D: np.ndarray,
    traj_arr: np.ndarray,
    k_range: tuple[int, int] | None = None,
) -> tuple[int, dict, np.ndarray]:
    """Pick K = argmax **DTW-space** silhouette via precomputed agglomerative clustering.

    Clusters with ``AgglomerativeClustering(metric='precomputed', linkage='average')``
    on *D*, scores ``silhouette_score(D, labels, metric='precomputed')`` (same DTW
    space it clustered in — a single honest objective, no composite weights).  CH is
    reported on the flattened trajectory space (Euclidean approximation of the DTW
    space), so it is internally consistent with the labels.  Returns
    ``(best_k, metrics_at_best, best_labels)``.
    """
    if k_range is None:
        k_range = K_RANGE
    n = D.shape[0]
    lo, hi = k_range
    lo_eff, hi_eff = max(lo, 2), min(hi, n - 1)
    flat = np.asarray(traj_arr, dtype=float).reshape(n, -1)
    empty = {"silhouette": -1.0, "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0}
    if lo_eff > hi_eff:
        return 1, empty, np.zeros(n, dtype=int)

    best_k, best_sil, best_labels = lo_eff, -np.inf, None
    for k in range(lo_eff, hi_eff + 1):
        labels = AgglomerativeClustering(
            n_clusters=k, metric="precomputed", linkage="average"
        ).fit_predict(D)
        if len(np.unique(labels)) < 2:
            continue
        sil = float(silhouette_score(D, labels, metric="precomputed"))
        if sil > best_sil:
            best_sil, best_k, best_labels = sil, k, labels

    if best_labels is None:
        return 1, empty, np.zeros(n, dtype=int)

    metrics = {
        "silhouette": best_sil,
        "ch": float(calinski_harabasz_score(flat, best_labels)),
        "wasserstein_sep": _cluster_wasserstein_separation(traj_arr, best_labels),
        "dtw_sep": _cluster_dtw_separation(traj_arr, best_labels),
    }
    log.info(
        "dtw-precomputed sweep %s → K=%d (dtw_sil=%.4f CH=%.1f wass=%.4f dtw=%.4f)",
        k_range, best_k, best_sil, metrics["ch"],
        metrics["wasserstein_sep"], metrics["dtw_sep"],
    )
    return best_k, metrics, best_labels


# ---------------------------------------------------------------------------
# P5.7: Task-1 production path — DTW complete-linkage (config-gated)
# docs/hypotheses/competitive-gap-audit-20260703-fable5.md §6
# ---------------------------------------------------------------------------


def _merge_singletons(
    labels: np.ndarray,
    D: np.ndarray,
    min_size: int | None = None,
) -> np.ndarray:
    """Reassign members of any cluster smaller than *min_size* to their nearest
    OTHER cluster (mean precomputed distance in *D*), iterating until every
    surviving cluster meets *min_size* or a single cluster remains.

    A singleton scores silhouette ~= +1 by construction (Slice-6 note) and is not
    a behavioral mode. This is the "singleton-merge-to-nearest-cluster" step the
    P5.7 hypothesis doc (§6) calls for, applied to complete-linkage output.
    """
    if min_size is None:
        min_size = TASK1_MIN_CLUSTER_SIZE
    labels = np.array(labels, copy=True)
    n = len(labels)
    if n == 0:
        return labels

    for _ in range(n):  # bounded: each pass empties at least one whole cluster
        uniq, counts = np.unique(labels, return_counts=True)
        small = uniq[counts < min_size]
        if len(small) == 0:
            break
        if len(uniq) <= 1:
            break  # nothing left to merge into
        cid = int(small[0])
        other_labels = [int(c) for c in uniq if c != cid]
        members = np.where(labels == cid)[0]
        for m in members:
            best_c, best_d = None, np.inf
            for c in other_labels:
                c_members = np.where(labels == c)[0]
                if len(c_members) == 0:
                    continue
                d = float(D[m, c_members].mean())
                if d < best_d:
                    best_d, best_c = d, c
            if best_c is not None:
                labels[m] = best_c
    return labels


def _dtw_complete_sweep(
    D: np.ndarray,
    traj_arr: np.ndarray,
    k_range: tuple[int, int] | None = None,
    min_size: int | None = None,
    max_share: float | None = None,
) -> tuple[int, dict, np.ndarray]:
    """Pick K = argmax **DTW-space** silhouette via COMPLETE-linkage agglomerative
    clustering on the precomputed DTW distance, subject to degeneracy rails.

    For each candidate K in *k_range*: fit
    ``AgglomerativeClustering(metric='precomputed', linkage='complete')``, apply
    :func:`_merge_singletons`, then REJECT the candidate (before its silhouette is
    compared) if, after merge:

      * fewer than 3 distinct clusters remain (K >= 3 required post-merge), OR
      * ``min(cluster_sizes) < min_size``, OR
      * ``max(cluster_sizes) / n > max_share``.

    Silhouette is scored on the FINAL (post-merge) labels in the same precomputed
    DTW space that was clustered in — one honest objective, matching the
    production label path that will actually ship. Different from
    :func:`_dtw_precomputed_sweep` (Slice 4): linkage is 'complete' not 'average',
    the default K range is `config.TASK1_DTW_K_RANGE` (2-8) not legacy `K_RANGE`
    (6-12), and degeneracy constraints are baked into selection.

    Returns
    -------
    (best_k, metrics, best_labels)
        ``best_k`` — number of distinct clusters in the selected (post-merge)
        partition, or 1 if no candidate K is feasible.
        ``metrics`` — dict with ``silhouette``, ``ch``, ``wasserstein_sep``,
        ``dtw_sep``, ``cluster_sizes``, ``rejected_reason`` (str|None).
        ``best_labels`` — the selected partition's labels (``(n,)`` int array).
    """
    if k_range is None:
        k_range = config.TASK1_DTW_K_RANGE
    if min_size is None:
        min_size = TASK1_MIN_CLUSTER_SIZE
    if max_share is None:
        max_share = TASK1_MAX_CLUSTER_SHARE

    n = D.shape[0]
    lo, hi = k_range
    lo_eff, hi_eff = max(lo, 2), min(hi, n - 1)
    flat = np.asarray(traj_arr, dtype=float).reshape(n, -1)

    def _fallback(reason: str) -> tuple[int, dict, np.ndarray]:
        return 1, {
            "silhouette": -1.0, "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0,
            "cluster_sizes": [n], "rejected_reason": reason,
        }, np.zeros(n, dtype=int)

    if lo_eff > hi_eff:
        return _fallback(f"no k>=2 feasible in range {k_range} for n={n}")

    best_k, best_sil, best_labels, best_sizes = None, -np.inf, None, None
    rejects: list[str] = []
    for k in range(lo_eff, hi_eff + 1):
        raw_labels = AgglomerativeClustering(
            n_clusters=k, metric="precomputed", linkage="complete"
        ).fit_predict(D)
        labels = _merge_singletons(raw_labels, D, min_size=min_size)
        uniq, sizes = np.unique(labels, return_counts=True)
        k_eff = len(uniq)
        if k_eff < 3:
            rejects.append(f"k={k}: k_eff={k_eff}<3 after singleton-merge")
            continue
        if int(sizes.min()) < min_size:
            rejects.append(f"k={k}: min_size {int(sizes.min())}<{min_size} after merge")
            continue
        share = float(sizes.max()) / n
        if share > max_share:
            rejects.append(f"k={k}: max_share {share:.2f}>{max_share:.2f}")
            continue

        sil = float(silhouette_score(D, labels, metric="precomputed"))
        if sil > best_sil:
            best_sil, best_k, best_labels = sil, k_eff, labels
            best_sizes = sorted(sizes.tolist())

    if best_labels is None:
        reason = "; ".join(rejects) or "all candidate K rejected by degeneracy rails"
        log.info("dtw-complete sweep %s -> NO feasible K (%s); K=1", k_range, reason)
        return _fallback(reason)

    metrics = {
        "silhouette": best_sil,
        "ch": float(calinski_harabasz_score(flat, best_labels)),
        "wasserstein_sep": _cluster_wasserstein_separation(traj_arr, best_labels),
        "dtw_sep": _cluster_dtw_separation(traj_arr, best_labels),
        "cluster_sizes": best_sizes,
        "rejected_reason": None,
    }
    log.info(
        "dtw-complete sweep %s -> K=%d (dtw_sil=%.4f CH=%.1f wass=%.4f dtw=%.4f sizes=%s)",
        k_range, best_k, best_sil, metrics["ch"],
        metrics["wasserstein_sep"], metrics["dtw_sep"], best_sizes,
    )
    return best_k, metrics, best_labels


def _stack_trajectories(
    trajectories: dict, index: pd.Index, n_bins: int
) -> np.ndarray:
    """Align a ``{index_key: (n_bins, N_SERIES)}`` dict to *index* → ``(n, n_bins, N_SERIES)``.

    Missing keys become an all-zero trajectory (a stock with no snapshot shape).
    """
    out = np.zeros((len(index), n_bins, N_SERIES), dtype=float)
    for i, key in enumerate(index):
        arr = trajectories.get(key)
        if arr is not None and np.asarray(arr).shape == (n_bins, N_SERIES):
            out[i] = arr
    return out


def _traj_summary_frame(trajectories: dict, index: pd.Index) -> pd.DataFrame:
    """Per-row trajectory-shape summary features (SUMMARY_COLS), aligned to *index*."""
    rows = []
    for key in index:
        arr = trajectories.get(key)
        if arr is None:
            rows.append({c: 0.0 for c in SUMMARY_COLS})
        else:
            rows.append(summary_features(np.asarray(arr, dtype=float)))
    return pd.DataFrame(rows, index=index, columns=SUMMARY_COLS)


def build_clustering_matrix(
    matrix: pd.DataFrame,
    trajectories: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray | None]:
    """Build the rank-normalized clustering matrix (H1 seam), optionally enriched
    with trajectory-shape summary features.

    Returns
    -------
    (clustering_feats, naming_feats, traj_arr)
        ``clustering_feats`` — normalized feature matrix KMeans fits on (EXCLUDE
        columns dropped; SUMMARY_COLS appended when *trajectories* is given).
        ``naming_feats`` — ``clustering_feats`` minus SUMMARY_COLS, so centroid
        naming reads only the original finance features (traj_* never named).
        ``traj_arr`` — ``(n, n_bins, N_SERIES)`` aligned trajectories, or None.

    With ``trajectories is None`` the result is byte-identical to the pre-P5 path.
    """
    feats = matrix.select_dtypes("number").fillna(0.0)
    traj_arr = None
    if trajectories is not None and len(matrix) > 0:
        summary = _traj_summary_frame(trajectories, matrix.index)
        feats = pd.concat([feats, summary], axis=1)
        n_bins = next(iter(trajectories.values())).shape[0] if trajectories else 0
        if n_bins:
            traj_arr = _stack_trajectories(trajectories, matrix.index, n_bins)

    normed = normalize_matrix(feats).select_dtypes("number").fillna(0.0)
    clustering_feats = normed.drop(columns=[c for c in EXCLUDE if c in normed.columns])
    naming_feats = clustering_feats.drop(
        columns=[c for c in SUMMARY_COLS if c in clustering_feats.columns]
    )
    return clustering_feats, naming_feats, traj_arr


def _composite_sweep(
    X: np.ndarray,
    traj_arr: np.ndarray,
    k_range: tuple[int, int] | None = None,
) -> tuple[int, dict]:
    """Pick K maximizing ``sil + 0.25*norm_wass + 0.25*norm_dtw``.

    silhouette is Euclidean on the (enriched) matrix *X*; Wasserstein/DTW
    separations are computed on *traj_arr* grouped by each K's labels.  wass/dtw
    are min-max normalized across the K candidates only (within-day, no leakage).
    Returns (best_k, metrics_at_best).
    """
    if k_range is None:
        k_range = K_RANGE
    n = X.shape[0]
    lo, hi = k_range
    lo_eff, hi_eff = max(lo, 2), min(hi, n - 1)
    if lo_eff > hi_eff:
        return 1, {"silhouette": -1.0, "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0}

    cands = []
    for k in range(lo_eff, hi_eff + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(X)
        if len(np.unique(labels)) < 2:
            continue
        cands.append({
            "k": k,
            "silhouette": float(silhouette_score(X, labels)),
            "ch": float(calinski_harabasz_score(X, labels)),
            "wasserstein_sep": _cluster_wasserstein_separation(traj_arr, labels),
            "dtw_sep": _cluster_dtw_separation(traj_arr, labels),
        })
    if not cands:
        return 1, {"silhouette": -1.0, "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0}

    def _minmax(vals):
        lo_v, hi_v = min(vals), max(vals)
        rng = hi_v - lo_v
        return [0.0 if rng == 0 else (v - lo_v) / rng for v in vals]

    nw = _minmax([c["wasserstein_sep"] for c in cands])
    nd = _minmax([c["dtw_sep"] for c in cands])
    best_i, best_score = 0, -np.inf
    for i, c in enumerate(cands):
        score = c["silhouette"] + _WASS_WEIGHT * nw[i] + _DTW_WEIGHT * nd[i]
        if score > best_score:
            best_score, best_i = score, i
    best = cands[best_i]
    log.info(
        "composite sweep %s → K=%d (sil=%.4f CH=%.1f wass=%.4f dtw=%.4f)",
        k_range, best["k"], best["silhouette"], best["ch"],
        best["wasserstein_sep"], best["dtw_sep"],
    )
    return best["k"], best


def score_day(
    matrix: pd.DataFrame,
    trajectories: dict | None = None,
    k_range: tuple[int, int] | None = None,
    method: str = "euclidean",
    ksweep: str = "legacy",
) -> dict:
    """Per-day Task-1 clustering-quality report (offline harness seam, §5/§6).

    Reports the daily-only Euclidean silhouette baseline AND (when trajectories
    are given) the enriched silhouette + Wasserstein/DTW separations, so the
    lift is explicit and honest.  Label-free — §3.3-safe.

    Parameters
    ----------
    method : {"euclidean", "dtw_precomputed", "dtw-complete"}, default "euclidean"
        "euclidean" (default) → byte-identical to the pre-Slice-4 path (Slice-1
        enrichment when trajectories given, daily-only otherwise).
        "dtw_precomputed" (P5 Slice-4) → cluster ON the pairwise DTW distance and
        score silhouette in that same precomputed metric; requires *trajectories*.
        "dtw-complete" (P5.7) → COMPLETE-linkage on the pairwise DTW distance,
        K-swept over `config.TASK1_DTW_K_RANGE` (2-8, not legacy K_RANGE) with
        singleton-merge + max-share degeneracy rails baked into selection
        (:func:`_dtw_complete_sweep`); requires *trajectories*. Canonical
        hyphenated string — never an underscore variant.
    ksweep : {"legacy", "constrained"}, default "legacy"
        "legacy" (default) → byte-identical to the pre-Slice-6 path (K =
        argmax silhouette, no balance test).
        "constrained" (P5 Slice-6) → K chosen by the balance-first sweep
        (:func:`_sweep_k_constrained`) on the **daily** Euclidean matrix
        (``trajectories=None``, byte-identical to the production submit matrix);
        reports ``feasible_k_count`` / ``rejected_reason`` / ``cluster_sizes``.
        Euclidean-only — combining with ``method='dtw_precomputed'``/``'dtw-complete'`` raises.
    """
    if method not in ("euclidean", "dtw_precomputed", "dtw-complete"):
        raise ValueError(
            f"unknown method {method!r}; expected 'euclidean', 'dtw_precomputed', or 'dtw-complete'"
        )
    if ksweep not in ("legacy", "constrained"):
        raise ValueError(f"unknown ksweep {ksweep!r}; expected 'legacy' or 'constrained'")

    n = len(matrix)
    # Daily-only baseline (reproduces the D1.b audit path), reported in both modes.
    daily_feats, _, _ = build_clustering_matrix(matrix, trajectories=None)
    X_daily = daily_feats.values
    sil_daily, ch_daily = _fit_metrics(X_daily, _sweep_k(X_daily, k_range) if n > 1 else 1)

    if ksweep == "constrained":
        # Balance-first Euclidean sweep on the production daily matrix (Slice-6).
        # Reported alongside the legacy daily silhouette (silhouette_daily) so a
        # single run shows constrained vs legacy side by side.  DTW is out of scope.
        if method != "euclidean":
            raise ValueError("ksweep='constrained' is Euclidean-only; use method='euclidean'")
        if n > 1:
            best_k, cinfo = _sweep_k_constrained(X_daily, k_range)
        else:
            best_k, cinfo = 1, {
                "feasible_k_count": 0, "rejected_reason": "n<=1",
                "silhouette": -1.0, "ch": 0.0, "cluster_sizes": [n],
            }
        sizes = cinfo["cluster_sizes"]
        n_clusters = len(sizes)
        degenerate = bool(n_clusters < 2 or min(sizes) < TASK1_MIN_CLUSTER_SIZE)
        return {
            "best_k": int(best_k),
            "silhouette": float(cinfo["silhouette"]),
            "silhouette_daily": float(sil_daily),
            "ch": float(cinfo["ch"]),
            "wasserstein_sep": 0.0,
            "dtw_sep": 0.0,
            "n_clusters": int(n_clusters),
            "cluster_sizes": list(sizes),
            "degenerate": degenerate,
            "feasible_k_count": int(cinfo["feasible_k_count"]),
            "rejected_reason": cinfo["rejected_reason"],
        }

    if method == "dtw_precomputed":
        if trajectories is None:
            raise ValueError("method='dtw_precomputed' requires trajectories (falsification §4 metric-stub)")
        _, _, traj_arr = build_clustering_matrix(matrix, trajectories)
        if traj_arr is None:
            raise ValueError("method='dtw_precomputed' got empty/degenerate trajectories")
        if n <= 1:
            return {
                "best_k": 1, "silhouette": -1.0, "silhouette_daily": float(sil_daily),
                "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0,
                "n_clusters": 1, "cluster_sizes": [n], "degenerate": True,
                "feasible_k_count": None, "rejected_reason": None,
            }
        D = _dtw_distance_matrix(traj_arr)
        best_k, best, labels = _dtw_precomputed_sweep(D, traj_arr, k_range)
        _, sizes = np.unique(labels, return_counts=True)
        n_clusters = len(sizes)
        degenerate = bool(n_clusters < 2 or (sizes < 2).any())
        return {
            "best_k": int(best_k),
            "silhouette": float(best["silhouette"]),
            "silhouette_daily": float(sil_daily),
            "ch": float(best["ch"]),
            "wasserstein_sep": float(best["wasserstein_sep"]),
            "dtw_sep": float(best["dtw_sep"]),
            "n_clusters": int(n_clusters),
            "cluster_sizes": sizes.tolist(),
            "degenerate": degenerate,
            "feasible_k_count": None, "rejected_reason": None,
        }

    if method == "dtw-complete":
        if trajectories is None:
            raise ValueError("method='dtw-complete' requires trajectories (falsification §4 metric-stub)")
        _, _, traj_arr = build_clustering_matrix(matrix, trajectories)
        if traj_arr is None:
            raise ValueError("method='dtw-complete' got empty/degenerate trajectories")
        if n <= 1:
            return {
                "best_k": 1, "silhouette": -1.0, "silhouette_daily": float(sil_daily),
                "ch": 0.0, "wasserstein_sep": 0.0, "dtw_sep": 0.0,
                "n_clusters": 1, "cluster_sizes": [n], "degenerate": True,
                "feasible_k_count": None, "rejected_reason": None,
            }
        D = _dtw_distance_matrix(traj_arr)
        eff_k_range = k_range if k_range is not None else config.TASK1_DTW_K_RANGE
        best_k, best, labels = _dtw_complete_sweep(D, traj_arr, k_range=eff_k_range)
        _, sizes = np.unique(labels, return_counts=True)
        n_clusters = len(sizes)
        degenerate = bool(
            n_clusters < 3
            or (sizes < TASK1_MIN_CLUSTER_SIZE).any()
            or (sizes.max() / n) > TASK1_MAX_CLUSTER_SHARE
        )
        return {
            "best_k": int(best_k),
            "silhouette": float(best["silhouette"]),
            "silhouette_daily": float(sil_daily),
            "ch": float(best["ch"]),
            "wasserstein_sep": float(best["wasserstein_sep"]),
            "dtw_sep": float(best["dtw_sep"]),
            "n_clusters": int(n_clusters),
            "cluster_sizes": best.get("cluster_sizes", sizes.tolist()),
            "degenerate": degenerate,
            "feasible_k_count": None,
            "rejected_reason": best.get("rejected_reason"),
        }

    if trajectories is None:
        best_k = _sweep_k(X_daily, k_range) if n > 1 else 1
        X = X_daily
        wass = dtw = 0.0
        sil, ch = sil_daily, ch_daily
    else:
        clustering_feats, _, traj_arr = build_clustering_matrix(matrix, trajectories)
        X = clustering_feats.values
        if n > 1:
            best_k, best = _composite_sweep(X, traj_arr, k_range)
            sil, ch, wass, dtw = (
                best["silhouette"], best["ch"],
                best["wasserstein_sep"], best["dtw_sep"],
            )
        else:
            best_k, sil, ch, wass, dtw = 1, sil_daily, ch_daily, 0.0, 0.0

    # Final fit for cluster sizes + degeneracy flag.
    if n > 1 and best_k >= 2:
        labels = KMeans(n_clusters=best_k, random_state=RANDOM_SEED, n_init=10).fit_predict(X)
    else:
        labels = np.zeros(n, dtype=int)
    _, sizes = np.unique(labels, return_counts=True)
    n_clusters = len(sizes)
    degenerate = bool(n_clusters < 2 or (sizes < 2).any())
    return {
        "best_k": int(best_k),
        "silhouette": float(sil),
        "silhouette_daily": float(sil_daily),
        "ch": float(ch),
        "wasserstein_sep": float(wass),
        "dtw_sep": float(dtw),
        "n_clusters": int(n_clusters),
        "cluster_sizes": sizes.tolist(),
        "degenerate": degenerate,
        "feasible_k_count": None, "rejected_reason": None,
    }


def _fit_metrics(X: np.ndarray, k: int) -> tuple[float, float]:
    """Silhouette + CH for a KMeans fit at *k* (helper for score_day baseline)."""
    if X.shape[0] <= 1 or k < 2:
        return -1.0, 0.0
    labels = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10).fit_predict(X)
    if len(np.unique(labels)) < 2:
        return -1.0, 0.0
    return float(silhouette_score(X, labels)), float(calinski_harabasz_score(X, labels))


def _name_clusters(
    feats: pd.DataFrame,
    labels: np.ndarray,
    name_fn,
) -> dict[int, tuple[str, str]]:
    """Centroid-driven, relative-dominance naming (P5.1b) for the legacy
    euclidean path.  *name_fn* maps (dominant_feat, delta_val) ->
    (pattern_type, explanation) — ``_dominant_feature_to_name``.  (The
    dtw-complete path uses the injective ``_assign_traj_names`` instead.)

    Identical control flow to the pre-P5.7 inline block in ``cluster_patterns``
    (verbatim move, not a rewrite) — required for the euclidean path to stay
    byte-identical.
    """
    n = len(feats)
    col_names = list(feats.columns)

    global_mean_arr = feats.values.mean(axis=0) if n > 0 else np.zeros(len(col_names))
    global_mean_dict = {col: float(global_mean_arr[i]) for i, col in enumerate(col_names)}

    unique_cids = list(np.unique(labels))
    cluster_info: dict[int, tuple[dict[str, float], list[tuple[str, float]]]] = {}
    for cid in unique_cids:
        members = feats.values[labels == cid]
        centroid_mean = members.mean(axis=0)
        centroid_dict = {col: float(centroid_mean[i]) for i, col in enumerate(col_names)}
        delta_sorted = sorted(
            ((col, centroid_dict[col] - global_mean_dict[col]) for col in col_names),
            key=lambda kv: kv[1],
            reverse=True,
        )
        cluster_info[cid] = (centroid_dict, delta_sorted)

    name_map: dict[int, tuple[str, str]] = {}
    for cid in unique_cids:
        _, delta_sorted = cluster_info[cid]
        dominant_feat, dominant_delta = delta_sorted[0]
        name_map[cid] = name_fn(dominant_feat, dominant_delta)

    if len(unique_cids) >= 2:
        axis_idx = 1
        while len({nm for nm, _ in name_map.values()}) < 2:
            candidates = []
            for cid in unique_cids:
                _, delta_sorted = cluster_info[cid]
                if axis_idx < len(delta_sorted):
                    feat, dval = delta_sorted[axis_idx]
                    candidates.append((abs(dval), cid, feat, dval))
            if not candidates:
                break
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, reassign_cid, feat, dval = candidates[0]
            name_map[reassign_cid] = name_fn(feat, dval)
            axis_idx += 1

    return name_map


def _cluster_patterns_dtw_complete(
    matrix: pd.DataFrame,
    trajectories: dict | None,
    k_range: tuple[int, int] | None,
) -> pd.DataFrame:
    """P5.7 production path: complete-linkage clustering on the precomputed DTW
    distance + trajectory-shape naming.  Requires *trajectories* — fails loud
    without them (never emits a partial/degenerate Task-1 result, matching the
    Slice-4 falsification rule for the DTW family of methods).
    """
    n = len(matrix)
    if trajectories is None:
        raise ValueError("method='dtw-complete' requires trajectories")
    _, _, traj_arr = build_clustering_matrix(matrix, trajectories)
    if traj_arr is None:
        raise ValueError("method='dtw-complete' got empty/degenerate trajectories")

    traj_summary = _traj_summary_frame(trajectories, matrix.index)

    if n <= 1:
        log.info("n=%d <= 1; K=1 path (dtw-complete)", n)
        labels = np.zeros(n, dtype=int)
    else:
        D = _dtw_distance_matrix(traj_arr)
        eff_k_range = k_range if k_range is not None else config.TASK1_DTW_K_RANGE
        best_k, _, labels = _dtw_complete_sweep(D, traj_arr, k_range=eff_k_range)
        if best_k <= 1:
            labels = np.zeros(n, dtype=int)
        else:
            log.info("dtw-complete: %d clusters over %d samples", best_k, n)

    # P5.7b: injective ranked naming so distinct clusters get distinct names
    # (n_pattern_type == n_clusters; top pattern share == max cluster share).
    name_map = _assign_traj_names(traj_summary, labels)
    out = pd.DataFrame(
        {
            "pattern_type": [name_map[c][0] for c in labels],
            "pattern_explanation": [name_map[c][1] for c in labels],
        },
        index=matrix.index,
    )
    log.info("pattern distribution (dtw-complete): %s", out["pattern_type"].value_counts().to_dict())
    return out


def cluster_patterns(
    matrix: pd.DataFrame,
    k_range: tuple[int, int] | None = None,
    trajectories: dict | None = None,
    method: str | None = None,
) -> pd.DataFrame:
    """Cluster (stock, day) rows and assign an interpretable pattern per row.

    Applies rank-normalization (normalize_matrix) before clustering to make
    features cross-sectionally comparable in [0,1] space.

    Parameters
    ----------
    matrix : pd.DataFrame
        Feature matrix; rows are (stock, day) observations.
    k_range : (min_k, max_k) inclusive, optional.
        Override the K sweep range; default is config.K_RANGE (euclidean) /
        config.TASK1_DTW_K_RANGE (dtw-complete).
        Exposed here so callers (mainly tests) can plant a known K.
    trajectories : dict, optional (P5 Slice-1).
        ``{index_key: (n_bins, N_SERIES) ndarray}`` intraday trajectories aligned
        to ``matrix.index``.  When given (euclidean method), the clustering
        matrix is enriched with trajectory-shape summary features and K is
        chosen by the composite (silhouette + Wasserstein + DTW) sweep.  When
        ``None`` (default, and the production main.py path pre-P5.7) behavior is
        byte-identical to pre-P5.  REQUIRED when ``method="dtw-complete"``.
    method : {"euclidean", "dtw-complete"}, optional (P5.7).
        Task-1 clustering path.  Defaults to ``config.TASK1_METHOD`` (read at
        CALL time, not import time — flipping the config global mid-process is
        honored).  ``"euclidean"`` (default) is byte-identical to pre-P5.7
        production.  ``"dtw-complete"`` is the trajectory-space production path
        (docs/hypotheses/competitive-gap-audit-20260703-fable5.md §6).

    Returns
    -------
    pd.DataFrame
        Same index as `matrix`; columns: pattern_type, pattern_explanation.
    """
    n = len(matrix)

    if method is None:
        method = config.TASK1_METHOD
    if method not in ("euclidean", "dtw-complete"):
        raise ValueError(
            f"unknown method {method!r} for cluster_patterns; "
            "expected 'euclidean' or 'dtw-complete'"
        )

    if method == "dtw-complete":
        return _cluster_patterns_dtw_complete(matrix, trajectories, k_range)

    # --- euclidean (legacy, byte-identical) path below — UNCHANGED from pre-P5.7 ---

    # --- Rank-normalize (H1 dependency) + optional trajectory enrichment (P5) ---
    # clustering_feats: what KMeans fits on (EXCLUDE dropped; traj_* appended when
    # trajectories given).  naming_feats: clustering_feats minus traj_* so centroid
    # naming reads only the original finance features.
    clustering_feats, naming_feats, traj_arr = build_clustering_matrix(matrix, trajectories)
    X = clustering_feats.values

    # --- K=1 fast path ---
    if n <= 1:
        log.info("n=%d ≤ 1; K=1 path", n)
        labels = np.zeros(n, dtype=int)
    else:
        if traj_arr is None:
            k = _sweep_k(X, k_range=k_range)
        else:
            k, _ = _composite_sweep(X, traj_arr, k_range=k_range)
        if k <= 1:
            labels = np.zeros(n, dtype=int)
        else:
            km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
            labels = km.fit_predict(X)
            log.info("KMeans: %d clusters over %d samples", k, n)

    # --- Centroid-driven naming (uses naming_feats, so EXCLUDE + traj_* cols
    #     are invisible to argmax and lexicon matching) ---
    name_map = _name_clusters(naming_feats, labels, _dominant_feature_to_name)

    out = pd.DataFrame(
        {
            "pattern_type": [name_map[c][0] for c in labels],
            "pattern_explanation": [name_map[c][1] for c in labels],
        },
        index=matrix.index,
    )
    log.info("pattern distribution: %s", out["pattern_type"].value_counts().to_dict())
    return out
