"""Tests for src/cluster.py — bounded-K sweep + centroid-driven naming (Phase 5 P5.1).

All tests use synthetic matrices with seeded numpy. A stub that always returns K=1 or
always the default name must FAIL these tests (they are discriminating).

Synthetic matrix columns use real feature names so the naming function has something
to read when computing centroid-driven labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import silhouette_score

import config
from src.cluster import (
    cluster_patterns,
    _sweep_k,
    _sweep_k_constrained,
    _dtw_distance,
    _dtw_distance_matrix,
    score_day,
)
from src.intraday_trajectory import build_trajectory


# ---------------------------------------------------------------------------
# Helper — build well-separated synthetic blobs with real-ish column names
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "oss_mega_amount_pct",
    "oss_large_amount_pct",
    "oss_small_amount_pct",
    "ap_active_buy_pct",
    "ap_active_net_direction",
    "pi_time_concentration",
    "rs_burst_ratio",
    "book_imbalance",
    "obp_big_quote_share",
]


def _make_blobs(n_per_cluster: int, n_clusters: int, rng: np.random.Generator) -> pd.DataFrame:
    """Create well-separated blobs; each cluster centroid is far from others."""
    rows = []
    for cid in range(n_clusters):
        # Each cluster centroid shifts in all dims by (cid * 3) so they're far apart
        centre = np.zeros(len(FEATURE_COLS))
        centre[cid % len(FEATURE_COLS)] = cid * 3.0 + 2.0
        blob = rng.normal(loc=centre, scale=0.2, size=(n_per_cluster, len(FEATURE_COLS)))
        rows.append(blob)
    data = np.vstack(rows)
    # Clip to valid probability ranges where features are proportions
    data = np.clip(data, 0.0, 1.0)
    return pd.DataFrame(data, columns=FEATURE_COLS)


# ---------------------------------------------------------------------------
# Test 1: planted-K recovery
# ---------------------------------------------------------------------------

def test_ksweep_recovers_planted_k():
    """Sweep inside k_range=(2,6) recovers the planted K=4 from well-separated blobs.

    A fixed-K stub (K=8 or K=DEFAULT_K) would return a different K, failing this test.
    """
    rng = np.random.default_rng(0)
    planted_k = 4
    df = _make_blobs(n_per_cluster=30, n_clusters=planted_k, rng=rng)
    selected_k = _sweep_k(df.values, k_range=(2, 6))
    assert selected_k == planted_k, (
        f"Expected K={planted_k}, got K={selected_k}. "
        "If the sweep is a stub returning a fixed K, this will fail."
    )


# ---------------------------------------------------------------------------
# Test 2: selected K silhouette > fixed K=8 silhouette
# ---------------------------------------------------------------------------

def _make_rank_separated_blobs(
    n_per_cluster: int, n_clusters: int, rng: np.random.Generator
) -> pd.DataFrame:
    """Build blobs that remain well-separated after rank-normalization.

    Each cluster occupies a distinct, non-overlapping rank band: cluster 0 gets
    the lowest values, cluster 1 slightly higher, etc. This guarantees that even
    after cross-sectional rank-normalization the within-cluster coherence is high
    and between-cluster distance remains large.
    """
    n_feat = len(FEATURE_COLS)
    rows = []
    # Spread cluster centres from 0.05 to 0.95 in 0/1 range, with tight std
    centres = np.linspace(0.05, 0.95, n_clusters)
    for centre in centres:
        blob = rng.normal(loc=centre, scale=0.015, size=(n_per_cluster, n_feat))
        blob = np.clip(blob, 0.0, 1.0)
        rows.append(blob)
    data = np.vstack(rows)
    return pd.DataFrame(data, columns=FEATURE_COLS)


def test_selected_k_beats_fixed_k8_silhouette():
    """Silhouette at the selected K must be strictly higher than at fixed K=8.

    Plant 3 well-separated blobs. After rank-normalization the 3-cluster
    structure should score better silhouette than forcing K=8 (which over-splits).
    Both the sweep and the comparison use the same rank-normalized values.
    """
    from sklearn.cluster import KMeans
    from src.normalize import normalize_matrix

    rng = np.random.default_rng(99)
    planted_k = 3
    df = _make_rank_separated_blobs(n_per_cluster=40, n_clusters=planted_k, rng=rng)

    # Rank-normalize — _sweep_k and comparison both use the same data
    norm_vals = normalize_matrix(df).select_dtypes("number").fillna(0.0).values

    # Sweep range (2,8) — selected K should be 3, clearly beating K=8
    selected_k = _sweep_k(norm_vals, k_range=(2, 8))

    km_selected = KMeans(n_clusters=selected_k, random_state=42, n_init=10)
    sil_selected = silhouette_score(norm_vals, km_selected.fit_predict(norm_vals))

    km_fixed8 = KMeans(n_clusters=8, random_state=42, n_init=10)
    sil_fixed8 = silhouette_score(norm_vals, km_fixed8.fit_predict(norm_vals))

    assert selected_k != 8, (
        f"Sweep should not select K=8 when only 3 clusters exist; got K={selected_k}"
    )
    assert sil_selected > sil_fixed8, (
        f"Selected K={selected_k} silhouette={sil_selected:.4f} must beat "
        f"fixed K=8 silhouette={sil_fixed8:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 3: naming is centroid-driven — two distinct clusters get distinct labels
# ---------------------------------------------------------------------------

def test_naming_is_centroid_driven():
    """Two clusters with different dominant features get distinct pattern_type labels.

    Build a matrix with exactly 2 clearly separated groups — one high in
    oss_mega_amount_pct/ap_active_buy_pct (游资-like) and one high in
    oss_small_amount_pct/rs_burst_ratio (量化-like). If naming is always the
    fallback, both get the same label and this fails.
    """
    rng = np.random.default_rng(2)
    n = 30

    # Group A: high mega_amount_pct and ap_active_buy_pct
    grp_a = pd.DataFrame(
        {
            "oss_mega_amount_pct": rng.uniform(0.3, 0.5, n),
            "ap_active_buy_pct": rng.uniform(0.6, 0.9, n),
            "pi_time_concentration": rng.uniform(0.4, 0.6, n),
            "oss_small_amount_pct": rng.uniform(0.0, 0.1, n),
            "rs_burst_ratio": rng.uniform(0.0, 0.1, n),
            "ap_active_net_direction": rng.uniform(0.0, 0.05, n),
            "oss_large_amount_pct": rng.uniform(0.1, 0.2, n),
            "book_imbalance": rng.uniform(0.0, 0.05, n),
            "obp_big_quote_share": rng.uniform(0.0, 0.1, n),
        }
    )
    # Group B: high oss_small_amount_pct and rs_burst_ratio
    grp_b = pd.DataFrame(
        {
            "oss_mega_amount_pct": rng.uniform(0.0, 0.05, n),
            "ap_active_buy_pct": rng.uniform(0.2, 0.4, n),
            "pi_time_concentration": rng.uniform(0.0, 0.1, n),
            "oss_small_amount_pct": rng.uniform(0.5, 0.8, n),
            "rs_burst_ratio": rng.uniform(0.3, 0.5, n),
            "ap_active_net_direction": rng.uniform(-0.05, 0.05, n),
            "oss_large_amount_pct": rng.uniform(0.0, 0.05, n),
            "book_imbalance": rng.uniform(-0.05, 0.05, n),
            "obp_big_quote_share": rng.uniform(0.0, 0.1, n),
        }
    )
    df = pd.concat([grp_a, grp_b], ignore_index=True)
    result = cluster_patterns(df, k_range=(2, 4))

    unique_labels = result["pattern_type"].unique()
    assert len(unique_labels) >= 2, (
        f"Expected at least 2 distinct pattern_type labels, got {list(unique_labels)}. "
        "Centroid-driven naming should yield different labels for very different clusters."
    )


# ---------------------------------------------------------------------------
# Test 4: every row gets a non-empty explanation ≤ 200 chars, index matches
# ---------------------------------------------------------------------------

def test_every_row_gets_explanation():
    """All rows have non-null pattern_explanation ≤ 200 chars; index matches input."""
    rng = np.random.default_rng(3)
    df = _make_blobs(n_per_cluster=15, n_clusters=3, rng=rng)
    df.index = pd.RangeIndex(start=100, stop=100 + len(df))  # non-default index

    result = cluster_patterns(df, k_range=(2, 5))

    assert list(result.index) == list(df.index), "Output index must match input index"
    assert "pattern_type" in result.columns
    assert "pattern_explanation" in result.columns

    for idx, row in result.iterrows():
        assert row["pattern_explanation"] and len(row["pattern_explanation"]) > 0, (
            f"Row {idx} has empty pattern_explanation"
        )
        assert len(row["pattern_explanation"]) <= 200, (
            f"Row {idx} explanation too long: {len(row['pattern_explanation'])} chars"
        )
        assert row["pattern_type"] and len(row["pattern_type"]) > 0, (
            f"Row {idx} has empty pattern_type"
        )


# ---------------------------------------------------------------------------
# Test 5: K=1 graceful on single row
# ---------------------------------------------------------------------------

def test_k1_graceful_on_single_row():
    """n==1 matrix: K=1 path, no exception, non-empty label, correct shape."""
    df = pd.DataFrame(
        {
            "oss_mega_amount_pct": [0.2],
            "ap_active_buy_pct": [0.6],
            "pi_time_concentration": [0.3],
        },
        index=[42],
    )
    result = cluster_patterns(df)  # default k_range — must degrade gracefully
    assert len(result) == 1
    assert result.index[0] == 42
    assert result["pattern_type"].iloc[0] and len(result["pattern_type"].iloc[0]) > 0
    assert result["pattern_explanation"].iloc[0] and len(result["pattern_explanation"].iloc[0]) > 0
    assert len(result["pattern_explanation"].iloc[0]) <= 200


# ---------------------------------------------------------------------------
# Test 6: default k_range == config.K_RANGE
# ---------------------------------------------------------------------------

def test_default_range_is_config_k_range():
    """_sweep_k called without k_range uses config.K_RANGE.

    Build a matrix large enough to support the upper bound of K_RANGE,
    then confirm _sweep_k() (no k_range arg) returns a value within config.K_RANGE.
    """
    rng = np.random.default_rng(4)
    # Need at least K_RANGE[1] + 1 samples to support the full sweep
    n_per = 20
    n_clusters = config.K_RANGE[1]  # = 12
    df = _make_blobs(n_per_cluster=n_per, n_clusters=n_clusters, rng=rng)

    selected_k = _sweep_k(df.values)  # no k_range — should use config.K_RANGE
    lo, hi = config.K_RANGE
    assert lo <= selected_k <= hi, (
        f"Default sweep returned K={selected_k} outside config.K_RANGE={config.K_RANGE}"
    )


# ---------------------------------------------------------------------------
# Test 7 (P5.1a regression): raw-scale EXCLUDE columns must not drive clustering
# ---------------------------------------------------------------------------

def test_raw_scale_n_ticks_does_not_drive_clustering_or_naming():
    """EXCLUDE columns (n_ticks at raw scale ~thousands) must not dominate KMeans
    distance or centroid naming.

    Build a synthetic matrix with two clearly distinct microstructure groups:
      Group A: high oss_mega_amount_pct / ap_active_buy_pct  (游资-like)
      Group B: high oss_small_amount_pct / rs_burst_ratio    (量化-like)
    Then add an n_ticks column with raw-scale values (1000–50000) that is
    UNCORRELATED with the true groups (shuffled independently).

    Before the fix: n_ticks (~thousands) dominates Euclidean distance →
      all rows collapse to a single fallback label → test fails.
    After the fix: n_ticks is dropped before KMeans and before centroid naming →
      ≥2 distinct pattern_type labels, none with "n_ticks" or "n ticks" in explanation.
    """
    rng = np.random.default_rng(7)
    n = 40  # 40 rows per group

    # Group A: high mega_amount_pct and ap_active_buy_pct (游资-like)
    grp_a = pd.DataFrame(
        {
            "oss_mega_amount_pct": rng.uniform(0.55, 0.85, n),
            "ap_active_buy_pct": rng.uniform(0.60, 0.90, n),
            "pi_time_concentration": rng.uniform(0.50, 0.75, n),
            "oss_small_amount_pct": rng.uniform(0.00, 0.10, n),
            "rs_burst_ratio": rng.uniform(0.00, 0.10, n),
            "ap_active_net_direction": rng.uniform(0.30, 0.60, n),
            "oss_large_amount_pct": rng.uniform(0.20, 0.40, n),
            "book_imbalance": rng.uniform(0.10, 0.30, n),
            "obp_big_quote_share": rng.uniform(0.10, 0.30, n),
        }
    )
    # Group B: high oss_small_amount_pct / rs_burst_ratio (量化-like)
    grp_b = pd.DataFrame(
        {
            "oss_mega_amount_pct": rng.uniform(0.00, 0.10, n),
            "ap_active_buy_pct": rng.uniform(0.10, 0.30, n),
            "pi_time_concentration": rng.uniform(0.00, 0.15, n),
            "oss_small_amount_pct": rng.uniform(0.60, 0.90, n),
            "rs_burst_ratio": rng.uniform(0.55, 0.80, n),
            "ap_active_net_direction": rng.uniform(-0.10, 0.10, n),
            "oss_large_amount_pct": rng.uniform(0.00, 0.10, n),
            "book_imbalance": rng.uniform(-0.10, 0.10, n),
            "obp_big_quote_share": rng.uniform(0.00, 0.10, n),
        }
    )

    df = pd.concat([grp_a, grp_b], ignore_index=True)

    # Add n_ticks at raw scale, UNCORRELATED with group membership (shuffled)
    n_ticks_raw = rng.integers(1000, 50000, size=len(df)).astype(float)
    rng.shuffle(n_ticks_raw)  # ensure no accidental correlation
    df["n_ticks"] = n_ticks_raw

    result = cluster_patterns(df, k_range=(2, 4))

    # 1. At least 2 distinct pattern types — raw n_ticks must NOT collapse naming
    unique_labels = result["pattern_type"].unique()
    assert len(unique_labels) >= 2, (
        f"Expected ≥2 distinct pattern_type labels but got {list(unique_labels)}. "
        "n_ticks (raw scale ~thousands) is dominating Euclidean distance "
        "and collapsing all rows to a single fallback. Fix: drop EXCLUDE columns "
        "before KMeans and centroid naming."
    )

    # 2. No explanation may mention n_ticks (the EXCLUDE col must be invisible to naming)
    for idx, row in result.iterrows():
        expl = row["pattern_explanation"]
        assert "n_ticks" not in expl and "n ticks" not in expl, (
            f"Row {idx} explanation mentions EXCLUDE column 'n_ticks': {expl!r}. "
            "The EXCLUDE column must be dropped before centroid naming."
        )


# ---------------------------------------------------------------------------
# Test 8 (P5.1b): relative naming yields ≥3 distinct labels when ≥3 clusters
# ---------------------------------------------------------------------------

def test_relative_naming_yields_multiple_labels():
    """Each planted cluster is extreme on a DIFFERENT feature; relative naming
    must produce ≥3 distinct pattern_type labels.

    This FAILS on the old absolute-threshold naming because all centroids
    post rank-normalization hover near ~0.5 and no AND-predicate ever fires
    → every cluster falls to the same 机构长线配置 fallback.

    With relative naming (argmax(centroid - global_mean)), each cluster is
    assigned the feature it sits FURTHEST ABOVE the day's average, mapping
    to distinct lexicon entries → ≥3 distinct labels.
    """
    rng = np.random.default_rng(42)
    n = 40  # rows per cluster

    # Cluster A: extreme on mega_amount → should map to 游资* family
    mega_col = "oss_mega_amount_pct"
    # Cluster B: extreme on small_amount → should map to 量化* or high-freq family
    small_col = "oss_small_amount_pct"
    # Cluster C: extreme on active_buy → should map to 买盘* family
    buy_col = "ap_active_buy_pct"

    base_cols = [
        "oss_mega_amount_pct",
        "oss_large_amount_pct",
        "oss_small_amount_pct",
        "ap_active_buy_pct",
        "ap_active_net_direction",
        "pi_time_concentration",
        "rs_burst_ratio",
        "book_imbalance",
        "obp_big_quote_share",
    ]

    def make_cluster(dominant_col: str, high_val: float, low_val: float) -> pd.DataFrame:
        """Build a cluster with dominant_col high and all others low."""
        data = {c: rng.uniform(low_val - 0.05, low_val + 0.05, n) for c in base_cols}
        data[dominant_col] = rng.uniform(high_val - 0.05, high_val + 0.05, n)
        return pd.DataFrame(data)

    grp_a = make_cluster(mega_col,  high_val=0.90, low_val=0.05)
    grp_b = make_cluster(small_col, high_val=0.90, low_val=0.05)
    grp_c = make_cluster(buy_col,   high_val=0.90, low_val=0.05)

    df = pd.concat([grp_a, grp_b, grp_c], ignore_index=True)

    result = cluster_patterns(df, k_range=(3, 5))

    unique_labels = result["pattern_type"].unique()
    assert len(unique_labels) >= 3, (
        f"Expected ≥3 distinct pattern_type labels (one per planted dominant feature), "
        f"got {len(unique_labels)}: {list(unique_labels)}. "
        "Relative naming (argmax of centroid-global_mean delta) should distinguish "
        "clusters extreme on different features."
    )


# ---------------------------------------------------------------------------
# Test 9 (P5.1b): ≥2 distinct labels guaranteed when K≥2 (tie-break exercises)
# ---------------------------------------------------------------------------

def test_naming_guarantees_two_labels_when_k_ge_2():
    """Two clusters share the same top-delta axis but differ on a secondary axis;
    the tie-break must still produce ≥2 distinct pattern_type labels.

    Cluster A: extreme on mega_amount (top), secondary high on active_buy
    Cluster B: extreme on mega_amount (top), secondary high on small_amount
    Both share the same argmax(delta) on mega_amount.  Without the tie-break
    both would receive the same label.  The tie-break must reassign the cluster
    with the largest secondary |delta| to its secondary-axis label → ≥2 distinct.
    """
    rng = np.random.default_rng(99)
    n = 40  # rows per cluster

    # Both clusters are high on mega_amount so same primary dominant feature
    # Cluster A is additionally high on active_buy
    # Cluster B is additionally high on small_amount
    base_cols = [
        "oss_mega_amount_pct",
        "oss_large_amount_pct",
        "oss_small_amount_pct",
        "ap_active_buy_pct",
        "ap_active_net_direction",
        "pi_time_concentration",
        "rs_burst_ratio",
        "book_imbalance",
        "obp_big_quote_share",
    ]

    # Cluster A: high mega + high active_buy, everything else mid
    data_a = {c: rng.uniform(0.40, 0.55, n) for c in base_cols}
    data_a["oss_mega_amount_pct"] = rng.uniform(0.80, 0.95, n)  # primary (both share)
    data_a["ap_active_buy_pct"]   = rng.uniform(0.70, 0.85, n)  # secondary (A only)
    grp_a = pd.DataFrame(data_a)

    # Cluster B: high mega + high small_amount, everything else mid
    data_b = {c: rng.uniform(0.40, 0.55, n) for c in base_cols}
    data_b["oss_mega_amount_pct"] = rng.uniform(0.80, 0.95, n)  # primary (both share)
    data_b["oss_small_amount_pct"] = rng.uniform(0.70, 0.85, n)  # secondary (B only)
    grp_b = pd.DataFrame(data_b)

    df = pd.concat([grp_a, grp_b], ignore_index=True)

    result = cluster_patterns(df, k_range=(2, 4))

    unique_labels = result["pattern_type"].unique()
    assert len(unique_labels) >= 2, (
        f"Expected ≥2 distinct pattern_type labels (tie-break guarantee), "
        f"got {len(unique_labels)}: {list(unique_labels)}. "
        "When two clusters share the same primary dominant feature, the tie-break "
        "must reassign one to its secondary-axis label."
    )


# ===========================================================================
# Slice-1 (P5): metric alignment — DTW / Wasserstein + trajectory enrichment
# ===========================================================================


def test_dtw_identical_zero_shifted_positive():
    """DTW of a series with itself is 0; DTW of a series vs its time-shift is > 0."""
    rng = np.random.default_rng(1)
    a = rng.normal(size=(30, 3))
    b = np.roll(a, shift=5, axis=0)  # time-shifted copy
    assert _dtw_distance(a, a) == 0.0
    assert _dtw_distance(a, b) > 0.0
    # DTW is symmetric.
    assert abs(_dtw_distance(a, b) - _dtw_distance(b, a)) < 1e-9


def _make_shape_group(kind: str, n_ticks: int = 120):
    """Snapshot-style frame whose intraday turnover SHAPE encodes `kind`."""
    third = n_ticks // 3
    if kind == "front":
        amt = [10.0] * third + [0.2] * (n_ticks - third)
    elif kind == "back":
        amt = [0.2] * (n_ticks - third) + [10.0] * third
    else:  # uniform
        amt = [3.0] * n_ticks
    price = [10.0 + 0.001 * i for i in range(n_ticks)]
    px = pd.Series(price, dtype=float)
    return pd.DataFrame(
        {
            "stock_code": "X",
            "transaction_date": "20260616",
            "tick_amount": amt,
            "totalbidvolume": [100.0] * n_ticks,
            "totalaskvolume": [100.0] * n_ticks,
            "price": px,
            "price_change": px.diff().fillna(0.0),
        }
    )


def _enrichment_fixture(rng):
    """3 groups whose DAILY aggregate is ~pure noise but whose intraday SHAPE
    cleanly separates them (front / back / uniform turnover).

    Returns (matrix, trajectories) keyed on a shared RangeIndex.
    """
    n_per = 20
    shapes = ["front", "back", "uniform"]
    daily_cols = [
        "oss_mega_amount_pct", "oss_large_amount_pct", "oss_small_amount_pct",
        "ap_active_buy_pct", "ap_active_net_direction", "pi_time_concentration",
    ]
    rows, trajs = [], {}
    ridx = 0
    for kind in shapes:
        for _ in range(n_per):
            # Daily features: identical distribution across all groups (noise).
            rows.append({c: float(rng.uniform(0.0, 1.0)) for c in daily_cols})
            trajs[ridx] = build_trajectory(_make_shape_group(kind), n_bins=30)
            ridx += 1
    matrix = pd.DataFrame(rows)
    return matrix, trajs


def test_enrichment_beats_euclidean_only_silhouette():
    """When daily features are noise but intraday shape carries the structure,
    trajectory-enriched clustering must score a strictly higher silhouette than
    daily-only Euclidean clustering, and report non-trivial Wasserstein/DTW.
    """
    rng = np.random.default_rng(7)
    matrix, trajs = _enrichment_fixture(rng)

    daily_only = score_day(matrix, trajectories=None, k_range=(2, 5))
    enriched = score_day(matrix, trajectories=trajs, k_range=(2, 5))

    assert enriched["silhouette"] > daily_only["silhouette"], (
        f"enriched silhouette {enriched['silhouette']:.4f} must beat daily-only "
        f"{daily_only['silhouette']:.4f} when structure lives in intraday shape"
    )
    assert enriched["wasserstein_sep"] > 0.0
    assert enriched["dtw_sep"] > 0.0
    assert enriched["best_k"] >= 2


def test_score_day_reports_required_components():
    """score_day exposes every per-day component the offline harness reports."""
    rng = np.random.default_rng(11)
    matrix, trajs = _enrichment_fixture(rng)
    d = score_day(matrix, trajectories=trajs, k_range=(2, 5))
    for key in (
        "best_k", "silhouette", "silhouette_daily", "ch",
        "wasserstein_sep", "dtw_sep", "n_clusters", "degenerate",
    ):
        assert key in d, f"score_day missing component {key!r}"


def test_trajectories_none_is_byte_identical():
    """Passing trajectories=None must reproduce the no-arg (daily-only) output
    exactly — the production main.py path is unchanged this slice.
    """
    rng = np.random.default_rng(3)
    df = _make_blobs(n_per_cluster=15, n_clusters=3, rng=rng)
    a = cluster_patterns(df, k_range=(2, 5))
    b = cluster_patterns(df, trajectories=None, k_range=(2, 5))
    pd.testing.assert_frame_equal(a, b)


def test_enriched_output_has_required_columns_and_labels():
    """cluster_patterns with trajectories keeps the P5.1b contract:
    required columns, index preserved, ≥2 distinct labels when K≥2.
    """
    rng = np.random.default_rng(5)
    matrix, trajs = _enrichment_fixture(rng)
    result = cluster_patterns(matrix, trajectories=trajs, k_range=(2, 5))
    assert list(result.columns) == ["pattern_type", "pattern_explanation"]
    assert list(result.index) == list(matrix.index)
    assert result["pattern_type"].nunique() >= 2
    # No trajectory-summary column should surface in the human-facing explanation.
    for expl in result["pattern_explanation"]:
        assert "traj_" not in expl


# ===========================================================================
# Slice-4 (P5): clustering ON a precomputed DTW distance (Slice 1b)
# docs/hypotheses/p5-task1-dtw-precomputed.md
# ===========================================================================


def test_dtw_distance_matrix_symmetric_zero_diagonal():
    """_dtw_distance_matrix returns a symmetric, zero-diagonal (n,n) matrix whose
    off-diagonal entries are > 0 for distinct trajectories and 0 for identical ones.
    """
    front = build_trajectory(_make_shape_group("front"), n_bins=30)
    back = build_trajectory(_make_shape_group("back"), n_bins=30)
    traj_arr = np.stack([front, back, front.copy()])  # rows 0 and 2 identical
    D = _dtw_distance_matrix(traj_arr)

    assert D.shape == (3, 3)
    assert np.allclose(np.diag(D), 0.0), "diagonal must be zero"
    assert np.allclose(D, D.T), "distance matrix must be symmetric"
    assert D[0, 1] > 0.0, "distinct shapes must have positive DTW distance"
    assert D[0, 2] == 0.0, "identical trajectories must have zero DTW distance"


def _shape_cluster_fixture(rng):
    """3 groups whose intraday SHAPE cleanly separates them (front/back/uniform).

    Daily features are pure noise (so a Euclidean daily fit cannot find the
    structure); the DTW distance between full trajectories can. Returns
    (matrix, trajectories) on a shared RangeIndex.
    """
    n_per = 20
    shapes = ["front", "back", "uniform"]
    daily_cols = [
        "oss_mega_amount_pct", "oss_large_amount_pct", "oss_small_amount_pct",
        "ap_active_buy_pct", "ap_active_net_direction", "pi_time_concentration",
    ]
    rows, trajs = [], {}
    ridx = 0
    for kind in shapes:
        for _ in range(n_per):
            rows.append({c: float(rng.uniform(0.0, 1.0)) for c in daily_cols})
            trajs[ridx] = build_trajectory(_make_shape_group(kind), n_bins=30)
            ridx += 1
    return pd.DataFrame(rows), trajs


def test_dtw_precomputed_beats_random_silhouette():
    """Clustering on the DTW distance recovers the 3 shape groups: the resulting
    DTW-space silhouette must strongly beat a random labeling on the same matrix.

    A stub that returns arbitrary labels (or K=1) fails this.
    """
    from sklearn.metrics import silhouette_score

    rng = np.random.default_rng(7)
    matrix, trajs = _shape_cluster_fixture(rng)

    d = score_day(matrix, trajectories=trajs, k_range=(2, 5), method="dtw_precomputed")

    # Rebuild the DTW matrix independently to score a random baseline in the same space.
    traj_arr = np.stack([trajs[i] for i in range(len(matrix))])
    D = _dtw_distance_matrix(traj_arr)
    rand_labels = np.random.default_rng(0).integers(0, d["best_k"], len(matrix))
    rand_sil = silhouette_score(D, rand_labels, metric="precomputed")

    assert d["best_k"] >= 2
    assert not d["degenerate"], f"unexpected degenerate clustering: {d['cluster_sizes']}"
    assert d["silhouette"] > rand_sil, (
        f"DTW-precomputed silhouette {d['silhouette']:.4f} must beat random "
        f"labeling {rand_sil:.4f} when structure lives in intraday shape"
    )
    # Clean shapes → near-perfect recovery; sanity floor well above the Euclidean tier.
    assert d["silhouette"] > 0.5


def test_score_day_dtw_reports_required_components():
    """score_day(method='dtw_precomputed') exposes every component the harness prints,
    plus a non-stub Wasserstein/DTW separation.
    """
    rng = np.random.default_rng(11)
    matrix, trajs = _shape_cluster_fixture(rng)
    d = score_day(matrix, trajectories=trajs, k_range=(2, 5), method="dtw_precomputed")
    for key in (
        "best_k", "silhouette", "silhouette_daily", "ch",
        "wasserstein_sep", "dtw_sep", "n_clusters", "cluster_sizes", "degenerate",
    ):
        assert key in d, f"score_day missing component {key!r}"
    assert d["wasserstein_sep"] > 0.0
    assert d["dtw_sep"] > 0.0


def test_score_day_method_default_is_euclidean():
    """method defaults to 'euclidean' → byte-identical to the pre-Slice-4 call, so
    every existing caller and the production path are untouched.
    """
    rng = np.random.default_rng(11)
    matrix, trajs = _shape_cluster_fixture(rng)
    default = score_day(matrix, trajectories=trajs, k_range=(2, 5))
    euclid = score_day(matrix, trajectories=trajs, k_range=(2, 5), method="euclidean")
    assert default == euclid


def test_score_day_dtw_requires_trajectories():
    """The DTW path needs trajectories; asking for it without them fails loud
    (never silently emits a partial Task-1 number, falsification §4 metric-stub).
    """
    rng = np.random.default_rng(1)
    matrix, _ = _shape_cluster_fixture(rng)
    with pytest.raises(ValueError):
        score_day(matrix, trajectories=None, k_range=(2, 5), method="dtw_precomputed")


# ===========================================================================
# Slice-6 (P5): constraint-first (balance) Euclidean K-sweep
# docs/hypotheses/p5-task1-constrained-ksweep.md
# ===========================================================================


def _sizes_at(X: np.ndarray, k: int) -> list[int]:
    """Sorted KMeans cluster sizes at *k* (helper for constrained-sweep tests)."""
    from sklearn.cluster import KMeans

    if k < 2:
        return [X.shape[0]]
    labels = KMeans(n_clusters=k, random_state=config.RANDOM_SEED, n_init=10).fit_predict(X)
    return sorted(np.unique(labels, return_counts=True)[1].tolist())


def test_constrained_rejects_singleton_k_legacy_picks():
    """Planted 3 balanced blobs + one moderate outlier: legacy argmax-silhouette
    isolates the outlier as a SINGLETON (K=4 → [1,20,20,20]); the constrained
    sweep (min_size=2) rejects every singleton K and picks the balanced K=3
    ([20,20,21]).  A stub that ignores balance would return the singleton K.
    """
    rng = np.random.default_rng(0)
    parts = []
    for c in range(3):
        centre = np.zeros(9)
        centre[c] = 4.0
        parts.append(rng.normal(centre, 0.05, size=(20, 9)))
    outlier = np.full((1, 9), 2.0)  # moderate: isolable at K=4, absorbed at K=3
    X = np.vstack(parts + [outlier])  # n = 61

    k_legacy = _sweep_k(X, k_range=(2, 6))
    k_con, info = _sweep_k_constrained(X, k_range=(2, 6), min_size=2, max_share=0.95)

    # Legacy's winning partition contains a singleton (the isolated outlier).
    assert min(_sizes_at(X, k_legacy)) == 1, (
        f"fixture broken: legacy K={k_legacy} sizes={_sizes_at(X, k_legacy)} has no singleton"
    )
    # Constrained never returns a partition with a cluster smaller than min_size.
    con_sizes = _sizes_at(X, k_con)
    assert min(con_sizes) >= 2, f"constrained K={k_con} kept a singleton: {con_sizes}"
    assert k_con != k_legacy, "constrained must diverge from the singleton-isolating legacy K"
    assert info["feasible_k_count"] >= 1
    assert info["rejected_reason"] is None


def test_constrained_rejects_giant_cluster():
    """A 7-point blob + a 3-point blob: legacy picks K=2 ([3,7], max share 0.70);
    the constrained sweep (max_share=0.60) rejects that giant-cluster K and picks
    the balanced K=3 ([3,3,4], max share 0.40).
    """
    rng = np.random.default_rng(1)
    b0 = rng.normal(np.zeros(9), 0.01, size=(7, 9))
    b1 = rng.normal(np.array([5.0] + [0.0] * 8), 0.01, size=(3, 9))
    X = np.vstack([b0, b1])  # n = 10

    k_legacy = _sweep_k(X, k_range=(2, 3))
    k_con, info = _sweep_k_constrained(X, k_range=(2, 3), min_size=2, max_share=0.60)

    n = X.shape[0]
    assert max(_sizes_at(X, k_legacy)) / n > 0.60, (
        f"fixture broken: legacy K={k_legacy} has no >60% cluster"
    )
    con_sizes = _sizes_at(X, k_con)
    assert max(con_sizes) / n <= 0.60, f"constrained K={k_con} kept a >60% cluster: {con_sizes}"
    assert k_con != k_legacy
    assert info["feasible_k_count"] >= 1


def test_constrained_all_k_rejected_returns_one():
    """Three mutually-distant points, k_range=(2,2): the only K=2 partition is
    [2,1] (a singleton), which min_size=2 rejects → no feasible K → fall back to
    K=1 with a recorded rejected_reason (the §4 no-feasible-K falsifier signal).
    """
    X = np.array(
        [[0.0] * 9, [5.0] + [0.0] * 8, [0.0, 5.0] + [0.0] * 7], dtype=float
    )
    k_con, info = _sweep_k_constrained(X, k_range=(2, 2), min_size=2, max_share=0.95)
    assert k_con == 1
    assert info["feasible_k_count"] == 0
    assert info["rejected_reason"] is not None


def test_constrained_vacuous_matches_legacy():
    """With min_size=1 and max_share=1.0 the balance rejections never fire, so the
    constrained sweep reduces to legacy argmax-silhouette and MUST return the same
    K (regression guard: constrained is a strict superset-restriction of legacy).
    """
    rng = np.random.default_rng(0)
    df = _make_blobs(n_per_cluster=25, n_clusters=3, rng=rng)
    k_legacy = _sweep_k(df.values, k_range=(2, 6))
    k_con, _ = _sweep_k_constrained(df.values, k_range=(2, 6), min_size=1, max_share=1.0)
    assert k_con == k_legacy


def test_constrained_defaults_from_config():
    """_sweep_k_constrained with no min_size/max_share uses the config globals."""
    assert hasattr(config, "TASK1_MIN_CLUSTER_SIZE")
    assert hasattr(config, "TASK1_MAX_CLUSTER_SHARE")
    rng = np.random.default_rng(4)
    df = _make_blobs(n_per_cluster=20, n_clusters=3, rng=rng)
    # Explicit config values must match the no-arg call.
    k_default, _ = _sweep_k_constrained(df.values, k_range=(2, 6))
    k_explicit, _ = _sweep_k_constrained(
        df.values,
        k_range=(2, 6),
        min_size=config.TASK1_MIN_CLUSTER_SIZE,
        max_share=config.TASK1_MAX_CLUSTER_SHARE,
    )
    assert k_default == k_explicit


def _named_blobs(n_per_cluster: int, n_clusters: int, rng: np.random.Generator) -> pd.DataFrame:
    """Balanced blobs with real feature names (for score_day daily-matrix tests)."""
    return _make_blobs(n_per_cluster=n_per_cluster, n_clusters=n_clusters, rng=rng)


def test_score_day_constrained_reports_balance_diagnostics():
    """score_day(ksweep='constrained') reports the balance diagnostics and yields a
    non-degenerate partition on balanced blobs (every cluster ≥ min_size).
    """
    rng = np.random.default_rng(0)
    matrix = _named_blobs(n_per_cluster=20, n_clusters=3, rng=rng)
    d = score_day(matrix, trajectories=None, k_range=(2, 6), ksweep="constrained")
    for key in (
        "best_k", "silhouette", "silhouette_daily", "ch",
        "n_clusters", "cluster_sizes", "degenerate",
        "feasible_k_count", "rejected_reason",
    ):
        assert key in d, f"score_day(constrained) missing component {key!r}"
    assert not d["degenerate"], f"unexpected degenerate partition: {d['cluster_sizes']}"
    assert min(d["cluster_sizes"]) >= config.TASK1_MIN_CLUSTER_SIZE
    assert d["feasible_k_count"] >= 1
    assert d["rejected_reason"] is None


def test_score_day_ksweep_default_is_legacy():
    """ksweep defaults to 'legacy' → byte-identical to the pre-Slice-6 call, so the
    production submit path and every existing caller are untouched.
    """
    rng = np.random.default_rng(3)
    df = _make_blobs(n_per_cluster=15, n_clusters=3, rng=rng)
    default = score_day(df, trajectories=None, k_range=(2, 5))
    legacy = score_day(df, trajectories=None, k_range=(2, 5), ksweep="legacy")
    assert default == legacy


def test_score_day_constrained_silhouette_le_legacy():
    """§2.2 invariant: constrained selects argmax silhouette over a SUBSET of the K
    legacy ranks, so its reported silhouette can never exceed the legacy silhouette
    on the same daily matrix (pointwise ≤).
    """
    rng = np.random.default_rng(0)
    matrix = _named_blobs(n_per_cluster=20, n_clusters=3, rng=rng)
    d_leg = score_day(matrix, trajectories=None, k_range=(2, 6), ksweep="legacy")
    d_con = score_day(matrix, trajectories=None, k_range=(2, 6), ksweep="constrained")
    assert d_con["silhouette"] <= d_leg["silhouette"] + 1e-9
