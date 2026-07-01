# P5 — Task-1 metric-aligned clustering (Wasserstein / DTW)

**Status:** implemented + measured — **hypothesis FALSIFIED** (see §8 Results, 2026-07-01). The
measurement harness + DTW/Wasserstein computation ship as durable infrastructure; the enrichment /
composite-K mechanism is **not** wired into production (regresses silhouette). Resolves **LIS open-Q #2**.
**Date:** 2026-07-01 · **Branch:** feat/phase6-parquet-submit · **HEAD:** d429674
**Spec:** docs/LIS.md v1.6.8 · **Parent:** `docs/hypotheses/p4-pattern-type-label-gate.md`, `docs/hypotheses/competitive-gap-audit-20260701.md` (D6 Slice 1).
**LIS mapping:** H5 / Phase 5 (Task-1). **Compliance:** LIS §3.3 (label-free, no board tuning).
Related: [[normalize-exclude-leak-clustering]], [[proxy-gate-scores-capital-type-only]], [[p0629-board-h5-hard-key]].

---

## 0. The lever (do not re-litigate)

Phase-0 audit (competitive-gap-audit-20260701.md, D1.b) measured Task-1 **silhouette 0.136–0.169
every labeled day** (median **0.1509**, CH median **16.4**), Euclidean KMeans on the rank-normalized
~31-feature daily matrix — **no Wasserstein/DTW**. Task-1 is **0.4 of the board**; at the ~0.15 tier
only ≈0.06 of that 0.4 is realized. **0.65 total is arithmetically impossible while Task-1 sits at
0.15** (D1.c). 0626/0629 board collapse is **H5** (proxy↑ board↓) → Task-1, not Task-2 tuning, is the
bankable lever. Task-1 is **label-free and §3.3-safe**: silhouette/CH/Wasserstein/DTW are deterministic
functions of our own data + our own clustering — no answer key exists to tune to.

## 1. Resolving LIS open-Q #2 — what object does Wasserstein/DTW score?

**open-Q #2 (from p4 §2):** *"What object does Wasserstein/DTW score in Task 1 — per-day static
feature vectors, or intraday time-series?"*

The brief is ambiguous and the organizer has not been asked. We therefore adopt an **explicit,
falsifiable engineering assumption** (§2) rather than block. The reasoning: DTW is a *time-series*
alignment distance — it is only meaningful on **ordered intraday trajectories**, not on a single
static daily feature vector (a length-1 "series" makes DTW degenerate to |a−b|). Wasserstein is a
*distribution* distance — meaningful on the **intraday distribution** of a microstructure quantity.
Both metric names therefore point at the **intraday tick stream**, not the daily aggregate row. This
is consistent with the competition framing Task-1 as "trading-behavior *pattern*" recognition (a
shape over the session), not a static cross-sectional snapshot.

**Decision:** Wasserstein/DTW score **intraday objects** built from the same-day snapshot tick stream.
The daily-aggregate rank-normalized matrix (current P5.1 path) remains the space for the **final
KMeans fit + P5.1b naming**; the intraday metrics primarily improve **K selection and assignment
quality** (and give us the two board components we currently do not compute at all).

## 2. Assumption (documented AND implemented)

### 2.1 Intraday trajectory object (drives DTW)
For each stock-day, build a fixed-length **`N_BINS × n_series`** trajectory from the same-day snapshot
stream (intraday-only, no look-ahead — compliance #1):

- **Binning:** `N_BINS = 30` equal-count bins over the temporally-sorted tick stream (equal-count, not
  equal-time, so illiquid names still fill all bins; ties broken by arrival order). Time-of-day is
  available via Beijing `hour`/`minute`/`_tick_int` if equal-time is later preferred.
- **Series (n_series = 3), all snapshot-computable from the cleaned frame today:**
  1. `tick_amount_share` — per-bin Σ`tick_amount` / day-total (session turnover shape).
  2. `book_imbalance` — per-bin mean of `(totalbidvolume − totalaskvolume) / (totalbidvolume +
     totalaskvolume + ε)` (OBP proxy; both columns already ingested).
  3. `price_return` — per-bin Σ`price_change` / first-tick `price` (intraday return shape).
- **Edge cases:** empty group → zeros `(N_BINS, 3)`; single tick → repeat that tick across bins;
  constant series → zeros after standardization. Per-series z-standardize **within the stock-day**
  before DTW so the three series are commensurable.

### 2.2 Intraday distribution object (drives Wasserstein)
Per stock-day, the **1-D distribution** of per-bin `tick_amount_share` (and, averaged, the other two
series) — i.e. the histogram/CDF of the trajectory's turnover-share series. Wasserstein separation is
computed on these distributions via `scipy.stats.wasserstein_distance` (already available through
scipy; **no new dependency**).

### 2.3 Separation scores (↑ = better, label-free)
- `_dtw_distance(a, b)` — classic O(n²) DTW over multivariate `(N_BINS, n_series)` (pure numpy;
  **no tslearn**). Identical series → 0; shifted series → > 0.
- `_cluster_dtw_separation(trajectories, labels)` — mean pairwise DTW between **cluster centroids**
  (centroid = per-bin mean trajectory of members). Higher = clusters have more distinct shapes.
- `_cluster_wasserstein_separation(trajectories, labels)` — mean pairwise `wasserstein_distance`
  between cluster-pooled turnover-share distributions. Higher = more distinct distributions.

### 2.4 The silhouette-lifting mechanism — trajectory-summary enrichment (CORRECTION)

**Why K-reselection alone is insufficient (and a correction to a naïve first draft):** the current
`_sweep_k` already picks `K = argmax silhouette`. Any composite that merely *re-selects K on the same
daily-matrix space* can only pick a K whose Euclidean silhouette is **≤ the current max** — so pure
K-reselection **cannot raise silhouette** and would fail the acceptance criterion by construction. To
honestly lift silhouette we must change the **clustering input**, not just K.

**Mechanism:** derive a small set of **trajectory-shape summary features** from each stock-day's
`(N_BINS, 3)` trajectory and **append them to the clustering matrix** (rank-normalized with the rest,
inside the Task-1 path only — never entering Task-2). Candidate axes (all intraday-only, interpretable):
`traj_turnover_front_load` / `traj_turnover_back_load` (first/last-third turnover share),
`traj_turnover_concentration` (peak-bin share), `traj_imbalance_mean`, `traj_imbalance_trend`
(last-third − first-third book imbalance), `traj_return_amplitude` (max−min cumulative return). These
give KMeans genuinely new, behavior-discriminative axes → more coherent clusters → higher silhouette.

### 2.5 Composite K-selection (fixed global weights — NOT label/board tuned)
On the **enriched** matrix, replace the silhouette-only pick with a composite, **within-day min-max
normalized across the K candidates only** (no cross-day leakage, no board input):

```python
# Fixed, documented weights. Silhouette (on the enriched matrix) stays the primary
# term; the two intraday board-components are equal secondary nudges. NOT fit to any
# label or board score.
score(K) = sil_euclidean_enriched(K) + 0.25 * norm_wass(K) + 0.25 * norm_dtw(K)
```

`norm_wass`/`norm_dtw` are each min-max scaled to [0,1] over the K-sweep's own candidate set for that
day. Silhouette remains the dominant term so we never abandon cohesion for raw separation. Weights are
frozen constants; they are **not** searched against labels or the board.

### 2.6 What stays unchanged
- **KMeans + Euclidean silhouette** remain the fit/scoring primitives (metric family comparable to the
  D1.b baseline); the input space is enriched, honoring the EXCLUDE set
  ([[normalize-exclude-leak-clustering]]). The harness reports **both** the daily-only baseline
  silhouette (reproducing D1.b) **and** the enriched silhouette per day, so the comparison is explicit
  and honest, plus `wass_sep`/`dtw_sep` (the board components currently absent).
- **P5.1b centroid-driven relative-dominance naming** — byte-identical contract; ≥2 distinct
  `pattern_type` when K≥2.
- Trajectory clustering **replaces** the daily-matrix fit **only if** tests prove it strictly
  dominates on sil+CH (it is not assumed to; see falsification).

## 3. Seam (minimal-diff, avoids duplicate 100× reads)

`cluster.cluster_patterns(matrix)` receives **only the daily-aggregate matrix**; the raw snapshot
stream is loaded in `src/pipeline_parquet.build_feature_matrix_for_panel` (via `load_parquet`) and
discarded after `aggregate.build_feature_matrix`. Two consequences:

1. **`cluster_patterns` gains an optional `trajectories: dict[index_key, np.ndarray] | None = None`.**
   When `None` (the default, and the production `main.py` path for Slice 1), behavior is
   **byte-identical** to today → existing tests pass, Task-2 path untouched, zero production risk.
   When provided, the composite K-sweep (§2.4) is used.
2. **The Slice-1 acceptance measurement runs through the new offline harness**
   `scripts/validate_pattern_offline.py`, which loads the snapshot stream itself (mirroring
   `build_feature_matrix_for_panel`, **reusing the same `load_parquet` groups — no extra cancel/deal
   reads**), builds trajectories, and calls `cluster_patterns` with them. This keeps
   `pipeline_parquet.py` ingest paths **untouched** this slice; wiring trajectories into the
   production `main.py` submit path is an explicit **Slice-2+ decision**, gated on the offline lift
   proving out first.

This is the "build inside the harness from already-loaded snapshot groups" option from the audit —
it satisfies both "don't duplicate the 100× reads" and "don't touch production ingest paths."

## 4. Falsification (what kills this assumption)

The assumption is **rejected** (and we do NOT wire trajectories into production) if **any** hold:

- **Primary:** composite K-pick does **not** beat Euclidean-only on **< 5 of 9** labeled days
  (silhouette not strictly above the D1.b per-day value), OR median silhouette **≤ 0.1509**.
- **CH regression:** median CH drops **below 16.4** (cohesion sacrificed for separation).
- **Degeneracy:** the composite pick collapses clusters (any day → K with a cluster < 2 members, or a
  single label ≥ some large share) that Euclidean did not.
- **Metric stub:** Wasserstein/DTW cannot be computed on real data (would falsify §2's "snapshot-
  computable today" claim) → fail loud, do not emit a partial Task-1 number.

If falsified, Slice-1 still delivers value: the harness that **measures all four board components per
day** (the p4 §3 gate we never built) ships regardless, and we report the negative result.

## 5. Acceptance (VERIFY-2 must prove all)

**Task-1 lift (primary), via `validate_pattern_offline.py --all-dates` on `parquet:data/202606`,
universe `samples/stock-samples.xlsx`:**

| Metric | Baseline (audit D1.b) | Slice-1 target |
|---|---|---|
| Median silhouette | 0.1509 | strictly > 0.1509 |
| Median CH | 16.4 | ≥ 16.4 (no regression) |
| Days silhouette strictly ↑ | — | ≥ 5 of 9 |
| Wasserstein / DTW | absent | reported every day, not stub |

**Task-2 isolation (mandatory, byte-identical — Slice-1 touches no Task-2 code):**
capital weighted-F1 **0.6438**/n=122, intention **0.6750**/n=115; floors through-0624 ≥0.6773,
through-0625 ≥0.6500, P2-intent-b ≥0.6271. Any drift → FAIL gate.

**Suite:** current baseline green + new tests (≥186 passed, 2 xfailed or better).

## 6. Scope / compliance

- **Touch:** `src/cluster.py`, new `src/intraday_trajectory.py` (≤120 lines), new
  `scripts/validate_pattern_offline.py`, `tests/test_cluster.py` (+ maybe
  `tests/test_intraday_trajectory.py`). Optional `config.TASK1_N_BINS` with justification.
- **Do NOT touch:** `src/rules.py`, `src/label.py`, `src/features.py`, `config.py` intent/capital
  constants, `tests/fixtures/validation_labels.csv`, `src/model.py`,
  `src/pipeline_parquet.py` ingest paths.
- **Deps:** numpy + `scipy.stats.wasserstein_distance` only (scipy already present via sklearn).
  **No tslearn, no pip install** without a written blocker note + human approval.
- **§3.3:** no reading of Tianchi scores to pick K, weights, or thresholds. Metrics are label-free.

## 7. Deferred (NOT this slice)
Wiring trajectories into `main.py` production submit (Slice-2 gate) · OFI / ap_run_max / OBP spread /
PI herfindahl (Slice 2) · intention rank-relative gate (Slice 3) · GBDT head · label CSV expansion ·
P3.3 cadence flip · batch-cancel perf.

---

## 8. Results (2026-07-01) — HYPOTHESIS FALSIFIED

`validate_pattern_offline.py --input parquet:data/202606 --all-dates` (universe
`samples/stock-samples.xlsx`, TASK1_EXIT=0):

| date | best_K | sil (enriched) | sil (daily-only) | audit D1.b | CH | wass_sep | dtw_sep | nclust |
|------|-------:|---------------:|-----------------:|-----------:|-----:|---------:|--------:|-------:|
| 20260616 | 6 | 0.1526 | 0.1670 | 0.1685 | 14.9 | 0.0089 | 9.33 | 6 |
| 20260617 | 6 | 0.1294 | 0.1390 | 0.1445 | 13.5 | 0.0133 | 12.64 | 6 |
| 20260618 | 8 | 0.0945 | 0.1303 | 0.1355 | 10.6 | 0.0087 | 8.25 | 8 |
| 20260622 | 6 | 0.1308 | 0.1403 | 0.1596 | 13.2 | 0.0141 | 16.51 | 6 |
| 20260623 | 9 | 0.1480 | 0.1445 | 0.1426 | 11.2 | 0.0152 | 15.96 | 9 |
| 20260624 | 6 | 0.1307 | 0.1505 | 0.1564 | 13.3 | 0.0093 | 10.14 | 6 |
| 20260625 | 6 | 0.1422 | 0.1548 | 0.1583 | 14.1 | 0.0113 | 13.33 | 6 |
| 20260626 | 11 | 0.1147 | 0.1453 | 0.1509 | 10.2 | 0.0065 | 4.15 | 11 |
| 20260629 | 9 | 0.1257 | 0.1427 | 0.1437 | 11.0 | 0.0091 | 11.66 | 9 |
| **median** | — | **0.1307** | **0.1445** | **0.1509** | **13.2** | — | — | — |

**Every falsification trigger in §4 fired:**
- Median enriched silhouette **0.1307 ≤ 0.1509** (and *below* the same-harness daily-only 0.1445).
- Days silhouette > audit D1.b: **1/9** (only 20260623) — needs ≥5.
- Median CH **13.2 < 16.4**.
- Wasserstein/DTW **are** computed & reported every day (non-stub) — the one criterion that passed.

**Root cause (measured, two effects):**
1. **Composite weights mis-scaled vs silhouette's dynamic range.** Silhouette differences across K are
   ~0.01–0.03; the `0.25 * norm_{wass,dtw}` terms span up to 0.25 (each min-maxed to [0,1] across
   candidates). So the separation terms **dominate** K selection — the composite picks the highest-
   separation K (e.g. 0626→K=11, 0618→K=8), *not* a silhouette-cohesive one. This violates the doc's
   own "silhouette remains the dominant term" intent. Silhouette-dominant reweighting could recover
   ~daily-only silhouette but (see 2) still cannot exceed baseline.
2. **Trajectory-summary enrichment lowers silhouette even before K effects.** Daily-only (0.1445) is
   itself slightly *below* audit D1.b (0.1509) here — a **panel difference** (audit used labeled∪samples
   ~109–116 stocks; production/harness uses the samples universe ~99–100) — and appending 6 traj_*
   axes dilutes Euclidean cohesion rather than sharpening it. The intraday-shape axes are not more
   cluster-coherent than the existing daily features on this corpus.

**Conclusion:** metric alignment via trajectory enrichment + composite-K **does not** buy a Task-1
silhouette/CH lift on data/202606; it regresses both. Per §4 this is a rejection — trajectories are
**not** wired into production (`cluster_patterns` default `trajectories=None`, main.py byte-identical).

**Durable value shipped anyway (per §4):**
- The **offline Task-1 clustering-quality gate** (`validate_pattern_offline.py`) — the p4 §3 gate that
  never existed — now measures silhouette/CH/Wasserstein/DTW per day, label-free (§3.3-safe).
- **Wasserstein & DTW separations are now computable** on the real corpus (were absent). These are two
  of the four board Task-1 components; we can now track them even if we can't yet move them.
- **K-selection is quantified** as separation-dominated when the composite is on — a concrete input to
  any future Task-1 work.

**What did NOT change (verified):** Task-2 capital 0.6438/n=122 and intention 0.6750/n=115 reproduce
byte-identical; production submit path unchanged.

**Recommendation for next Task-1 attempt (needs human go — do NOT auto-iterate, §3.3/H5 discipline):**
The bankable-Task-1-lever thesis (audit D1) is **not refuted** — only *this mechanism* is. Candidate
follow-ups, each a fresh falsifiable experiment: (a) cluster in a **DTW-precomputed distance** and
report DTW-silhouette (`metric='precomputed'`), a purer metric alignment than Euclidean-on-enriched;
(b) select trajectory features by measured cohesion contribution instead of appending all 6;
(c) re-baseline against the labeled∪samples panel so the comparison is exact. **Not pursued this slice
— reported as the honest negative.**
