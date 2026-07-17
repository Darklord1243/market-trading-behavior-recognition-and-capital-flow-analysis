# Sonnet execution prompt — P5.7: Task-1 trajectory-space clustering (DTW complete-linkage)

> **Dispatched by:** Opus lead orchestrator Batch 6
> **Human approves with:** `"proceed to dispatch P5.7"`
> **Hypothesis doc:** `docs/hypotheses/competitive-gap-audit-20260703-fable5.md` §6
> **Parent slices:** Slice 4 FALSIFIED (average linkage); Slice 6 FALSIFIED (Euclidean K-sweep)

---

# Role

You are a **Sonnet-class execution agent** on AFAC2026 Track 1. Implement **P5.7 only** — wire a
config-gated **DTW complete-linkage** production path for Task-1 clustering.

> *Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do not commit.*

**Read (minimal):**
1. `docs/hypotheses/competitive-gap-audit-20260703-fable5.md` §2.1, §6
2. This prompt
3. `src/cluster.py` (primary edit), `config.py`, `main.py`, `src/pipeline_parquet.py`, `tests/test_cluster.py`
4. `src/intraday_trajectory.py` — **trajectory builders live here** (`build_trajectory`, `build_trajectories`, `summary_features`)
5. Reference (do not import from scripts): `scripts/validate_pattern_offline.py` — trajectory build + scoring pattern

**Out of scope:**
- `src/rules.py`, `src/features.py`, `src/label.py`, `src/model.py`
- `tests/fixtures/validation_labels.csv`
- Task-2 threshold / intent band changes
- GBDT, Euclidean K-sweep tweaks, label expansion
- Docs/LIS edits (flag contradictions in report only)

**Do not commit.** Opus gates and commits.

---

# Organizer clarification (binding for this slice)

Task-1 **compactness** = within same clustering label; **separation** = across different labels. Both
computed on **your clustering output**. This validates clustering directly in trajectory/distribution
space — not Euclidean feature-space KMeans as a proxy.

---

# Naming convention (verified by Opus — obey exactly)

The existing `--method` CLI choices are **hyphenated**: `euclidean`, `dtw-precomputed`. The new method
must follow the same convention. Use the **single string `dtw-complete`** everywhere — CLI choice, the
config `TASK1_METHOD` value, and any internal branch comparison. Do **not** introduce an underscore
variant (`dtw_complete`) — one canonical string only.

---

# What to build

## Goal
Replace production Task-1 clustering (when `TASK1_METHOD == "dtw-complete"`) with:

1. Build `(n, 30, 3)` intraday trajectories via existing `build_trajectories` / `build_trajectory`
   (from `src/intraday_trajectory.py`)
2. Precompute pairwise DTW matrix `_dtw_distance_matrix(traj_arr)` (reuse existing `_dtw_distance`)
3. **Complete-linkage** agglomerative clustering on `D`, K-sweep **K ∈ {2,…,8}** (new constant
   `TASK1_DTW_K_RANGE = (2, 8)` — NOT legacy `K_RANGE = (6, 12)`)
4. Select K = argmax **DTW-space silhouette** subject to:
   - After **singleton-merge-to-nearest-cluster**: min cluster size ≥ `TASK1_MIN_CLUSTER_SIZE` (2)
   - Max cluster share ≤ `TASK1_MAX_CLUSTER_SHARE` (0.60 in config; audit allows up to 0.65 — use the
     config constant, and document in your report if you need to raise it to 0.65 for acceptance)
   - K ≥ 3 after merge
5. **Trajectory-shape naming** from per-cluster `summary_features` centroids (not one dominant
   microstructure feature → kills the 55–64% `机构长线配置` fallback)
6. Wire trajectories into `run_parquet` / `cluster_patterns` on the parquet path only

**Legacy path:** `TASK1_METHOD == "euclidean"` (default) → **byte-identical** to current production.

## Files (expected touch set)
| Action | Path |
|--------|------|
| Edit | `config.py` — add `TASK1_METHOD = "euclidean"` (default), `TASK1_DTW_K_RANGE = (2, 8)` |
| Edit | `src/cluster.py` — `_dtw_complete_sweep`, `_merge_singletons`, `_traj_centroid_to_name`, extend `cluster_patterns` |
| Edit | `main.py` — in `run_parquet`: one batched snapshot read → `build_trajectories` → pass to `cluster_patterns` when method is `dtw-complete` |
| Edit | `scripts/validate_pattern_offline.py` — add `"dtw-complete"` to `--method` choices, wire through existing seam for acceptance measurement |
| Edit | `tests/test_cluster.py` — unit tests for complete-linkage sweep, singleton merge, naming diversity |

**Reuse (do not rewrite):** `_dtw_distance`, `_dtw_distance_matrix`, `_stack_trajectories`,
`_traj_summary_frame`, `summary_features`, `TASK1_MIN_CLUSTER_SIZE`, `TASK1_MAX_CLUSTER_SHARE`,
`_sweep_k_constrained` degeneracy patterns from Slice 6.

**Different from Slice 4 `_dtw_precomputed_sweep`:** linkage=`'complete'` (not `'average'`), K range
2–8, degeneracy constraints in selection, scores **production label path**, trajectory naming.

## Fallback (only if complete-linkage fails acceptance)
Hand-rolled **PAM/k-medoids** on precomputed `D` (~60 lines, seed-fixed with `RANDOM_SEED=42`, no new
deps). Try only if complete-linkage cannot hit +0.15 on ≥9/11 days. If both fail → do **not** flip the
default; report falsification.

---

# TDD workflow
1. **Red:** test `_merge_singletons` — singleton relabeled to nearest cluster; min size ≥ 2
2. **Green:** implement merge helper
3. **Red:** test `_dtw_complete_sweep` on a synthetic 3-cluster DTW-separated toy (small n)
4. **Green:** implement sweep with complete linkage + constraints
5. **Red:** test trajectory naming yields ≥3 distinct `pattern_type` on a fixture with 3 shape modes
6. **Green:** implement `_traj_centroid_to_name` lexicon, e.g.:
   - 全天单边拉升 / 冲高回落出货 / 尾盘集中放量 / 横盘均衡震荡
   - Quantitative explanation: cluster mean vs market mean on `SUMMARY_COLS`
7. **Red:** test `cluster_patterns(..., method via config)` respects `TASK1_METHOD`
8. **Green:** wire `cluster_patterns` + `run_parquet` trajectory threading (mirror
   `validate_pattern_offline` snapshot read — ONE extra batched read, no per-stock cancel loop repeat)
9. **Full suite:** `conda run -n base pytest tests/ -q`

---

# Acceptance (pre-registered — Opus re-runs; you report)

Run on **all 11 parquet days** (0616–0702):
```bash
# June corpus (9 days)
PYTHONIOENCODING=utf-8 python scripts/validate_pattern_offline.py \
  --input parquet:data/202606 --all-dates --method dtw-complete

# July days (0701, 0702) if in data/202607
PYTHONIOENCODING=utf-8 python scripts/validate_pattern_offline.py \
  --input parquet:data/202607 --date 20260701 --method dtw-complete
PYTHONIOENCODING=utf-8 python scripts/validate_pattern_offline.py \
  --input parquet:data/202607 --date 20260702 --method dtw-complete
```

**Must pass:**
- DTW-sil ≥ +0.15 every day (baseline production: −0.1248 on 0625, −0.1625 on 0629)
- No singletons; max share ≤ config limit; K ≥ 3
- ≥3 distinct `pattern_type`/day; top pattern ≤ 65%
- Euclidean sil reported per day (drop expected — state explicitly)

**Task-2 regression (Opus runs, you must not perturb):**
```bash
PYTHONIOENCODING=utf-8 python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
PYTHONIOENCODING=utf-8 python scripts/validate_intent_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```
capital **0.6438/n=122**, intention **0.6750/n=115** byte-identical.

**Single-day runtime:** time `main.py` on 20260629 (~100 stocks) with `TASK1_METHOD=dtw-complete`;
target ≤7 min Task-1 portion.

**pytest** `tests/ -q` green (222+ passed, 2 xfailed).

**Production smoke after wiring:**
```bash
PYTHONIOENCODING=utf-8 python main.py \
  --input parquet:data/202606 --universe samples/stock-samples.xlsx \
  --date 20260629 -o outputs/p57_smoke_0629 --pack submit.zip
```
(Temp dir — delete before report; Opus re-runs.)

---

# Hard rules
- Intraday-only — trajectories from same-day snapshots
- No label file reads in the clustering path
- `RANDOM_SEED = 42` where applicable (k-medoids fallback)
- Do not remove or break the `TASK1_METHOD == "euclidean"` default path
- Do not pip-install new packages (`sklearn_extra` forbidden)

---

# When done, report
- Commands + pass/fail output
- Files changed (list)
- Per-day table: `date | K | cluster_sizes | dtw_sil | euclid_sil | n_pattern_types | top_pattern_share`
- Acceptance checklist (all boxes)
- Runtime measurement (0629)
- Proxy-F1: "unchanged expected — Opus to verify"
- Falsification status: **SHIP** or **DO NOT SHIP**
- Contradictions with LIS (if none, say so)

Begin with the first failing test.
