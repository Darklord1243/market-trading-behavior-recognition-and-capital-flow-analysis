# Sonnet execution prompt — Phase 5b (P5.1b): relative cluster naming (LIS v1.6.7)

> **You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do NOT commit.**
> The Opus lead inspects, double-verifies, gates, re-runs production, regenerates submit.zip, and commits.

---

# Context — the bug (found on the real 99-stock 20260623 matrix)

After P5.1a fixed the `n_ticks` leak, the production run STILL produced **1 distinct `pattern_type`**
(all 99 → fallback `机构长线配置`), even though clustering found **K=9** clusters.

Root cause: `_centroid_to_name` matches **absolute** rank thresholds (e.g. `mega_amount_pct ≥ 0.60` AND
`active_buy_pct ≥ 0.60` AND `time_concentration ≥ 0.60`). But a cluster centroid is the **mean of
rank-normalized values**, which regresses toward **~0.5** — so no multi-feature AND rule ever clears 0.60.
Every cluster falls to the fallback → 1 label → Task-1 regression vs the prior stub's 2 labels.

The fix is a **naming-strategy change** (this slice). Clustering itself (the K-sweep, the EXCLUDE drop) is
correct and stays untouched.

---

# Role / scope

Implement **LIS Phase 5b (P5.1b) only** — **relative** cluster naming so labels are assigned by which
feature each cluster is most extreme on *versus the global average*, guaranteeing label diversity.

**Read (minimal):** this file; `src/cluster.py` (edit — focus on `_centroid_to_name` and the naming loop in `cluster_patterns`).

**Touch ONLY:** `src/cluster.py` and `tests/test_cluster.py`. No other file. **No new deps.**

**Do not change** `_sweep_k`, the EXCLUDE drop, the rank-normalization, the K=1 path, or the output contract.
**Do not edit** `docs/LIS.md` — flag contradictions in your report.

---

# The fix — approach (a), relative dominance (decided by the lead)

In `cluster_patterns`, after computing `clustering_feats` (already EXCLUDE-dropped, rank-normalized):

1. Compute the **global mean vector** over all rows: `global_mean = clustering_feats.mean(axis=0)`.
2. For each cluster, compute its centroid mean (as today) **and** the **delta** `delta = centroid_mean - global_mean`
   (per clustering column). The cluster's **dominant feature** is `argmax(delta)` — the feature on which this
   cluster sits furthest *above* the day's average. (Optionally also track `argmin(delta)` as the most-*below*
   axis for "weak-X" patterns.)
3. Map the dominant feature to a finance-grounded open-vocab Chinese `(pattern_type, explanation)` via a
   **single-feature lexicon** (substring match on the feature name). The explanation must reference the actual
   dominant feature and its above-average direction; ≤ 200 chars; no `n_ticks`/EXCLUDE columns (already dropped).
4. **Guarantee ≥ 2 distinct `pattern_type` whenever K ≥ 2.** `argmax(delta)` usually diversifies on its own,
   but two clusters could share a top axis. Add a **deterministic** tie-break: if the assigned set has < 2
   distinct labels while K ≥ 2, reassign the cluster with the largest **secondary** |delta| to its secondary-axis
   label, repeating until ≥ 2 distinct (or axes exhausted). No randomness; seed-independent.
5. **K = 1 / n ≤ 1:** keep a single sensible label (fallback is fine — the ≥2 guarantee applies only for K ≥ 2,
   since with one cluster `centroid == global_mean`).

**Lexicon coverage** — map by feature *family* (substring), covering the real feature vocabulary seen on the
corpus. Suggested (refine the Chinese phrasing as you see fit, keep it finance-grounded and open-vocab):

| dominant feature substring | pattern_type (example) |
|---|---|
| `mega_amount` / `mega_count` | 游资强势拉升 |
| `large_amount` / `active_net_direction` / `book_imbalance` | 主力资金吸筹建仓 |
| `small_amount` / `small_count` + `burst` | 量化高频T0套利 |
| `active_buy` | 买盘主动占优 |
| `active_sell` | 卖压主动出货 |
| `*cancel*` (cb_buy_cancel / cb_sell_cancel) | 盘口撤单博弈 |
| `big_quote_share` | 盘口诱多挂单 |
| `time_concentration` | 尾盘/开盘成交集中 |
| `burst_ratio` (alone) | 高频脉冲交易 |
| (no mapped match) | 机构长线配置 (fallback) |

Prefer keeping the existing `FALLBACK_*` constants and reusing the existing phrase strings where they fit;
this is a re-wiring of *how* a name is chosen (relative argmax), not a rewrite of the vocabulary.

---

# TDD workflow (failing tests first)

Add to `tests/test_cluster.py`:

1. **`test_relative_naming_yields_multiple_labels`** — build a matrix with **≥3** clusters, each made extreme
   on a **different** feature (so each cluster's `argmax(delta)` is a different family). Call
   `cluster_patterns(df, k_range=(3,5))`. Assert **distinct `pattern_type` ≥ 3** (or == number of distinct
   planted dominant families). This FAILS on the old absolute-threshold naming (centroids near 0.5 → all
   fallback) and passes with relative naming. Note before/after in your report.
2. **`test_naming_guarantees_two_labels_when_k_ge_2`** — construct a case where two clusters share the same
   top axis but differ on a second axis; assert distinct `pattern_type` ≥ 2 (exercises the tie-break guarantee).
3. Keep the existing P5.1/P5.1a tests green — especially `test_raw_scale_n_ticks_does_not_drive_clustering_or_naming`
   (≥2 labels, no `n_ticks` in explanations) and `test_every_row_gets_explanation` (≤200 chars).

**Run:**
```bash
conda run -n base --no-capture-output pytest tests/test_cluster.py -q
conda run -n base --no-capture-output pytest tests/ -q
```
Expect: your 2 new tests green, all prior green — full suite **163 passed, 2 xfailed** (161 + 2 new).

> Do **not** run `main.py`/parquet — the Opus lead re-runs production 20260623 (expects distinct `pattern_type`
> ≥ 2, ideally several at K=9; no `n_ticks` in explanations; predict_result.csv byte-identical) and regenerates submit.zip.

---

# Acceptance (tick each)

- [ ] Naming chosen by **relative** dominance: `argmax(centroid − global_mean)` over clustering columns, mapped via single-feature lexicon.
- [ ] **≥ 2 distinct `pattern_type` guaranteed when K ≥ 2** (deterministic tie-break), proven by a test.
- [ ] New multi-label test ≥ 3 distinct labels on a ≥3-cluster synthetic matrix (fails on old absolute naming).
- [ ] Existing tests green; K=1 path + output contract + EXCLUDE drop + `_sweep_k` unchanged.
- [ ] Full suite green; only `src/cluster.py` + `tests/test_cluster.py` changed; no new deps.
- [ ] **Proxy-F1: N/A** — no scorer touched (`rules/features/label/normalize` untouched); clustering output feeds only `pattern_type`. Do not run the gate.

---

# When done, report

1. Commands + pass/fail counts; the new multi-label test's pre-change failure vs post-change pass.
2. Files changed (exactly the two).
3. Acceptance checklist ticked.
4. Confirm `rules/features/label/normalize` untouched; `_sweep_k`/EXCLUDE-drop/K=1 path unchanged.
5. Any LIS contradiction (else none).
6. **Next hint:** Opus re-runs production 20260623 → expects distinct `pattern_type` ≥ 2 (several at K=9), no n_ticks in explanations, predict_result byte-identical, then regenerates submit.zip.

**Do NOT commit.** Begin with the failing multi-label test.
