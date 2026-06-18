# Build Notes — Pipeline Scaffold (Step B)

> ⚠️ **SUPERSEDED for current state — see `docs/LIS.md`.** This file documents the Step-B scaffold era
> (2-class `量化机构`, 24 tests, fixture emitting `量化机构`). The repo is now **3-class `{游资,量化,散户}`**
> (commit `ee2a1d9`), **37 tests**, and the fixture emits `散户`. Treat `docs/LIS.md` + the code as the
> source of truth; this file is kept for build history only.

**Branch:** `feat/pipeline-scaffold`
**Date:** 2026-06-13
**Goal of this step:** a running, audit-compliant skeleton that ingests the official
fixture and emits two correctly-formatted CSVs. Real model training and full
bounded-K clustering are intentionally deferred.

**Precondition check:** `docs/verification_report.md` VERDICT = *"Sound to build from
after a small set of amendments (N=4)"*; commit `8ac76b7` ("brief Rev. 6 —
verification follow-up fixes N1–N4") confirms the amendments were applied to the
brief. Proceeded to build.

---

## Repo skeleton created (brief §9)

```
config.py            # single source of truth: locked labels, OSS thresholds, K range, seed
main.py              # entry point: --input / -o / --date, relative paths, fixed seed
init_env.sh          # dependency install (relative paths, idempotent)
requirements.txt     # pinned-floor deps
src/
  __init__.py
  ingest.py          # raw-L2 reader (65-col), JSON book parse, cumulative->tick, cancel-table detect
  features.py        # per-(stock,day) feature computation — critical path; CB graceful-degrade
  aggregate.py       # ticks -> (stock,day) feature matrix; hh-window seam
  rules.py           # Stage-1 11-dim capital scorer + intent gate (baseline get_intention)
  label.py           # Stage-2 weak labels + confidence
  model.py           # Stage-3 LightGBM head — STUB (pass-through)
  cluster.py         # Task-1 bounded-K KMeans + pattern naming — STUB-grade
  postprocess.py     # canonical CSV writers + audit-contract validators (fail loudly)
tests/
  conftest.py        # makes repo root importable
  test_config.py     # locked label vocabularies are exact
  test_features.py   # feature math on a deterministic synthetic tick group
  test_postprocess.py# output validator rejects malformed CSVs
  test_smoke.py      # end-to-end on the official fixture
```

## What was ported from the official baseline (baseline-guide.md)

| Baseline behaviour | Where it now lives | Preserved as documented |
|---|---|---|
| `load_and_preprocess()` — `dt`→`transaction_date`, `date`(epoch-ms)→`datetime`, `hh`→Beijing hour, rename `symbol`→`stock_code`, price/volume/amount filter, temporal sort | `src/ingest.py` | ✅ |
| Cumulative→tick `diff().fillna(0).clip(lower=0)` on volume/amount/transactions/bigordervolume | `src/ingest.py` | ✅ |
| OSS share thresholds 50k / 10k / 1k | `config.OSS_THRESHOLDS` → `src/features.py` | ✅ |
| AP aggressor-side inference from `price.diff()` | `src/features.py` | ✅ |
| PI open-30min / close-10min concentration via Beijing `hh`/`minute` | `src/features.py` | ✅ |
| OBP dual-source imbalance (first-snapshot JSON + full-day totals) | `src/features.py` | ✅ |
| 11-dimension weighted capital-type scoring; `游资 if score_yz >= score_qt` | `src/rules.py` | ✅ (behaviour; weights are 1.0 stubs — see below) |
| `get_intention()` gate: buy>0.6 ∧ imb>0.08 → 买入; sell>0.6 ∧ imb<−0.08 → 卖出; else T0交易 | `src/rules.py` | ✅ verbatim thresholds |
| Dual-source imbalance blend 0.4·snapshot + 0.6·full-day | `config` + `src/rules.py` | ✅ |
| KMeans dynamic downgrade `min(k, n_samples)`; ≥3-condition pattern naming | `src/cluster.py` | ✅ (stub-grade) |
| Output label assertions `isin([...])` | `src/postprocess.py` (hardened) | ✅ + extended |

## What is stubbed (deferred per brief — NOT to build yet)

- **`src/model.py` (Stage-3 head):** `CapitalTypeHead.fit/predict` are pass-through;
  predictions == Stage-2 weak labels. The fit/predict signature is the real seam for
  a LightGBM/XGBoost head trained on confidence-weighted weak labels.
- **`src/cluster.py` (bounded-K):** uses `DEFAULT_K=8` clamped into `K_RANGE`, then
  `min(k, n_samples)`. Full K sweep by silhouette/CH over `K_RANGE` is a `TODO`.
  Pattern naming uses 4 of the baseline's candidate names (open vocabulary).
- **`src/rules.py` 11-dim weights:** all dimension weights are 1.0 (equal). The
  dimension set and arg-max behaviour match the baseline; tuned weights come later.
- **CB features:** zero-valued and flagged (`cb_available=0.0`) on snapshot-only data.
  The `has_cancel_table=True` branch in `features._cb_features` is a `TODO` seam for
  the real tick-cancel computation.
- **Holiday calendar:** `main.previous_trading_day` skips weekends; `_KNOWN_HOLIDAYS`
  is an empty stub with a `TODO` to wire an exchange holiday table.
- **`aggregate.compute_window_features`:** per-`hh` window rollup seam, not yet
  consumed (PI features already fold windows into the daily reduce).

## Audit-contract compliance (brief §9)

- ✅ `main.py` recomputes features from raw L2 each run — never reads a pre-computed
  / purchased feature file.
- ✅ Relative paths only; `config.RANDOM_SEED=42` seeded in `numpy` + `random` before
  any modelling.
- ✅ Output writers (`postprocess.py`) assert: exactly 4 cols in fixed order;
  `capital_type ∈ {游资, 量化机构}` and no `散户`/bare-`量化` leak; `capital_intention ∈
  {买入, 卖出, T0交易}`; `transaction_date` equals the expected day; no nulls/blank
  cells; UTF-8-sig encoding. Any breach raises `OutputContractError` (fails loudly).
- ✅ `--date` resolution is dynamic: explicit `--date` > the single date present in the
  data > `None`; the nightly "yesterday" default is computed holiday-aware and logged.
- ✅ No LLM call anywhere in the inference path.
- ⚠️ `submit.zip` "no nested folders" packaging rule (verification O1) is **not** yet
  enforced here — packaging is a later step; noted so it isn't forgotten.

## Smoke-test result

Command:
```bash
bash init_env.sh
python main.py --input samples/AFAC2026.xlsx -o outputs/
```
Produced (both UTF-8-sig, 4-col, all asserts pass):

| File | Row | Values |
|---|---|---|
| `predict_result.csv` | `603997.SH, 20260507` | `capital_type=量化机构`, `capital_intention=T0交易` |
| `pattern_reco.csv` | `603997.SH, 20260507` | `pattern_type=游资强势连板拉升`, with explanation |

- Feature matrix: **1 (stock, day) × 31 features**.
- Clustering degraded to **K=1** on the single sample — **expected** per the baseline
  guide (not a bug; not "fixed").
- CB features degraded to zero with a logged warning — **expected** (snapshot-only).
- `pytest tests/` → **24 passed**.

## Discrepancies / observations vs. the brief

1. **Task-1 vs Task-2 disagree on the single fixture row.** Task 1 names the cluster
   `游资强势连板拉升` (a 游资 pattern) while Task 2 scores it `量化机构`. The two tasks
   are independent (clustering vs. rule scoring) and on a single sample the cluster
   centroid happens to trip the first pattern predicate while the equal-weighted 11-dim
   score leans quant. The brief treats Task-1 clusters only as a *sanity check* on
   Task-2, not a hard constraint — so this is acceptable for the skeleton. Tuned weights
   / cross-task reconciliation are future work.
2. **Case 1 exists; tests anchor on a synthetic group by design, not necessity.**
   Case 1 ("Shrinking Volume Game") *is* present and cited in the repo —
   `docs/competition-spec/topic-specifications-and-data.{en,zh}.md` §7.2 (恒工精密,
   2026-04-28). It describes a **different stock** than the 603997.SH fixture, so its
   figures cannot be asserted against the fixture's features. Feature unit tests are
   therefore anchored on a *constructed* synthetic tick group with hand-computed
   expected values — a deliberate engineering choice (deterministic, fixture-independent
   arithmetic), not because Case 1 is missing.
3. **Reference feature set is ~89 fields (competition-spec), baseline emits ~52–56.**
   This skeleton computes 31 features — the MVP subset needed for the rules + intent gate
   + clustering. Expanding toward the full reference set (RS/PD/OBP detail, the baseline's
   8th `TRD` family) is deliberate later work.
4. **Console mojibake on Windows.** Chinese labels print garbled to the cp936 console,
   but the on-disk CSVs are correct UTF-8-sig (verified by `repr()` of decoded values and
   the BOM check in `test_smoke.py`). Cosmetic only.

## Not done (out of scope for this step, by instruction)

- Real LightGBM/XGBoost training; full bounded-K selection; tuned scoring weights;
  real CB from a tick-cancel table; `submit.zip` packaging; holiday-calendar data.
