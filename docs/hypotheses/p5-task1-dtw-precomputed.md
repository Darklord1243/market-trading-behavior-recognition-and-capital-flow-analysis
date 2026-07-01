# P5 — Task-1 clustering on a precomputed DTW distance (Slice 4 / Slice 1b)

**Status:** measured — **hypothesis FALSIFIED** (see §8 Results, 2026-07-01) via the **degeneracy**
trigger: DTW-silhouette clears the bar (median 0.3808 > 0.1509) but only because average-linkage
singleton-chaining collapses every day to one giant cluster + singletons — the high silhouette is the
artifact, not signal. Slice-4 follow-up (a) of `docs/hypotheses/p5-task1-metric-alignment.md` §8
("cluster in a **DTW-precomputed distance** and report DTW-silhouette (`metric='precomputed'`), a purer
metric alignment than Euclidean-on-enriched"). Production unchanged (`method="euclidean"` default).
**Date:** 2026-07-01 · **Branch:** feat/phase6-parquet-submit · **HEAD:** <after slice 3 doc commit>
**Spec:** docs/LIS.md v1.6.8 · **Parents:** `competitive-gap-audit-20260701.md` (D1),
`p5-task1-metric-alignment.md` (Slice 1 enrichment FALSIFIED), Slices 2 & 3 (both FALSIFIED).
**LIS mapping:** H5 / Phase 5 (Task-1). **Compliance:** LIS §3.3 (label-free, no board tuning).
Related: [[p5-task1-metric-alignment-falsified]], [[normalize-exclude-leak-clustering]],
[[proxy-gate-scores-capital-type-only]], [[p0629-board-h5-hard-key]].

---

## 0. The lever (unchanged — do not re-litigate)

Audit D1 (competitive-gap-audit-20260701.md): Task-1 is **0.4 of the board**; we cluster Euclidean-only
at silhouette median **0.1509** (CH median **16.4**), realizing only ≈0.06 of that 0.4. Task-1 is the
bankable, **label-free / §3.3-safe** lever (silhouette/CH/Wasserstein/DTW are deterministic functions of
our own data + our own clustering — no answer key to tune to). Slice 1 proved that **enriching the
Euclidean feature matrix** with trajectory-shape summaries does **not** lift silhouette (it regressed:
median 0.1307 vs 0.1509). The lever thesis was *not* refuted — only that mechanism was.

## 1. What is different from Slice 1 (the precise new bet)

Slice 1 stayed in **Euclidean space**: it appended 6 `traj_*` summary columns to the daily matrix and
kept KMeans + Euclidean silhouette. This slice does the **orthogonal thing** — it never touches the
daily feature matrix. It clusters **directly on the pairwise DTW distance** between the full
`(N_BINS, 3)` intraday trajectories and scores silhouette in that **same DTW metric**
(`silhouette_score(D, labels, metric='precomputed')`).

| | Slice 1 (FALSIFIED) | Slice 4 (this doc) |
|---|---|---|
| Clustering input | daily matrix ⊕ 6 traj summaries | pairwise DTW distance matrix `D (n×n)` |
| Fit primitive | KMeans (Euclidean) | AgglomerativeClustering `metric='precomputed'`, `linkage='average'` |
| Silhouette metric | Euclidean on enriched matrix | **DTW-precomputed** (same space it clustered in) |
| K selection | composite `sil + .25 wass + .25 dtw` | **argmax DTW-silhouette** (single, honest objective) |

Rationale: DTW is a *shape-alignment* distance. Summarizing a 30-bin shape into 6 scalars (Slice 1)
throws away exactly the alignment information DTW is built to exploit. Clustering on the DTW distance
directly is the *only* way to test whether the intraday trajectory shape carries cluster structure the
daily aggregate misses. This is the purest form of the audit's "metric-aligned Task-1" idea.

## 2. Assumption (documented AND implemented)

- **Trajectory object:** reuse `src/intraday_trajectory.build_trajectories` **unchanged** — same
  `(N_BINS=30, 3)` `[tick_amount_share, book_imbalance, price_return]` equal-count trajectory Slice 1
  shipped. No new trajectory columns; no `traj_*` summaries enter anything.
- **Distance:** reuse `src/cluster._dtw_distance` (classic O(n²) multivariate DTW, pure numpy) to build
  a symmetric zero-diagonal `D (n×n)`. Built **once per day**, reused across the K-sweep.
- **Clustering:** `AgglomerativeClustering(n_clusters=k, metric='precomputed', linkage='average')`
  (average linkage — the simplest correct precomputed-metric clusterer; PAM/k-medoids would need
  `sklearn_extra`, which is **not installed** and forbidden to pip-pull, LIS §3.3 dep rule).
- **K-sweep:** over `config.K_RANGE = (6, 12)` clamped to `[2, n-1]`, pick **K = argmax
  DTW-silhouette** (`silhouette_score(D, labels, metric='precomputed')`). Single objective — no
  composite weights (Slice 1's separation-term mis-scaling was a root cause of its failure).
- **Reported components:** DTW-silhouette (primary), CH on the **flattened trajectory space**
  (`traj_arr.reshape(n, -1)`, the Euclidean approximation of the space DTW clusters in — so CH is
  internally consistent with the labels, *not* the daily-matrix CH), plus `wass_sep` / `dtw_sep`
  (reused `_cluster_*_separation`) and the daily-only Euclidean silhouette baseline for context.

### 2.1 The comparability caveat (stated honestly up front)

DTW-silhouette and the audit's Euclidean silhouette **0.1509 live in different metric spaces** — a raw
`>` comparison is apples-to-oranges and we say so. We adopt the spec's bar (`> 0.1509`) as the
**acceptance gate anyway**, because: (a) it is the only pre-registered, non-tunable number we have; and
(b) the *decision* it drives is binary and correct regardless of unit — wire DTW clustering into
production **only if** it demonstrably out-separates the Euclidean baseline by a margin that survives
the space caveat. A DTW-silhouette that merely equals ~0.15 is **not** a win (same tier, more compute).

## 3. Seam (minimal-diff, offline-only)

- `src/cluster.py` gains `_dtw_distance_matrix(traj_arr)` and a `method` param on `score_day`
  (`method="euclidean"` default → **byte-identical** to today; `method="dtw_precomputed"` → new path).
  `cluster_patterns` is **untouched** (production `main.py` never calls the DTW path).
- `scripts/validate_pattern_offline.py` gains `--method {euclidean,dtw-precomputed}` (default
  `euclidean` → existing behavior byte-identical). DTW path reuses the **same** batched snapshot read
  the harness already does for trajectories — no extra parquet I/O.
- **Production submit path (`main.py`, `pipeline_parquet.py`) is not touched.** Promotion to production
  is a separate, gated decision only if this slice proves out.

## 4. Falsification (what kills this assumption)

Rejected (do NOT wire DTW clustering into production) if **any** hold:

- **Primary:** median DTW-silhouette **≤ 0.1509** (audit D1.b median) across the labeled days.
- **CH regression:** median CH (flattened-traj space) **< 16.4**.
- **Degeneracy:** any day's best-K produces a cluster with **< 2 members** (average linkage is prone to
  singleton chaining) that a coherent solution would not.
- **Metric stub:** DTW distance / precomputed silhouette cannot be computed on the real corpus.
- **Task-2 regression:** any Task-2 gate drifts (capital 0.6438 / intention 0.6750 / floors). This path
  is Task-1-isolated and must not touch it; a drift means an accidental leak → FAIL.

## 5. Acceptance (VERIFY must prove all)

- `validate_pattern_offline.py --input parquet:data/202606 --all-dates --method dtw-precomputed`:
  **median DTW-silhouette STRICTLY > 0.1509**, median CH ≥ 16.4, no degenerate day, wass/dtw non-stub.
- Task-2 gates **byte-identical** (capital 0.6438/n=122, intention 0.6750/n=115, through-0624 ≥0.6773,
  through-0625 ≥0.6500, P2-intent-b ≥0.6271) — DTW path off by default proves isolation.
- Suite **≥204 passed, 2 xfailed** (new DTW tests added).

## 6. Scope / compliance

- **Touch:** `src/cluster.py` (add DTW-matrix + `method` seam), `scripts/validate_pattern_offline.py`
  (add `--method` flag), `tests/test_cluster.py` (new DTW-precomputed tests).
- **Do NOT touch:** `src/rules.py`, `src/label.py`, `src/features.py`, `config.py` intent/capital
  constants + scorer thresholds, `tests/fixtures/validation_labels.csv`, `src/model.py`,
  `src/pipeline_parquet.py` ingest paths, `src/intraday_trajectory.py` (reused as-is).
- **Deps:** sklearn (`AgglomerativeClustering`, already present) + numpy only. No tslearn, no pip.
- **Fallback (documented):** if the O(n²·N_BINS²) DTW matrix is too slow on the ~100-stock panel,
  vectorize the per-pair local cost (cdist) or cap N_BINS — recorded in §Results, not silently applied.

## 7. Deferred (NOT this slice)
Wiring DTW clustering into `main.py` (gated on this proving out) · feature-cohesion-selected traj
summaries (Slice 1 follow-up b) · labeled∪samples re-baseline (follow-up c) · GBDT head · label CSV
expansion · batch-cancel perf.

---

## 8. Results (2026-07-01) — HYPOTHESIS FALSIFIED (degeneracy trigger)

`validate_pattern_offline.py --input parquet:data/202606 --all-dates --method dtw-precomputed`
(universe `samples/stock-samples.xlsx`, TASK1_EXIT=0). Runtime ≈ 5m45s/day (O(n²·N_BINS²) DTW
matrix on ~100 stocks) — feasible, no fallback needed.

| date | best_K | DTW-sil | sil_daily | audit D1.b | CH | wass_sep | dtw_sep | cluster_sizes |
|------|-------:|--------:|----------:|-----------:|-----:|---------:|--------:|---------------|
| 20260616 | 6 | 0.3035 | 0.1670 | 0.1685 | 84.4 | 0.0106 | 15.63 | [58, 26, 8, 6, **1, 1**] |
| 20260617 | 6 | 0.3403 | 0.1390 | 0.1445 | 110.0 | 0.0176 | 20.47 | [11, 3, 62, 4, 18, **1**] |
| 20260618 | 6 | 0.5422 | 0.1303 | 0.1355 | 31.2 | 0.0210 | 26.03 | [91, 2, 3, **1, 1, 1**] |
| 20260622 | 6 | 0.3808 | 0.1403 | 0.1596 | 84.9 | 0.0151 | 21.64 | [12, 71, 5, 2, 8, **1**] |
| 20260623 | 6 | 0.4149 | 0.1445 | 0.1426 | 108.8 | 0.0184 | 20.45 | [49, 5, 39, 3, **1**, 2] |
| 20260624 | 6 | 0.4295 | 0.1505 | 0.1564 | 62.7 | 0.0240 | 26.38 | [81, 7, 6, 2, **1**, 2] |
| 20260625 | 6 | 0.4248 | 0.1548 | 0.1583 | 85.7 | 0.0151 | 19.24 | [42, 6, 48, 2, **1, 1**] |
| 20260626 | 6 | 0.3561 | 0.1453 | 0.1509 | 45.4 | 0.0102 | 20.42 | [62, 3, 8, **1**, 3, 23] |
| 20260629 | 6 | 0.3571 | 0.1427 | 0.1437 | 34.4 | 0.0169 | 22.40 | [3, 4, 78, 13, **1, 1**] |
| **median** | **6** | **0.3808** | **0.1445** | **0.1509** | **84.4** | — | — | — |

**The two headline metrics "pass" — and both are artifacts of the third trigger:**
- Median DTW-silhouette **0.3808 > 0.1509** (9/9 days above audit D1.b). *But see the caveat §2.1: this
  is a DTW-space number, not directly comparable to the Euclidean baseline.*
- Median CH **84.4 ≥ 16.4** (flattened-traj space).
- **Every one of the 9 days is DEGENERATE** (falsification §4, third trigger): each has ≥1 singleton
  cluster, and the panel collapses to **one giant cluster (50–91% of stocks) + a scatter of size-1/2
  clusters**. This is textbook **average-linkage singleton-chaining**: the linkage peels far-outlier
  trajectories off one at a time; a lone outlier scores silhouette ≈ 1 and its distance from the bulk
  inflates CH — so the very degeneracy that disqualifies the solution is *what produces* the high
  silhouette/CH. The metrics are not measuring six coherent behavioral modes; they are measuring
  outlier isolation.

**Corroborating tell — `best_K = 6` on all 9 days (the K_RANGE floor).** DTW-silhouette is monotonically
*decreasing* over K∈[6,12]; the clusterer would take K=2 if allowed (→ `[~98, ~2]`). The DTW distance
structure of the intraday trajectories is **"one dominant mode + rare outliers," not a 6-way partition**
into tradeable pattern types. Forcing balanced clusters would collapse the silhouette back toward the
Euclidean tier.

**Conclusion:** clustering on a precomputed DTW distance with average linkage **does not** deliver a
genuine Task-1 clustering-quality lift on data/202606 — it produces degenerate giant-cluster+singleton
partitions whose inflated silhouette/CH are pathology, not signal. Per §4 (degeneracy on any day) this
is a **rejection**. The DTW path stays behind the default-off `--method` flag / `method="euclidean"`
default; production `main.py`/`cluster_patterns` are byte-identical (Task-2 unaffected).

**Why it failed where the idea sounded right:** DTW *shape*-distance between intraday trajectories is
dominated by a few extreme-shape names (halt/one-sided/thin-tape days) that sit far from everyone in
DTW space. Average linkage rewards isolating them. The bulk of stock-days have *similar* intraday
turnover/imbalance shapes (the market's common rhythm), so they do not sub-partition into six coherent
DTW clusters. This is consistent with Slice 1's finding that trajectory *summaries* did not sharpen
Euclidean cohesion either — on this corpus the intraday shape simply does not carry a clean 6-way
behavioral partition the daily matrix misses.

**Durable value (if kept — human decision at gate):** the `--method dtw-precomputed` harness path now
measures DTW-space silhouette / CH / separations per day and, crucially, **surfaces `cluster_sizes`** so
singleton-chaining is legible rather than hidden behind a one-word flag — a reusable diagnostic for any
future precomputed-metric Task-1 attempt.

**What did NOT change (verified):** production Task-1 (`cluster_patterns`) and all Task-2 code are
untouched; `method` defaults to `"euclidean"` (byte-identical). Full suite green (see VERIFY).

**Recommendation (needs human go — do NOT auto-iterate, §3.3/H5 discipline):** the degeneracy is a
property of **average linkage on DTW**, not necessarily of DTW clustering per se. A *fresh* falsifiable
attempt could try a linkage/algorithm that resists singleton-chaining under a precomputed metric
(complete/Ward-on-embedded, or k-medoids if an offline-installed implementation appears) **with a
minimum-cluster-size or balance constraint baked into the acceptance** so a giant-cluster+singleton
solution cannot "win" on silhouette. Two mechanisms are now falsified (Slice-1 enrichment, Slice-4
average-linkage-DTW); the audit-D1 lever thesis is still not refuted, but the bar for the next attempt
is higher. **Not pursued this slice — reported as the honest negative.**
</content>
</invoke>
