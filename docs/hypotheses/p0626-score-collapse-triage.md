# P0626 — 0626 board score-collapse triage (read-only)

**Status:** read-only diagnostic. No code / config / threshold / label / submit change made.
**Date:** 2026-06-28 · **Branch:** feat/phase6-parquet-submit · **HEAD:** 4b92c10 (+ pipeline b9c1b72 P2-intent-b)
**Triggered by:** 0626 zip board point **0.3265** (vs 0625 0.4558, −0.129 — not noise).
**Spec:** docs/LIS.md v1.6.8. Compliance #3 honored: nothing tuned to the board.
Related: [[rs-burst-ratio-dead-parquet]], `docs/hypotheses/p3-quant-youzi-leakage-0625.md`, `docs/hypotheses/p2-intent-b-sell-precision.md`.

---

## TL;DR — Most likely driver

**The 0.3265 collapse is NOT explained by any detectable defect in the submission, the
input data, or Task 2.** Submission is clean, the 0626 parquet is a complete full-day
snapshot, and BOTH Task 2 heads are *healthy-to-improved* on the 0626 OOS proxy.

> **Most likely driver of 0.3265 is Task 1 (pattern_type) on the 0626 answer key — or
> genuine 0626 key difficulty — because every head we *can* measure (capital_type,
> intention) held or improved on 0626, while pattern_type is (a) the only head whose
> distribution moved materially day-over-day and (b) the only head with ZERO
> ground-truth labels, i.e. a complete validation blind spot.**

Task 1 is the prime suspect **by elimination**, but it is currently **unfalsifiable** —
we have no pattern_type labels. The one remaining place a *fixable* bug could still hide
is a partial-parquet pack at 21:39 (H1b); the recommended next slice closes that.

---

## A. Submission integrity — **VERDICT: OK**

| check | 0624 | 0625 | 0626 |
|---|---|---|---|
| zip entries | 2 flat CSVs | 2 flat CSVs | 2 flat CSVs |
| predict rows (excl header) | 99 | 100 | **100** |
| pattern rows (excl header) | 99 | 100 | **100** |
| header | `stock_code,transaction_date,capital_type,capital_intention` (utf-8-sig BOM) | same | same |
| transaction_date | all `20260624` | all `20260625` | all **`20260626`** |
| zip↔loose CSV | identical | identical | identical |
| zip SHA256 | db2d9bd4… | 8a60d76f… | **e910c335…** |

- 0626 zip = 2 flat CSV entries, both correct schema, date column **exclusively 20260626**, 100 universe codes, 0 dup keys.
- Zip-extracted CSVs are byte-identical to the loose `outputs/20260626/*.csv`.
- **Universe expansion (99→100) happened 0624→0625, NOT 0625→0626.** 0625 and 0626 are the
  *identical* 100-code set (set-diff empty both ways). → **H4 rejected.**

## B. Task 1 vs Task 2 decomposition

Board returns one number: `Total = 0.4·Task1 + 0.6·Task2`. We infer offline.

### Prod distributions
| | 0624 (n=99) | 0625 (n=100) | 0626 (n=100) |
|---|---|---|---|
| **capital_type** | 游资38 量化31 散户30 | 游资41 量化31 散户28 | 游资42 量化30 散户28 |
| **capital_intention** | T0:61 卖19 买19 | T0:64 买26 卖10 | T0:63 卖21 买16 |
| **pattern_type** | 6 labels (机构32 主力21 游资16 卖压14 尾盘8 撤单8) | **4 labels** (机构**61** 游资17 卖压14 买盘8) | **4 labels** (机构**43** 游资28 卖压13 买盘16) |

- **capital_type / intention: stable across all three days** (within a few points). Confirms the "already similar" expectation.
- **pattern_type moved the most**: 机构长线配置 61→43, 游资强势拉升 17→28, 买盘主动占优 8→16.
  But note 0624→0625 swung 机构 32→61 (even bigger) for **near-zero board change** (0.4586→0.4558),
  so pattern concentration alone is a weak board lever cross-day (different keys, though).

### Cross-day flips 0625→0626 (identical 100-code universe)
| head | flip rate | dominant transitions |
|---|---|---|
| capital_type | **18%** | 量化→游资 5, 游资→量化 5 (balanced churn) |
| capital_intention | **54%** | 买入→T0 19, T0→卖出 15, T0→买入 10 |
| pattern_type | **39%** | 机构→买盘 11, 机构→卖压 8, 卖压→游资 5 |

Day-over-day flips are *expected* (different trading days) and carry no ground truth — they
size churn, not error.

### Offline OOS proxies (parquet recompute on committed LHB labels)
| head | 0625 | 0626 | Δ |
|---|---|---|---|
| **capital_type F1** | 0.4613 (n=16) | **0.5446 (n=14)** | **+0.083** ↑ |
| **intention F1** | 0.6923 (n=13) | **0.7473 (n=13)** | **+0.055** ↑ |

- 0626 capital_type per-class: 游资 P0.45/R1.00 · 量化 P1.00/**R0.33** · 散户 P1.00/R0.33
  → still the documented **量化→游资 leakage** ([[rs-burst-ratio-dead-parquet]]), but this is
  *chronic* (dead on 0625 too), not a 0626-new effect, and the aggregate still **rose**.
- 0626 intention per-class: 买入 P0.89/R0.89 · T0 P0.50/R0.67 · 卖出 0/0 (support 1).
- **Both Task 2 heads improved on 0626.** → Task 2-on-labels did NOT drive the collapse. → **H3 rejected on the proxy.**

## C. 0626 parquet data-quality audit — **VERDICT: DATA OK**

Parquet dirs landed Jun 28 ~21:30–21:33; submit packed 21:39.

| stream | 0624 bytes | 0625 bytes | 0626 bytes |
|---|---|---|---|
| 十盘档口 (snapshot) | 2.171 GB | 2.182 GB | **2.188 GB** |
| 委托补全 (order) | 3.656 GB | 3.692 GB | **3.768 GB** |
| 指数 (index) | 0.103 GB | 0.102 GB | **0.104 GB** |
| 逐笔委托 (order_raw) | 4.014 GB | 4.060 GB | **4.130 GB** |
| 逐笔成交 (deal) | 3.819 GB | 3.909 GB | **4.004 GB** |

All 5 streams present for 0626 and **larger than 0625** (consistent with a complete, busier day).

Deal-stream coverage / timestamp range:
| day | rows | distinct stocks | DealTime span | universe present | missing |
|---|---|---|---|---|---|
| 0624 | 219.9M | 5192 | 09:15:00 → 15:00:02 | 99/100 | 603721 |
| 0625 | 225.6M | 5191 | 09:15:00 → 15:00:02 | 100/100 | — |
| **0626** | **230.9M** | **5193** | **09:15:00 → 15:00:02** | **100/100** | — |

- 0626 is a **full session** (open auction → close), all 100 universe codes present, most rows of the three days.
- The capital_type/intention OOS recompute (Section B) reads snapshot+order+deal for the labeled keys and produced **clean, improved** results — independent confirmation the streams it touches are sane.
- → **H1 (incomplete/bad snapshot) rejected** on every measured dimension.

## D. Cross-day same-pipeline diff

Pipeline frozen at b9c1b72 between the 0625 and 0626 packs → **the only变量 is the 0626 parquet.**
Section C shows that input is complete; Section B shows the resulting Task 2 predictions are
healthy. The 18% capital_type churn is balanced (量化↔游资 5/5), not a one-way 量化→游资 cascade,
so the p3 leakage did not *worsen* on 0626 — it is steady-state.

## E. Falsifiable hypotheses (ranked)

| # | hypothesis | evidence FOR | evidence AGAINST | confirming test |
|---|---|---|---|---|
| **H2** | **Task 1 pattern regression / mis-map on 0626 key** | only head with big distribution move; **zero ground-truth labels = blind spot**; by elimination (Task 2 healthy) a head must have dropped ~0.22–0.32 | 0624→0625 had bigger 机构 swing with ~no board change | **seed pattern_type labels**, score Task 1 offline per day |
| **H5** | **0626 board key genuinely hard; proxy can't see universe-Task2** | every measurable head fine yet board fell; LHB labels are off-universe, board is on-universe | no positive evidence of a defect anywhere | seed on-universe labels (or accept day-variance) |
| **H1b** | **pack ran on partial parquet at 21:39 (files still finishing 21:30–21:33)** | tight 6-min window | files are complete NOW; deterministic seed | **re-run 0626 from current parquet, diff vs committed CSVs** |
| H3 | Task 2 intention overshoot (卖出 10→21) | 卖出 doubled | intention OOS **rose** to 0.747; 卖出 prod share normal vs 0624 (19) | covered by Section B — rejected |
| H1 | 0626 snapshot bad/incomplete | parquet landed mid-session | Section C: complete full day, +rows | rejected |
| H4 | bad stock added 99→100 | — | expansion was 0624→0625; 0625≡0626 universe | rejected |

**Recommended next slice (exactly one):** **0626 reproducibility re-run.** Re-run
`main.py --input parquet:data/202606 --date 20260626` to a *scratch* output dir and diff the
fresh `predict_result.csv` + `pattern_reco.csv` against the committed `outputs/20260626/*`.
This is purely diagnostic (does **not** repack or resubmit) and is the only test that can still
catch a *fixable* bug today (H1b partial-pack):
- **Identical** → H1b dead; collapse is H2/H5 → escalate to the structural fix below.
- **Differs** → the pack ran on incomplete data; we found the bug.

**Structural follow-up (dependent, needs human go):** Task 1 (pattern_type) is the prime
suspect *and* completely unvalidated. Seed pattern_type ground-truth labels so Task 1 gets its
own offline gate (mirror the capital/intention harness). Until then H2 cannot be confirmed or
denied, and 40% of the board score flies blind.

**Forbidden without approval:** board-driven threshold tweaks, limit-up nudges, P2-intent-b revert,
submit regen.

## F. Frozen-gate re-check

Code is frozen (b9c1b72) and the 0624-and-earlier parquet was **not** modified on Jun 28
(0624 dirs stamped Jun 25 19:23; 0625 dirs Jun 26 00:23–00:25; only 0626 dirs are Jun 28).
With frozen code + byte-identical older inputs, the through-0624 / through-0625 gates are
**unchanged by construction**:
- {through-0624} capital 0.6773 / n=77 · intention 0.6480 / n=76 — **unchanged**.
- {through-0625} capital 0.6500 / n=93 · intention 0.6480 / n=76 — **unchanged**.
- Per-day recompute observed this session: 0625 capital 0.4613, 0626 capital 0.5446; 0625 intent 0.6923, 0626 intent 0.7473.

## G. Compliance
Read-only triage. No tuning to the 0.3265 board point (compliance #3). No submit regen.
P2-intent-b (`b9c1b72`) stays — intention gate did not regress (0626 intent proxy **rose**).
