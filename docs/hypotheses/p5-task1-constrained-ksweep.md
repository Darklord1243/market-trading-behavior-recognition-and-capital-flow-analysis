# P5 — Task-1 constrained (balance-first) Euclidean K-sweep (Slice 6)

**Status:** measured — **hypothesis FALSIFIED** (2026-07-02, see §8): the balance constraint is a
**no-op** on data/202606 (constrained ≡ legacy K on all 9 days; 7/7 feasible K; balanced sizes every
day) — the strict "beat audit D1.b" gate is unreachable by construction (§2.2), and the real finding is
that the production Euclidean Task-1 path is **not degenerate**. Production unchanged; harness + tests
kept default-off (`ksweep="legacy"`).
**Date:** 2026-07-02 · **Branch:** feat/phase6-parquet-submit · **HEAD:** 9c5a06d (+ optional label-audit doc commit)
**Spec:** docs/LIS.md v1.6.8 · **Parents:** `competitive-gap-audit-20260701.md` (D1.b),
`p5-task1-metric-alignment.md` (Slice 1 enrichment FALSIFIED),
`p5-task1-dtw-precomputed.md` (Slice 4 DTW FALSIFIED — degeneracy trigger),
`p4-youzi-guard-000657-audit.md` (5B closed — Task-2 guard dead).
**LIS mapping:** H5 / Phase 5 (Task-1). **Compliance:** LIS §3.3 (label-free, no board tuning).
Related: [[p5-task1-metric-alignment-falsified]], [[slice4-dtw-precomputed-falsified]],
[[normalize-exclude-leak-clustering]], [[proxy-gate-scores-capital-type-only]], [[p0629-board-h5-hard-key]].

---

## 0. The lever (unchanged — do not re-litigate)

Audit D1 (competitive-gap-audit-20260701.md): Task-1 is **0.4 of the board**; production Euclidean
KMeans clusters at silhouette median **0.1509** (CH median **16.4**), realizing ≈0.06 of that 0.4.
Task-1 is the bankable, **label-free / §3.3-safe** lever. Two mechanisms are already falsified:
**Slice 1** (append `traj_*` summaries to the Euclidean matrix → regressed silhouette) and **Slice 4**
(cluster on the precomputed DTW distance with average linkage → degenerate giant-cluster+singleton
partitions whose high DTW-silhouette was pathology, not signal).

## 1. What is different from Slices 1/4 (the precise new bet)

Slice 4's post-mortem recommended the next attempt bake a **balance / minimum-cluster-size
constraint into the acceptance so a giant-cluster+singleton solution cannot "win" on silhouette.**
This slice takes that recommendation but keeps the **production Euclidean path** — it does **not**
touch trajectories, DTW, or the daily feature matrix. The only change is *how K is selected*:

Production `_sweep_k` (src/cluster.py) picks `K = argmax Euclidean silhouette` over `config.K_RANGE`
with a single 2-distinct-labels check. It performs **no balance test** — nothing stops it from
selecting a K whose winning silhouette is driven by an imbalanced partition (one dominant cluster +
tiny satellites), the same pathology that disqualified Slice 4. This slice adds a **constraint-first**
sweep: reject imbalanced candidate K **before** comparing silhouette, then argmax silhouette among the
feasible survivors only.

| | Production `_sweep_k` (legacy) | `_sweep_k_constrained` (this slice) |
|---|---|---|
| Feature matrix | rank-normalized daily matrix (`trajectories=None`) | **same, byte-identical** |
| Fit primitive | `KMeans(RANDOM_SEED, n_init=10)` | **same** |
| Candidate K | `K_RANGE = (6,12)` clamped to `[2, n-1]` | **same** |
| Feasibility test | `len(unique(labels)) ≥ 2` | `≥2` **AND** `min(size) ≥ 2` **AND** `max(size)/n ≤ 0.60` |
| Selection | argmax silhouette (tie-break CH) over all K | argmax silhouette (tie-break CH) over **feasible** K |

## 2. Mechanism (production Euclidean path only)

For each candidate `K` in `config.K_RANGE` (6–12), clamped to `[2, n-1]`:
1. Fit `KMeans(n_clusters=K, random_state=RANDOM_SEED, n_init=10)` on the daily clustering matrix `X`
   (from `build_clustering_matrix(matrix, trajectories=None)` — byte-identical to today).
2. Compute `cluster_sizes = np.unique(labels, return_counts=True)`.
3. **REJECT** candidate `K` if ANY:
   - `len(cluster_sizes) < 2` (KMeans collapsed labels), OR
   - `min(cluster_sizes) < TASK1_MIN_CLUSTER_SIZE` (default 2), OR
   - `max(cluster_sizes) / n > TASK1_MAX_CLUSTER_SHARE` (default 0.60 — no cluster > 60% of panel).
4. Among **feasible K only**: pick `argmax silhouette` (tie-break Calinski-Harabasz, same as legacy).
   If **no** K is feasible, fall back to `K=1` and record `rejected_reason` (a real signal — see §4).

### 2.1 Constants (fixed globals in config.py — NOT tuned to any board or label)

```
TASK1_MIN_CLUSTER_SIZE  = 2     # silhouette needs ≥1 neighbour; a singleton is not a "behavioral mode"
TASK1_MAX_CLUSTER_SHARE = 0.60  # a cluster holding >60% of the panel is the "one dominant mode" pathology,
                                # not a discovered partition (Slice-4 giant clusters ran 50–91%)
```

Rationale is **microstructure/degeneracy reasoning, not fitting**: a size-1 cluster contributes a
silhouette of ≈1 by construction (its `a(i)` is undefined → sklearn treats it as 0) and inflates the
score without describing a real behavior; a >60%-share cluster is the DTW pathology's Euclidean twin.
Both thresholds are round, defensible, pre-registered globals — they are **never** swept against the
board (LIS §3.3), and they are **not** derived from the labeled days.

### 2.2 Predicted relationship — READ THIS BEFORE INTERPRETING RESULTS (honest up front)

`_sweep_k_constrained` selects `argmax silhouette` over a **subset** of the K candidates the legacy
sweep ranks (it only ever *adds* rejection rules). Therefore, **pointwise on every day**:

```
constrained_silhouette(day) ≤ legacy_silhouette(day)      (argmax over a subset ≤ argmax over the superset)
```

The constraint can only **lower or equal** the selected silhouette — never raise it. Two consequences,
stated plainly so the Results are not over-read:

- The "**median silhouette strictly > 0.1509**" and "**≥5/9 days strictly > audit D1.b**" success
  criteria (§5) are, by this inequality, **essentially unreachable by construction** — a constrained
  argmax cannot out-score the unconstrained argmax it is a subset of, and current legacy daily
  silhouette already sits *below* the frozen audit-D1.b table on 8/9 days (Slice-4 doc §8 `sil_daily`
  column). Under the strict letter of §5 this slice is expected to **falsify → production unchanged**.
- The genuinely informative question this slice answers is therefore **NOT** "does the constraint beat
  the baseline?" (it provably cannot) but "**does the balance constraint ever *bind* on the production
  Euclidean path — i.e., is production degenerate the way the Slice-4 DTW path was?**" The reported
  `cluster_sizes`, `feasible_k_count`, and `rejected_reason` per day are the real deliverable:
  - If constrained ≡ legacy on all 9 days (constraint never binds) → **positive confirmatory finding**:
    the production Euclidean partition is *not* degenerate (no >60% giant cluster, no singletons); the
    Slice-4 pathology is specific to average-linkage-on-DTW and does **not** afflict production. The
    constraint is a costless safety rail worth keeping as a default-on guard *iff* it is a no-op.
  - If constrained < legacy on some days (constraint binds) → production is silently picking imbalanced
    K on those days; we quantify the silhouette cost of forcing balance and surface which days.

This slice is run as an **honest diagnostic** under the pre-registered strict gate, not as a bet we
expect to win the letter of §5. The value is the degeneracy measurement, not a silhouette lift.

## 3. Seam (minimal-diff, offline-first)

- `src/cluster.py` gains `_sweep_k_constrained(X, k_range, min_size, max_share)`. `_sweep_k` (legacy) is
  left **byte-identical** — the two coexist; no legacy caller changes.
- `score_day` gains a `ksweep` param (`"legacy"` default → byte-identical; `"constrained"` → Euclidean
  daily path scored with `_sweep_k_constrained`, reporting `cluster_sizes`, `feasible_k_count`,
  `rejected_reason`). The constrained path is Euclidean-only (raises on `method="dtw_precomputed"`).
- `scripts/validate_pattern_offline.py` gains `--ksweep {legacy,constrained}` (default `legacy` →
  existing behavior byte-identical). Constrained run measures the **daily** matrix directly (no DTW
  separations) → fast and apples-to-apples with the production submit path.
- **Production `cluster_patterns` / `main.py` are NOT touched in the harness phase.** Wiring the
  constrained sweep into production is a **separate, gated** step taken **only if §5 passes**.

## 4. Falsification (revert production wiring if ANY)

- median silhouette **≤ 0.1509** (audit D1.b), OR
- median CH **< 16.4**, OR
- days with silhouette strictly **>** the audit-D1.b per-date baseline: **< 5 of 9**, OR
- **any** labeled day has **NO feasible K** in `K_RANGE` (all candidates violate the constraints —
  would force `K=1`, an inference-path regression), OR
- **any** Task-2 gate drifts (capital 0.6438 / intention 0.6750 / through-0624 0.6773 /
  through-0625 0.6500 / P2-intent-b 0.6271).

Per §2.2 the first three are expected to trip by construction; the fourth (no-feasible-K) is the
*safety* falsifier — if the constraint ever starves a day of all K, the rail is too aggressive and
must **not** be wired even as a guard.

## 5. Success (promote to production `cluster_patterns`)

- median silhouette **strictly > 0.1509**, AND
- median CH **≥ 16.4**, AND
- **≥ 5/9** days silhouette **>** the `_AUDIT_D1B` per-date baseline, AND
- **every** day: a feasible K exists + `cluster_sizes` reported + non-degenerate per constraints, AND
- Task-2 gates **byte-identical**.

## 6. Scope / compliance

- **Touch:** `src/cluster.py` (add `_sweep_k_constrained` + `ksweep` seam on `score_day`),
  `config.py` (add `TASK1_MIN_CLUSTER_SIZE`, `TASK1_MAX_CLUSTER_SHARE`),
  `scripts/validate_pattern_offline.py` (add `--ksweep`), `tests/test_cluster.py` (new tests).
- **Do NOT touch:** `src/intraday_trajectory.py`, the DTW path (`--method dtw-precomputed`),
  trajectory enrichment, `src/rules.py`, `src/label.py`, `src/features.py`,
  `tests/fixtures/validation_labels.csv`, intent/capital config thresholds, `YOUZI_WIN_MARGIN` / guard.
- **Deps:** sklearn (`KMeans`, `silhouette_score`, `calinski_harabasz_score`) + numpy — all present.
- **Legacy reproducibility:** `_sweep_k` and the default `ksweep="legacy"` path stay byte-identical
  until (and unless) §5 passes and production wiring is a deliberate, separately-committed change.

## 7. Deferred (NOT this slice)

Wiring the constrained sweep into `main.py` (gated on §5) · alternative balance objectives
(entropy of `cluster_sizes`, Gini) · relaxing `MAX_CLUSTER_SHARE` per panel size · GBDT head ·
label CSV expansion · batch-cancel perf.

---

## 8. Results (2026-07-02) — HYPOTHESIS FALSIFIED (by construction) · constraint is a NO-OP

`validate_pattern_offline.py --input parquet:data/202606 --all-dates --ksweep constrained`
(universe `samples/stock-samples.xlsx`, exit 0). The constrained run reports the legacy
argmax-silhouette on the SAME daily matrix in the `sil_daily` column, so constrained-vs-legacy is a
single-pass comparison. `wass_sep`/`dtw_sep` are 0 (constrained is daily-only Euclidean, no DTW build).

| date | panel_n | K (both) | sil (constr) | sil_daily (legacy) | audit D1.b | CH | feas_K | cluster_sizes | binds? |
|------|--------:|---------:|-------------:|-------------------:|-----------:|-----:|-------:|---------------|:------:|
| 20260616 | 100 | 6 | 0.1670 | 0.1670 | 0.1685 | 17.9 | 7 | [12,14,15,16,18,25] | no |
| 20260617 | 99 | 8 | 0.1390 | 0.1390 | 0.1445 | 13.7 | 7 | [5,6,11,15,15,15,16,16] | no |
| 20260618 | 99 | 6 | 0.1303 | 0.1303 | 0.1355 | 15.4 | 7 | [13,14,15,16,16,25] | no |
| 20260622 | 99 | 9 | 0.1403 | 0.1403 | 0.1596 | 12.3 | 7 | [6,6,7,8,10,14,15,16,17] | no |
| 20260623 | 99 | 9 | 0.1445 | 0.1445 | 0.1426 | 12.6 | 7 | [5,9,9,10,11,12,12,14,17] | no |
| 20260624 | 99 | 10 | 0.1505 | 0.1505 | 0.1564 | 12.6 | 7 | [5,6,8,8,8,8,12,13,15,16] | no |
| 20260625 | 100 | 6 | 0.1548 | 0.1548 | 0.1583 | 15.3 | 7 | [8,8,14,17,22,31] | no |
| 20260626 | 100 | 6 | 0.1453 | 0.1453 | 0.1509 | 16.4 | 7 | [12,13,16,16,18,25] | no |
| 20260629 | 100 | 8 | 0.1427 | 0.1427 | 0.1437 | 14.0 | 7 | [9,10,11,11,13,14,15,17] | no |
| **median** | ~100 | — | **0.1445** | **0.1445** | **0.1509** | **14.0** | **7** | — | **never** |

**The constraint never binds.** On every one of the 9 days: `sil == sil_daily` to 4 decimals (the
constrained sweep selects the *identical* K as legacy), **all 7 candidate K in `K_RANGE (6,12)` are
feasible** (`feas_K = 7`), and every partition is balanced — smallest cluster 5–13 members (never a
singleton), largest cluster 25–31% of the panel (`max_share` 0.25–0.31, nowhere near the 0.60 cap).
The `TASK1_MIN_CLUSTER_SIZE=2` / `TASK1_MAX_CLUSTER_SHARE=0.60` rails are a pure no-op on this corpus.

**Falsification (§4) — three triggers fire, exactly as §2.2 predicted by construction:**
- median silhouette **0.1445 ≤ 0.1509** (audit D1.b). *Because constrained ≡ legacy here, this is just
  the current legacy median; it sits below the frozen audit table because the audit was measured on a
  **larger panel** (n=109–116 vs n=99–100 now — a corpus/pipeline evolution, NOT introduced by this
  slice).*
- median CH **14.0 < 16.4** (same panel-size drift).
- days silhouette strictly > audit D1.b: **1/9 < 5/9** (only 20260623, the one upward-drift day).
- The **no-feasible-K** safety falsifier did **NOT** trip (7/7 feasible every day) — the rail is never
  so aggressive it would force `K=1`. Good: were it ever wired on, it would not regress the inference
  path.

**Diagnostic conclusion (the real deliverable — §2.2).** The production Euclidean Task-1 partition is
**not degenerate**: every K in the range yields balanced clusters, so the Slice-4 DTW pathology
(one 50–91% giant cluster + singletons, `best_K` pinned at the floor) has **no Euclidean analogue** on
this corpus. The balance constraint cannot lift silhouette (it is argmax over a subset — §2.2) and here
does not even *change* the selection. Per §4 this is a clean **rejection**: the constrained sweep is
**NOT** wired into production `cluster_patterns`; production is byte-identical.

**Durable value (if kept — human decision at gate).** The `--ksweep constrained` harness path + the
`_sweep_k_constrained` function now provide a **degeneracy audit** for the Euclidean K-sweep: `feas_K`,
`cluster_sizes`, and `rejected_reason` make it visible, on any future corpus, whether the production
clusterer has started selecting imbalanced partitions (at which point the rail would begin to bind and
this measurement would flag it). It is a reusable safety diagnostic, not a scoring mechanism.

**What did NOT change (verified).** `_sweep_k` (legacy) and `cluster_patterns` (production submit path)
are untouched; `score_day` defaults `ksweep="legacy"` (byte-identical); no Task-2 code
(`rules.py`/`label.py`/`features.py`/`model.py`/intent+capital thresholds) touched → Task-2 gates
cannot drift (capital 0.6438 / intention 0.6750 / floors). Full suite **220 passed, 2 xfailed**.

**Recommendation (needs human go — §3.3/H5 discipline, do NOT auto-iterate).** Two Task-1 mechanisms
were already falsified (Slice-1 enrichment, Slice-4 DTW); this slice adds a third negative and, more
usefully, **rules out degeneracy as the Euclidean silhouette's problem** — the ~0.14–0.15 tier is what
balanced Euclidean KMeans genuinely scores on this ~100-stock daily matrix, not a degeneracy artifact
waiting to be constrained away. The audit-D1 lever (Task-1 = 0.4 of board) is still not *refuted*, but
raising silhouette now requires a **different feature/metric space**, not a better K-selection rule on
the existing one. Reported as the honest negative; harness + tests kept default-off.

### VERIFY
- `pytest -q` → **220 passed, 2 xfailed** (9 new Slice-6 tests; target ≥212/2 met).
- `--ksweep constrained --all-dates` → table above; legacy path (`--ksweep legacy` default) numbers
  are the `sil_daily` column (byte-identical selection).
- Task-2: no code in the Task-2 path touched; production `cluster_patterns` byte-identical → gates
  unaffected by construction (not re-run; capital-gate spot-check available on request).
