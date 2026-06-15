"""Task-1 bounded-K clustering + pattern naming.

Ports the baseline KMeans approach (baseline-guide.md L375-386): standardise the
feature matrix, run KMeans with a dynamically-downgraded cluster count, then map each
cluster to an interpretable `pattern_type` via multi-condition matching.

This is a STUB-grade implementation per the brief: it produces correctly-formatted
output and degrades to K=1 on a single (stock, day) (expected on the fixture). Full
bounded-K selection (silhouette/CH sweep over K_RANGE) is deferred — see the TODO.
The 8 candidate `pattern_type` names are Baseline defaults, not a mandatory enum
(competition-clarifications.md: pattern_type is open vocabulary).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from config import DEFAULT_K, K_RANGE, RANDOM_SEED

log = logging.getLogger(__name__)

# Baseline default candidate vocabulary (open per platform FAQ).
FALLBACK_PATTERN = "机构长线配置"
PATTERN_RULES = [
    # (pattern_type, explanation, predicate over a feature dict)
    (
        "游资强势连板拉升",
        "超大单占比高、主动买入强、尾盘/开盘成交集中，符合游资强势拉升特征",
        lambda f: (f.get("oss_mega_amount_pct", 0) > 0.12
                   and f.get("ap_active_buy_pct", 0) > 0.55
                   and f.get("pi_time_concentration", 0) > 0.30),
    ),
    (
        "量化高频T0套利",
        "小单占比高、成交节奏均匀、买卖均衡，符合量化高频日内套利特征",
        lambda f: (f.get("oss_small_amount_pct", 0) > 0.40
                   and f.get("rs_burst_ratio", 0) > 0.20
                   and abs(f.get("ap_active_net_direction", 0)) < 0.10),
    ),
    (
        "主力资金吸筹建仓",
        "大单净买入、盘口买盘占优、价格冲击温和，符合主力吸筹建仓特征",
        lambda f: (f.get("ap_active_net_direction", 0) > 0.10
                   and f.get("book_imbalance", 0) > 0.10
                   and f.get("oss_large_amount_pct", 0) > 0.10),
    ),
    (
        "盘口诱多撤单",
        "挂单大但成交占比低、撤单倾向高，疑似盘口诱多",
        lambda f: (f.get("obp_big_quote_share", 0) > 0.30
                   and f.get("ap_active_buy_pct", 0) < 0.45),
    ),
]


def _choose_k(n_samples: int) -> int:
    """Dynamic cluster count: clamp to K_RANGE, then downgrade to n_samples.

    TODO(bounded-k): sweep K over K_RANGE and pick by silhouette/CH instead of a
    fixed default. Stub uses DEFAULT_K clamped into range.
    """
    k = min(max(DEFAULT_K, K_RANGE[0]), K_RANGE[1])
    return max(1, min(k, n_samples))


def _name_cluster(centroid_feat: dict) -> tuple[str, str]:
    """Map a cluster centroid (mean feature dict) to a (pattern_type, explanation)."""
    for name, explanation, predicate in PATTERN_RULES:
        if predicate(centroid_feat):
            return name, explanation
    return FALLBACK_PATTERN, "未触发明确模式条件，归为机构长线配置（默认类别）"


def cluster_patterns(matrix: pd.DataFrame) -> pd.DataFrame:
    """Cluster (stock, day) rows and assign an interpretable pattern per row.

    Returns a frame indexed like `matrix` with columns pattern_type, pattern_explanation.
    """
    n = len(matrix)
    k = _choose_k(n)
    feats = matrix.select_dtypes("number").fillna(0.0)

    if k <= 1 or n <= 1:
        log.info(">>> samples (%d) <= clusters; KMeans downgrades to K=1", n)
        labels = np.zeros(n, dtype=int)
    else:
        X = StandardScaler().fit_transform(feats.values)
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(X)
        log.info("KMeans: %d clusters over %d samples", k, n)

    # Name each cluster from its centroid (mean of member feature rows).
    records = []
    for cid in np.unique(labels):
        members = feats[labels == cid]
        name, explanation = _name_cluster(members.mean().to_dict())
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
