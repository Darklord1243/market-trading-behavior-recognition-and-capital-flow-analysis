# P3 Feature Batch — OFI + AP run-max + OBP spread dynamics + PI Herfindahl/VWAP

**Slice:** D6 Slice 2 (competitive-gap-audit-20260701.md §D2/§D6) · **Spec:** docs/LIS.md v1.6.8
**Branch:** feat/phase6-parquet-submit · **Parent:** Slice 1 falsified (p5-task1-metric-alignment.md §8 — Task-1 enrichment dead; Task-2 is this slice's lever)
**Gate corpus:** parquet:data/202606 (9 days 20260616–20260629) · Labels: tests/fixtures/validation_labels.csv (122 cap / 115 int)
**Status:** hypothesis (pre-code)

---

## 0. Objective

Add **snapshot-computable** microstructure features that fill the highest-ROI gaps in
the D2 inventory, and wire the single most defensible new axis
(`ap_active_buy_run_max`, in the 89-set + baseline `KEY_COLS` but absent from our
`features.py`) into `DIMS_YOUZI` — the weakest capital class (游资 P=0.52, F1=0.59,
**over-fires**: R=0.68 > P=0.52).

New feature families (all intraday-only, no look-ahead, no new data source):

| Family | Keys | Source columns |
|--------|------|----------------|
| **OFI** | `ofi_mean`, `ofi_std`, `ofi_positive_ratio` | `totalbidvolume`/`totalaskvolume` per-tick diffs |
| **AP run-max** | `ap_active_buy_run_max`, `ap_active_sell_run_max` | `price_change` sign runs (share of session in [0,1]) |
| **OBP spread** | `obp_spread_mean`, `obp_spread_std` | per-tick best-bid/ask from `bids`/`asks` book JSON |
| **PI** | `pi_herfindahl_5min`, `pi_herfindahl_30min`, `pi_vwap_deviation` | `hour`/`minute` bins + `price`/`tick_amount` |

**Only `ap_active_buy_run_max` enters a scoring dim (DIMS_YOUZI).** The other 9 keys
enter the rank-normalized matrix and therefore may perturb Task-1 clustering as a side
effect, but do **not** feed the capital or intention scorer directly. The primary gate is
the Task-2 capital proxy-F1.

---

## 1. Why each family should discriminate 游资 / 量化 / 散户

**OFI (order-flow imbalance).** OFI = Δbid_depth − Δask_depth per tick captures whether
resting liquidity is being *built on the bid* (buy pressure) or *pulled/added on the ask*.
游资 accumulate one-directionally — sustained positive OFI → high `ofi_mean`, high
`ofi_positive_ratio` (>0.5), and bursty `ofi_std`. 量化 market-make / rebalance
two-sidedly — OFI mean ≈ 0, `ofi_positive_ratio` ≈ 0.5, but rapid quote flipping can give a
high `ofi_std`. 散户 order flow is uncoordinated noise → mean ≈ 0, ratio ≈ 0.5, moderate
std. OFI is a strong microstructure-literature price-pressure signal (tutorial Path 1) and
is 0/3 in our current feature set.

**AP run-max (consecutive-aggression run length).** The longest unbroken run of
same-sign `price_change` ticks, as a share of the session, measures *deliberate directional
persistence*. 游资 push a name in sustained one-directional bursts → long buy runs →
high `ap_active_buy_run_max`. 量化 alternate/two-side and flip direction frequently →
short runs. 散户 are random → short-to-moderate runs. This is the "consecutive buy
aggression" axis the audit flags as a known 游资 separator that our rules never used — the
reason it is the one new dim wired into DIMS_YOUZI (target: lift 游资 *precision* by
requiring sustained aggression, not just a single mega print).

**OBP spread dynamics.** Per-tick best-bid/ask spread mean/std captures liquidity
provision vs. consumption. 量化 market-makers keep a tight, stable spread →
low `obp_spread_mean`, low `obp_spread_std`. 游资 sweeping the book widen and destabilize
the spread → higher mean/std. 散户 sit between. (Softest family — kept out of the required
discriminating-test set; emission only, no dim wiring.)

**PI Herfindahl + VWAP deviation.** `pi_herfindahl_5min/30min` = Σ(amount-share²) over
time bins — high when trading is concentrated into a few windows (游资 open-ramp / close-seal
bursts), low when spread evenly through the session (量化 continuous execution; 散户 diffuse
but un-bursty). `pi_vwap_deviation` = |last_price − VWAP| / VWAP — 量化 execute *around*
VWAP (their benchmark) → low deviation; 游资 mark the close away from VWAP → high deviation.
These complement our existing open30/close10 concentration with a
distribution-shape (Herfindahl) and a price-location (VWAP) axis.

---

## 2. Design locks

- **Missing columns → 0.0, never NaN** in the output dict (OFI when totalbid/askvolume
  absent; OBP when no book JSON; PI VWAP when Σtick_amount = 0).
- **AP run-max normalized as session share in [0,1]** (`run_max / n_ticks`) so it is a
  clean rank-normalizable proportion, not a raw count.
- **OBP `obp_spread` (first-snapshot) unchanged.** New keys are `obp_spread_mean/std` only.
- **Normalization:** all 10 new keys rank-normalize (they are NOT added to
  `normalize.EXCLUDE`). Their absolute scale is irrelevant to the scorer, which reads the
  rank-normalized value; EXCLUDE is reserved for keys whose raw absolute meaning drives a
  rule threshold (`limit_seal_*`, `cb_available`, `n_ticks`). Verified: no EXCLUDE change.
- **Only DIMS_YOUZI is touched** (`ap_active_buy_run_max`, True, False). DIMS_QUANT /
  DIMS_RETAIL are NOT given run-max without probe evidence (per prompt B2). get_intention,
  RS_CADENCE_SOURCE, label.py, model.py, cluster.py untouched.

---

## 3. Falsification criteria

Reject the DIMS_YOUZI wiring iff **either**:
1. Full-CSV capital weighted-F1 regresses below the frozen floor **0.6438**, **or**
2. Neither 游资 recall **nor** 散户 recall strictly improves vs the pre-slice baseline
   (游资 R=0.68, 散户 R=0.62 from audit D1.a; re-measured exactly below).

On falsification: **revert the DIMS_YOUZI edit first**; keep the feature *emission* if it
holds all 5 frozen floors and is otherwise harmless (it still enriches the Task-1 matrix and
is available for a future probe). Document the negative result in §5. Do **not** commit a
regressed scorer.

**Frozen floors (all must hold, no regression):**

| Subset | Metric | Floor |
|--------|--------|------:|
| Full CSV | capital | ≥ 0.6438 |
| Full CSV | intention | ≥ 0.6750 |
| through-0624 | capital | ≥ 0.6773 |
| through-0625 | capital | ≥ 0.6500 |
| P2-intent-b 0616–0623 | intention | ≥ 0.6271 |

Intention floors are expected byte-identical (get_intention untouched; the new features do
not enter the intent gate).

---

## 4. Task-1 side-effect note (informational)

The 10 new columns enter the rank-normalized 34→44-feature matrix, so Euclidean KMeans
silhouette on the ~100-stock panel may shift for any day. This is **reported, not gated** —
per Slice-1's falsification, Task-1 enrichment is not this slice's lever. Log 20260626
silhouette vs the p5 §8 baseline; do not tune features to silhouette.

---

## 5. Results — DIMS_YOUZI wiring FALSIFIED, reverted; features retained

Gate corpus `parquet:data/202606`, labels `tests/fixtures/validation_labels.csv`.
Measured in a single capital pass (one matrix build/day, scored twice): **PRE** =
features emitted but `ap_active_buy_run_max` NOT in DIMS; **POST** = with the dim
wired into DIMS_YOUZI. PRE reproduces the frozen baseline **exactly** — confirming
the new feature *emission* is inert for Task-2 (no new key enters any DIMS or the
intent gate; rank-normalization is per-column, so adding columns cannot move the
existing dims' scores).

| Metric | PRE (= baseline) | POST (dim wired) | Floor | POST verdict |
|--------|-----------------:|-----------------:|------:|:------------:|
| Full capital F1 | **0.6438** | **0.6356** | 0.6438 | ❌ regressed |
| 游资 P / R / F1 | 0.52 / 0.68 / 0.59 | 0.51 / 0.68 / 0.58 | — | P↓, F1↓ |
| 量化 P / R / F1 | 0.71 / 0.61 / 0.66 | 0.72 / 0.59 / 0.65 | — | R↓ |
| 散户 P / R / F1 | 0.77 / 0.62 / 0.69 | 0.74 / 0.62 / 0.68 | — | P↓ |
| Full intention F1 | 0.6750 | 0.6750 | 0.6750 | ✅ (unaffected) |
| through-0624 capital | 0.6773 | 0.6652 | 0.6773 | ❌ regressed |
| through-0625 capital | 0.6500 | 0.6395 | 0.6500 | ❌ regressed |
| P2-intent-b intention | 0.6271 | 0.6271 | 0.6271 | ✅ (unaffected) |
| 20260626 silhouette (info) | see below | — | — | — |

**Both falsification conditions (§3) are met by POST:** (1) full capital F1 fell below
0.6438, and (2) neither 游资 R (0.68→0.68) nor 散户 R (0.62→0.62) improved — the
consecutive-buy-aggression dim added noise to an already over-firing class rather than
sharpening it, and cost 散户 precision / 量化 recall via the shared arg-max.

**Disposition (executed): DIMS_YOUZI wiring REVERTED** (rules.py + regression-guard test
`test_ap_active_buy_run_max_not_wired_into_dims_falsified`). **Feature emission retained**
— it is provably inert for Task-2 (PRE == frozen baseline on all 5 floors) while filling
the audit D2 gaps (OFI 0/3, `ap_active_*_run_max` absent from the 89-set/KEY_COLS, OBP
spread dynamics, PI Herfindahl/VWAP) and enriching the Task-1 matrix; it stays available
for a future re-probe against fresh evidence.

### Task-1 side effect (20260626, informational — not gated)

Recomputed on the realistic 100-stock panel (fast batched cancel reads, results
byte-identical to the per-stock path):

| Metric | With Slice-2 features | Audit D1.b baseline | Δ |
|--------|----------------------:|--------------------:|--:|
| silhouette (daily Euclidean) | 0.1431 | 0.1509 | **−0.0078** |
| silhouette (Slice-1 enriched) | 0.1098 | 0.1509 | −0.0411 |
| best K | 12 | 7 | — |
| CH | 10.1 | 17.6 | −7.5 |

The 10 new columns entering the rank-normalized clustering matrix **mildly lower**
Task-1 silhouette/CH on this day (best K drifts 7→12). Single-day, informational —
but it means the emission is **not** a Task-1 win either.

### Disposition & recommendation

The Slice-2 features:
- **Task-2:** completely inert (PRE == frozen baseline on all 5 floors).
- **Task-1:** mild negative on 20260626 (silhouette −0.008 daily, best-K drift).
- **Only upside:** they fill the audit D2 inventory gaps and are available for a
  future re-probe.

Because they show **no measured benefit on either task** and a small Task-1 negative,
the parsimonious call is a **full revert** (drop both the wiring — already reverted —
and the feature emission), rather than shipping inert-but-slightly-Task-1-negative
columns into the production matrix.

_Decision (executed): **full revert.**_ `src/features.py`, `src/rules.py`, and
`tests/test_features.py` were reverted to HEAD (`git checkout`), so the working tree is
byte-identical to `5570b07` — suite back to **204 passed / 2 xfailed** (the pre-Slice-2
baseline). This document is the sole retained artifact — the negative-result record.
Nothing was committed. The DIMS_YOUZI wiring and all four feature families are gone from
code; do not re-attempt any of them without fresh gate evidence that clears the §3 floors
**and** shows a real per-class improvement.

### Appendix — measurement note (offline harness only, not shipped)

The offline gate was initially ~22 min/**day** (~3 h for 9 days). Profiling (cumulative)
showed **91%** of the time in `ingest_parquet.read_cancel_frame_parquet` → `_read_stream`,
which **re-scans the entire `order` parquet once per stock** (~10 s × ~100 panel stocks).
The Slice-2 feature computation itself was only ~3.7 s (of which OBP per-tick spread ~2 s).
The gate was made runnable (~13 min) by a **scratchpad-only** monkeypatch that reads the
`order` stream once per day for the whole panel and serves per-stock slices from cache —
**byte-identical** cancel frames verified (`.equals()` True across stocks incl. 92k-row
ones). This is a real production-pipeline optimization opportunity (`src/ingest_parquet.py`
+ the harness cancel-lookup loop), but is **out of scope** for this slice and was not
applied to `src/`.
