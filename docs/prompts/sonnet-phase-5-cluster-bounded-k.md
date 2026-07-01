# Sonnet execution prompt — Phase 5 (P5.1): metric-aligned Task-1 clustering (LIS v1.6.7)

> **You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do NOT commit.**
> The Opus lead inspects, double-verifies, gates, and commits. Report when done; do not `git commit`.

---

# Role

You are an execution agent on AFAC2026 Track 1. Implement **LIS Phase 5 (P5.1) only** — real bounded-K
selection + centroid-driven interpretable naming for Task-1 trading-pattern clustering.

**Read (minimal):**
1. `docs/LIS.md` — **§6 Phase 5** (lines ~807-820) and **§5 H5** (the clustering hypothesis); plus **§2–§3** if you have not seen them this session.
2. This prompt file.
3. `src/cluster.py` (the file you edit) and `src/normalize.py` (the H1 seam you will reuse — read its `normalize_matrix` signature; do not edit it).

Do **not** re-read the whole doc tree.

**Out of scope this session:** `rules.py`, `features.py`, `label.py`, `normalize.py`, `aggregate.py`, `model.py`, `main.py`, `config.py`, `validate.py`, any scorer. **No new dependencies.**

**Do not edit `docs/LIS.md`** — if you hit a factual contradiction, flag it in your report with a proposed changelog line.

---

# Hard rules (auto-DQ if broken)

1. **No new dependencies.** `tslearn` is **NOT installed** and the LIS Phase-5 audit note forbids importing a clustering lib that pulls network at runtime. Use **only** what is already available: `sklearn` (KMeans, `sklearn.mixture.GaussianMixture`, `sklearn.metrics.silhouette_score` / `calinski_harabasz_score`), `numpy`, `pandas`. **Do not** `pip`/`conda install` anything. Document the DTW/TimeSeriesKMeans decision as deferred (see Task 5), do not implement it.
2. **Reproducible** — use `config.RANDOM_SEED` (42) for every estimator; no `random`/`np.random` without seeding; no LLM in the path.
3. **No answer-feedback** — never read `outputs/` or leaderboard answers. The K choice is made on **internal** metrics (silhouette, tie-break CH) only.
4. **Open-vocab naming** — `pattern_type` is open vocabulary (FAQ), finance-grounded Chinese labels; `pattern_explanation` ≤ 200 chars; every row gets a non-empty, defensible explanation.
5. **Scope** — touch **only** `src/cluster.py` and `tests/test_cluster.py`.

---

# What to build (LIS §6 Phase 5)

Replace the stub `_choose_k` (fixed `DEFAULT_K` clamp) and the fixed-predicate naming with:

### Task 1 — bounded-K sweep on the **normalized** matrix
- Rank-normalize the numeric feature matrix with `from src.normalize import normalize_matrix` **before** clustering (H1 dependency — replaces the in-file `StandardScaler`; values become cross-sectional ranks in [0,1], comparable across stocks).
- Sweep `k` over a range (default = `config.K_RANGE` = `(6, 12)` inclusive), fit KMeans (`random_state=RANDOM_SEED`, `n_init=10`) at each feasible `k`, score by **silhouette** (tie-break **Calinski-Harabasz**), pick the best `k`.
- **Testability requirement:** the sweep must accept an **optional `k_range` parameter** (default `K_RANGE`) so a test can plant a known K inside a custom range. Keep the public `cluster_patterns(matrix)` signature unchanged for `main.py`; add the parameter to the internal sweep helper (and optionally expose it as a keyword on `cluster_patterns` with a default).
- `k` is clamped to `[1, n_samples]`; silhouette is undefined for `k<2` or `k>=n` — skip those and fall through to the K=1 path.

### Task 2 — centroid-driven naming (not fixed predicates)
- Name each cluster from its **actual centroid** (mean of member rows in normalized space): identify the centroid's dominant (and notably weak) feature axes and map them to a finance-grounded open-vocabulary Chinese `(pattern_type, explanation)`. You may keep the existing 4 phrases as a seed lexicon, but the **selection must be driven by which features actually dominate the centroid**, not by rigid AND-predicates that mostly fall through to the default.
- Naming must be a **pure function of the centroid vector** (deterministic, testable).

### Task 3 — graceful K=1 path
- Preserve the current behavior for `n <= 1` (and when no `k>=2` is feasible): single cluster, neutral/fallback label, no crash, no silhouette call on degenerate input.

### Task 4 — keep output contract
- Return a DataFrame indexed like `matrix` with columns `pattern_type`, `pattern_explanation` (unchanged contract; `main.py` calls `cluster.cluster_patterns(matrix)`).

### Task 5 — document the metric-alignment decision (comment/docstring only)
- One short docstring/comment block: DTW (`tslearn.TimeSeriesKMeans`) and HDBSCAN evaluation are **deferred** because no offline-installed, network-free implementation is available in `base`; sweep uses silhouette/CH-selected KMeans on the rank-normalized matrix as the metric-aligned proxy. No code for DTW.

---

# TDD workflow (one failing test → fail → minimal impl → pass)

Create `tests/test_cluster.py`. Tests must be **discriminating** (a stub that always returns K=1 or always the default name must FAIL them). Suggested cases — build synthetic matrices with `numpy` (seeded), columns named like real features so naming has something to read:

1. **`test_ksweep_recovers_planted_k`** — build a matrix with a **planted K** of well-separated blobs inside a custom `k_range` (e.g. plant 4 blobs, pass `k_range=(2,6)`); assert the sweep selects K==4. (Fails for fixed-K stub.)
2. **`test_selected_k_beats_fixed_k8_silhouette`** — on a synthetic multi-cluster matrix, silhouette at the **selected** K > silhouette at fixed **K=8**. (Proves the sweep adds value.)
3. **`test_naming_is_centroid_driven`** — two clusters with clearly different dominant features get **different** `pattern_type` labels (not both the fallback). (Fails for fixed-default.)
4. **`test_every_row_gets_explanation`** — no null/empty `pattern_explanation`; each ≤ 200 chars; index matches input.
5. **`test_k1_graceful_on_single_row`** — `n==1` matrix → one row, K=1 path, no exception, non-empty label.
6. **`test_default_range_is_config_k_range`** — with no `k_range` passed, the sweep uses `config.K_RANGE`.

**Final checks before done (paste the output counts):**
```bash
conda run -n base --no-capture-output pytest tests/test_cluster.py -q
conda run -n base --no-capture-output pytest tests/ -q
```
Expect your new tests green and the full suite **154 + your new tests passed, 2 xfailed**.

> Do **not** run `main.py` on parquet (tens of minutes) — the synthetic matrix tests ARE the binding acceptance (LIS Phase-5 acceptance is "on a synthetic multi-cluster matrix"). The Opus lead will verify the 99-stock matrix separately.

---

# Acceptance criteria (check each in your report)

- [ ] K-sweep selects the planted K on a synthetic matrix (within a passed `k_range`).
- [ ] Selected-K silhouette **beats** fixed-K=8 silhouette on the synthetic multi-cluster matrix.
- [ ] Naming is driven by the **actual centroid**; distinct-shaped clusters get distinct labels.
- [ ] Every row gets a non-empty `pattern_explanation` ≤ 200 chars; output contract unchanged.
- [ ] K=1 graceful path preserved for `n<=1` / no feasible `k>=2`.
- [ ] Clustering runs on the **rank-normalized** matrix (`normalize_matrix`).
- [ ] Full suite green; **only** `src/cluster.py` + `tests/test_cluster.py` changed; **no new deps**.

**Proxy-F1:** **N/A** — this slice touches no scorer (`rules/features/label/normalize` untouched). Clustering output feeds only the `pattern_type` column, never `capital_type`/`capital_intention`. State this explicitly; do **not** run the offline gate.

---

# Style

- `from __future__ import annotations`, type hints, minimal diff, match `src/cluster.py` conventions.
- Test-first; deterministic (seed everything).
- Delete any throwaway debug scripts before finishing.

---

# When done, report

1. Commands run + pass/fail counts (paste `pytest` tails).
2. Files created/changed (must be exactly the two in scope).
3. Acceptance checklist (above) — tick each.
4. The **selected K** and **silhouette: fixed-K=8 → selected-K** on your synthetic matrix.
5. Anything that contradicted LIS (if none, say so).
6. **Proxy-F1:** N/A (no scorer touched) — confirm `rules/features/label/normalize` untouched.
7. **Next hint:** what a follow-up (e.g. real 99-stock silhouette delta, DTW eval if a lib is ever vendored) would cover.

**Do NOT commit.** Begin with the first failing test.
