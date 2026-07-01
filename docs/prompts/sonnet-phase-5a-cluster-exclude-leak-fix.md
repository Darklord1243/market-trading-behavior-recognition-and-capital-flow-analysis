# Sonnet execution prompt — Phase 5a (P5.1a): fix EXCLUDE-column leak in clustering (LIS v1.6.7)

> **You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do NOT commit.**
> The Opus lead inspects, double-verifies, gates, regenerates the submit, and commits. Report when done.

---

# Context — the bug (found on the real 99-stock 20260623 matrix)

P5.1 (commit `d24fd66`) made `cluster_patterns` run KMeans on `normalize_matrix(feats)`. But
`src/normalize.py` defines `EXCLUDE = {cb_available, n_ticks, limit_seal_up_ratio, limit_seal_down_ratio}`
and **passes those columns through at RAW scale** (not normalized to [0,1]). So:

- `n_ticks` (~thousands) **dominates the Euclidean KMeans distance** → clusters become an n_ticks histogram, not microstructure patterns.
- The centroid naming's `max(centroid.items())` argmax is always `n_ticks` (every explanation said "实际主导: n ticks").
- The naming lexicon (thresholds on [0,1] microstructure features) never fires → **all 99 rows collapse to the fallback `机构长线配置`** (distinct `pattern_type` = 1, a regression vs the prior stub's 2).

The synthetic P5.1 tests missed this because they had **no EXCLUDE columns**.

---

# Role / scope

Implement **LIS Phase 5a (P5.1a) only** — exclude the `normalize.EXCLUDE` columns from the clustering
feature matrix **and** from centroid naming, so they drive neither distance nor labels.

**Read (minimal):** this file; `src/cluster.py` (edit); `src/normalize.py` (read `EXCLUDE` — do not edit).

**Touch ONLY:** `src/cluster.py` and `tests/test_cluster.py`. No other file. **No new deps.**

**Do not edit `docs/LIS.md`** — flag contradictions in your report.

---

# The fix (minimal)

In `src/cluster.py`, `cluster_patterns`:

1. Import the actual set: `from src.normalize import normalize_matrix, EXCLUDE` (use the imported `EXCLUDE` frozenset — do **not** hard-code the column names, so it stays in sync if `normalize.EXCLUDE` changes).
2. After `normed = normalize_matrix(feats)`, **drop the EXCLUDE columns** from the frame used for both clustering and naming, e.g. `clustering_feats = normed.drop(columns=[c for c in EXCLUDE if c in normed.columns])` then `X = clustering_feats.select_dtypes("number").fillna(0.0).values` and build `col_names`/centroid dicts from `clustering_feats` (so the naming argmax and lexicon never see `n_ticks`/`cb_available`/`limit_*`).
3. Everything else stays: rank-normalized [0,1] microstructure features → `_sweep_k` (silhouette, CH tie-break) → KMeans → centroid-driven naming → K=1 graceful path → unchanged output contract (`pattern_type`, `pattern_explanation`, same index).

Keep the diff surgical. Do not change `_sweep_k`, the lexicon, or thresholds unless strictly required to make the EXCLUDE columns stop leaking. (If the lexicon genuinely needs a threshold nudge to fire on real centroids, prefer leaving it — the acceptance test below uses a synthetic matrix you control; the production re-run is the Opus lead's job.)

---

# TDD workflow (one failing test first)

Add to `tests/test_cluster.py` a **regression test that fails without the fix**:

**`test_raw_scale_n_ticks_does_not_drive_clustering_or_naming`**
- Build a synthetic matrix with real microstructure feature columns forming **≥2 clearly distinct groups** (e.g. one group high `oss_mega_amount_pct`/`ap_active_buy_pct`, another high `oss_small_amount_pct`/`rs_burst_ratio`), **plus a raw-scale `n_ticks` column** with large values (e.g. `rng.integers(1000, 50000)`) that is **uncorrelated with the true groups** (or even anti-correlated, to actively sabotage).
- Call `cluster_patterns(df, k_range=(2,4))`.
- Assert **distinct `pattern_type` ≥ 2** (i.e. naming did not collapse to the single fallback).
- Assert no `pattern_explanation` contains the substring `n_ticks` / `n ticks` (the EXCLUDE column must not appear as a dominant feature in any label).
- Confirm this test **FAILS on the current code** (n_ticks dominates → 1 label) before your fix, then passes after. Note the before/after in your report.

Keep the existing 6 P5.1 tests green (they have no EXCLUDE columns, so they should be unaffected).

**Run:**
```bash
conda run -n base --no-capture-output pytest tests/test_cluster.py -q
conda run -n base --no-capture-output pytest tests/ -q
```
Expect: your new test green, all prior green — full suite **161 passed, 2 xfailed** (160 + 1 new).

> Do **not** run `main.py`/parquet — the Opus lead re-runs the production 20260623 matrix to verify distinct `pattern_type` ≥ 2 and regenerates `submit.zip`.

---

# Acceptance (tick each in your report)

- [ ] `cluster_patterns` drops `normalize.EXCLUDE` columns (imported, not hard-coded) before KMeans **and** before centroid naming.
- [ ] New regression test fails pre-fix (n_ticks collapses naming to 1 label) and passes post-fix (≥2 labels; no `n_ticks` in any explanation).
- [ ] All 6 prior P5.1 cluster tests still green; K=1 path + output contract unchanged.
- [ ] Full suite green; only `src/cluster.py` + `tests/test_cluster.py` changed; no new deps.
- [ ] **Proxy-F1: N/A** — no scorer touched (`rules/features/label/normalize` untouched); clustering output feeds only `pattern_type`. State this; do not run the gate.

---

# When done, report

1. Commands + pass/fail counts (paste tails); the **pre-fix failure** vs **post-fix pass** of the new regression test.
2. Files changed (must be exactly the two).
3. Acceptance checklist ticked.
4. Confirm `rules/features/label/normalize` untouched.
5. Any LIS contradiction (else say none).
6. **Next hint:** Opus re-runs production 20260623 → expects distinct `pattern_type` ≥ 2, predict_result.csv byte-identical, then regenerates submit.zip.

**Do NOT commit.** Begin with the failing regression test.
