# P4 — 游资 relative-dominance guard tightening (capital precision probe)

**Slice:** Track 1 Slice 5B (competitive-gap-audit-20260701.md §D1.a — weakest capital class) · **Spec:** docs/LIS.md v1.6.8
**Branch:** feat/phase6-parquet-submit · **Parent:** Slice 2 falsified (p3-feature-batch-ofi-obp-pi.md — "probe before DIMS wiring")
**Gate corpus:** parquet:data/202606 (9 days 20260616–20260629) · Labels: tests/fixtures/validation_labels.csv (122 cap rows)
**Status:** **FALSIFIED (offline probe, pre-code)** — violates the frozen through-0624 ship floor at every positive margin.

---

## 0. Objective

游资 is the weakest capital class by precision (full n=122: **P=0.519, R=0.683, F1=0.589** —
it **over-fires**, R » P). Slice 2 proved that adding new *features* to `DIMS_YOUZI`
regresses capital (0.6438→0.6356, fully reverted). This slice instead probes a **structural
guard** — no new features, no DIMS expansion: require 游资 to win by *relative dominance*
over the runner-up class, not by a bare arg-max.

## 1. Mechanism

`score_capital_type` currently assigns 游资 (index 0) whenever `score_yz` is the arg-max of
the eligible classes. 量化/散户 already carry a relative guard (散户 needs
`RETAIL_WIN_MARGIN=0.05` over both rivals); 游资 carries **none** — a marginal `score_yz`
that barely tops `score_qt` still wins. The probe adds a symmetric guard:

```
best = arg-max over eligible classes                     # unchanged
if best == 游资 and (score_yz < score_qt + YOUZI_WIN_MARGIN):
    best = 量化                                           # demote marginal 游资
```

(When 游资 is the arg-max, 散户 is provably ineligible — retail eligibility requires
`score_rt ≥ max(yz,qt)+0.05 > score_yz`, which would make 散户 the arg-max — so the
runner-up is always 量化.) `YOUZI_WIN_MARGIN` is a single tunable constant, LHB-calibrated
on validation_labels.csv only, never the board.

## 2. Falsification criteria (binding, from the slice brief)

Revert if **any** of:
- full capital F1 < 0.6438, **OR**
- **through-0624 < 0.6773**, **OR**
- through-0625 < 0.6500, **OR**
- 游资 R drops without 游资 P gain (net harm).

## 3. Success criteria

full F1 ≥ 0.6438 (prefer strictly higher) **AND** 游资 P improves vs 0.52 with 游资 F1 ≥ 0.59
**AND** intention gates byte-identical.

---

## 4. Result — offline margin sweep (ONE ingest pass; probe is a faithful oracle)

The guard was probed **without touching rules.py**: the exact `guarded_pred` logic above was
applied in pure Python to the per-(stock,day) score triples produced by the real
`normalize → score_capital_type` path (`scripts/validate_offline.score_rows`). Sanity:
**margin=0 reproduces the live gate byte-for-byte** (0.6438 / 0.6773 / 0.6500, identical
per-class P/R/F1), so the sweep is a faithful oracle for the wired guard.

| YOUZI_WIN_MARGIN | full wf1 | **thru-0624** | thru-0625 | 游资 P (full) | 游资 F1 (full) |
|---:|---:|---:|---:|---:|---:|
| **0.000 (baseline)** | 0.6438 | **0.6773** | 0.6500 | 0.519 | 0.589 |
| 0.005 | 0.6359 | 0.6641 | 0.6393 | 0.509 | 0.574 |
| 0.010 | 0.6593 | 0.6641 | 0.6491 | 0.540 | 0.593 |
| 0.015 | 0.6669 | 0.6641 | 0.6589 | 0.551 | 0.600 |
| 0.020 | 0.6669 | 0.6641 | 0.6589 | 0.551 | 0.600 |
| **0.030** | **0.6730** | 0.6747 | **0.6773** | **0.578** | **0.605** |
| 0.040 | 0.6562 | 0.6747 | 0.6661 | 0.558 | 0.571 |
| 0.050 | 0.6477 | 0.6747 | 0.6547 | 0.548 | 0.554 |
| 0.060 | 0.6549 | 0.6747 | 0.6639 | 0.561 | 0.561 |
| 0.080 | 0.6371 | 0.6612 | 0.6403 | 0.553 | 0.532 |
| 0.100 | 0.6144 | 0.6544 | 0.6201 | 0.531 | 0.466 |

## 5. Verdict — FALSIFIED (through-0624 floor)

**No positive margin holds the through-0624 ship floor of 0.6773.** The maximum through-0624
at any positive margin is **0.6747** (margins 0.03–0.06) — short by 0.0026. A single true-游资
in the 0624 subset sits at a near-tie (`score_yz − score_qt < 0.005`); it is *correct* under
bare arg-max but the guard demotes it to 量化 at every margin ≥ 0.005, and no larger margin
recovers it. Because the brief makes through-0624 (the LIS v1.6.8 ship criterion) a **hard
veto**, the mechanism is falsified as specified.

**The mechanism is NOT dead — it is blocked by one row on one frozen subset.** At
**margin=0.03** it does exactly what it was designed to do everywhere else:
- full **0.6438 → 0.6730** (+0.0292)
- through-0625 **0.6500 → 0.6773** (+0.0273)
- 游资 **P 0.519 → 0.578**, **F1 0.589 → 0.605** (precision AND F1 both up — no net-harm signature)

Every success criterion is met *except* the through-0624 hard floor, which it misses by a
single near-tie row (0.0026).

## 6. Disposition

- **No code written; nothing to revert.** Probe-first discipline (the Slice 2 lesson)
  avoided a build/revert cycle. `DIMS_*`, intention path, features, cluster, and
  validation_labels.csv were untouched — intention gates are trivially byte-identical.
- **Do NOT ship the guard** under the current binding floors.
- **Open question for the human lead (NOT self-authorized):** the through-0624 floor is an
  in-sample-leaning snapshot (LIS v1.6.8 notes its own −0.0198 dip was "pure OOS label-set
  expansion, not a regression"). If the lead judges the 0624 floor may soften to accept a
  0.0026 miss in exchange for +0.029 full / +0.027 through-0625 / 游资 P 0.52→0.58, the wired
  guard at margin=0.03 is ready to implement under TDD. Otherwise this stands as a documented
  negative result. **Do not tune the margin to spare the single 0624 row** — that is fitting
  one constant to one row on the frozen subset (overfit / compliance-adjacent) and is out of
  scope.
