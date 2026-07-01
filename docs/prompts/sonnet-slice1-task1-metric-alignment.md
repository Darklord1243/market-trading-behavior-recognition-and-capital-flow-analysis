# Slice-1 execution spec — Task-1 metric alignment (DTW / Wasserstein)

> **Execution note (binding decision):** this slice was **executed inline by the Opus lead**, not
> dispatched to Sonnet — per the user directive *"Opus inline (my memory)"* (memory:
> [[subagent-shell-fanout-unacceptable]]), which overrode the orchestrator prompt's Sonnet-dispatch
> Model rule. This file is retained as the **execution record / spec** the work was built against.
>
> **Spec:** docs/hypotheses/p5-task1-metric-alignment.md · **LIS** H5 / Phase 5.
> **Python:** `C:/Users/ASUS/anaconda3/python.exe` · **TDD, minimal diff, no commit until human gate.**

---

## Scope (what was touched)

| Touched | Not touched (frozen) |
|---|---|
| `src/intraday_trajectory.py` (new, ≤120 lines) | `src/rules.py`, `src/label.py`, `src/features.py` |
| `src/cluster.py` (added helpers + optional `trajectories` param) | `src/model.py`, `src/pipeline_parquet.py` (ingest paths) |
| `scripts/validate_pattern_offline.py` (new offline harness) | `config.py` intent/capital constants |
| `tests/test_intraday_trajectory.py`, `tests/test_cluster.py`, `tests/test_validate_pattern_offline.py` | `tests/fixtures/validation_labels.csv` |

**Deps:** numpy + `scipy.stats.wasserstein_distance` only (scipy already present via sklearn).
**No tslearn, no pip install.**

## What was built

**B1. Intraday trajectory builder** (`src/intraday_trajectory.py`)
- `build_trajectory(group, n_bins=30) -> (n_bins, 3)` — equal-count bins of
  `[tick_amount_share, book_imbalance, price_return]`; empty→zeros; sparse day (n<bins)→upsample by
  repeating ticks in arrival order (single tick → identical across bins). Intraday-only, no look-ahead.
- `summary_features(traj) -> dict` — 6 shape axes (front/back-load, concentration, imbalance
  mean/trend, return amplitude) = the clustering-enrichment features (`SUMMARY_COLS`).
- `build_trajectories(df) -> {(stock_code, date): traj}` — grouped from the snapshot frame the pipeline
  already loads (no extra per-stock reads).

**B2. Metric helpers** (`src/cluster.py`, pure numpy + scipy)
- `_dtw_distance(a, b)` — classic O(n²) multivariate DTW; identical→0, shifted→>0, symmetric.
- `_cluster_dtw_separation(traj_arr, labels)` — mean pairwise DTW between cluster **centroid** trajectories.
- `_cluster_wasserstein_separation(traj_arr, labels)` — mean pairwise Wasserstein between cluster
  turnover-share distributions.

**B3. Composite K-sweep + enrichment**
- `build_clustering_matrix(matrix, trajectories)` — rank-normalized clustering matrix; appends
  `SUMMARY_COLS` when trajectories given; `naming_feats` excludes traj_* so centroid naming reads only
  finance features. With `trajectories=None` → **byte-identical** to pre-P5.
- `_composite_sweep(X, traj_arr, k_range)` — `score(K) = sil + 0.25*norm_wass + 0.25*norm_dtw`,
  wass/dtw min-max normalized within-day across K candidates only (fixed weights, not tuned).
- `cluster_patterns(matrix, k_range=None, trajectories=None)` — uses composite sweep when trajectories
  given, else the original silhouette sweep (production main.py path unchanged this slice).
- `score_day(matrix, trajectories=None, k_range=None)` — per-day report seam for the harness.

**B4. P5.1b naming contract** — unchanged; ≥2 distinct `pattern_type` when K≥2; traj_* never named.

**B5. Offline harness** (`scripts/validate_pattern_offline.py`)
- `--input parquet:data/202606 --date YYYYMMDD | --all-dates`; universe default
  `samples/stock-samples.xlsx`. Per day reports best_K, silhouette (enriched), silhouette_daily
  (baseline), CH, wasserstein_sep, dtw_sep, n_clusters, degeneracy — **components only, no blended
  score**. Exit 0 on success, 1 on missing/malformed data.

**B6. TDD** — DTW identity/shift, planted-K recovery (unchanged), enrichment-beats-Euclidean-only
silhouette on a synthetic trajectory fixture, byte-identical None path, required-columns/labels,
harness smoke + date discovery.

## Acceptance (see Slice-1 report for measured numbers)
- Task-1: median silhouette > 0.1509, median CH ≥ 16.4, ≥5/9 days silhouette above audit D1.b,
  Wasserstein/DTW reported every day.
- Task-2 isolation: capital 0.6438/n=122 and intention 0.6750/n=115 byte-identical (verified).
- Suite: ≥186 passed + new tests green.
