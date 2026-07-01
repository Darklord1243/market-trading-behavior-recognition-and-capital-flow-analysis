# P3 — 量化→游资 leakage on directional up-days (0625 triage addendum)

**Status:** read-only diagnostic. No code / config / threshold change made.
**Date:** 2026-06-26 · **Triggered by:** 0625 board point 0.4558 (vs 0624 0.4586, non-comparable dates).
**Frozen gates re-confirmed unchanged at time of writing:** capital_type 0.6773/n=77, intention 0.6480/n=76.
Related: [[normalize-exclude-leak-clustering]], `docs/hypotheses/p2-intent-t0-dominance.md`.

## 0. Why this exists
0625-only capital_type proxy dipped to **0.4613/n=16**, entirely on 量化 recall
(**1/6**; precision stayed 1.00). This doc tabulates the true-量化 keys, identifies
the error direction and the actual driver, and **falsifies the originally-proposed
cause** (limit-up seal). It recommends a falsifiable next slice — it does **not**
change the scorer.

## 1. Confusion (0625, n=16, gate path = validate_offline)
```
pred    散户  游资  量化
truth
散户       3    1    0
游资       2    4    0
量化       0    5    1
```
Per-class recall: 游资 4/6 · **量化 1/6** · 散户 3/4.

**Error direction is unambiguous and systematic: 量化 mispredicts as 游资, 5/5.
Zero 量化→散户.** (Frozen {through-0624} 量化 recall is 0.77 — this is a fresh-day
OOS effect, not a frozen-set regression.)

## 2. True-量化 score triples (s_yz / s_qt / s_rt)
| stock | pred | s_yz | s_qt | gap (yz−qt) | seal_up | net-buy-skew | oss_mega_amt | oss_small_amt | rs_burst |
|-------|------|------|------|-------------|---------|--------------|--------------|----------------|----------|
| 000100 | 游资 | 0.678 | 0.443 | +0.235 | **0.59** | 0.20 | 0.981 | 0.000 | 0.0 |
| 000636 | 游资 | 0.606 | 0.593 | **+0.013** | 0.39 | 0.12 | 0.626 | 0.157 | 0.0 |
| 002025 | 游资 | 0.579 | 0.571 | **+0.008** | 0.35 | 0.22 | 0.485 | 0.045 | 0.0 |
| 002687 | 游资 | 0.616 | 0.564 | +0.052 | 0.00 | −0.06 | 0.706 | 0.087 | 0.0 |
| 300961 | 游资 | 0.532 | 0.505 | +0.027 | 0.01 | 0.27 | 0.256 | 0.012 | 0.0 |
| **002976** | **量化 ✓** | 0.472 | **0.710** | −0.238 | 0.00 | 0.10 | 0.196 | 0.007 | 0.0 |

## 3. Hypothesis test — "limit-up / net-buy skew → 量化 read as 游资"
**Partially FALSIFIED.**
- **Limit-up seal: NOT the driver.** Only 1/5 misses (000100) is limit-up-sealed
  (≥0.5). limit-up-sealed rate MISS=0.20 vs OK=0.00. The B.3 limit-UP
  de-contamination in `score_capital_type` already targets the sealed case; 4/5
  misses are non-sealed and B.3 cannot touch them.
- **Net-buy skew: present but non-separating.** 4/5 misses have buy-skew 0.12–0.27,
  but genuine 游资 (000783 0.15, 300819 0.33) overlaps the same range — skew alone
  does not discriminate quant from youzi.

## 4. Actual driver — margin fragility from weak/dead 量化 dims
Mean s_yz MISS=0.602 vs OK=0.472; mean s_qt MISS=0.535 vs OK=0.710. The misses are
**not** cases where 量化 evidence is absent — they are coin-flip-close arg-maxes
(3/5 within 0.05) where 游资 evidence narrowly wins. Root cause, panel-wide (n=116):

| 量化 dim (DIMS_QUANT) | panel stat | verdict |
|-----------------------|-----------|---------|
| **`rs_burst_ratio`** | **0/116 nonzero, std 0** | **DEAD on parquet corpus** — casts a constant vote for every stock → zero discrimination |
| `oss_small_amount_pct` | med 0.015, max 0.233, std 0.041 | near-flat / weak |
| `rs_interval_cv` (LOW=quant) | med 17.88, range 11.4–18.5, std 1.71 | tightly clustered HIGH on this day → weak separation |

With `rs_burst_ratio` dead and `oss_small_amount_pct` near-flat, 量化's positive
evidence collapses onto a single dim (`rs_interval_cv` low) that itself
non-discriminates on a directional day. Meanwhile 游资's `oss_mega_amount_pct`
(quant accumulation prints are large: 0.49–0.98 on the misses) and `ap_active_buy_pct`
fire on the very same names. Net: s_yz floats ~0.60 on quant limit-up names and
edges a deflated s_qt.

## 5. Recommended next slice (0626) — hypothesis-first, gated, NOT board-driven
**Investigate why `rs_burst_ratio` is identically 0 on the parquet corpus.** It is a
量化 discriminator currently contributing nothing. Two falsifiable outcomes:
1. **Feature-extraction bug** (burst not computed from parquet order/tick stream) →
   fix is a measurement correction, not a label-tuned threshold. Re-extract, then
   re-run BOTH frozen gates; promote only if 量化 recall rises **without** moving
   {through-0624} 0.6773/0.6480.
2. **Genuinely absent in this data** → drop `rs_burst_ratio` from DIMS_QUANT (it is
   dead weight diluting the score) and re-confirm gates.

Either path is decided by the frozen gates, never by the board. **Do not** add a
limit-up→量化 nudge: the data shows seal is not the driver, so such a nudge would be
fitting noise. **Do not** touch `get_intention` (intention gate is unaffected here).

## 6. Compliance
Read-only triage. No tuning to the 0.4558 board point (compliance #3). P2-intent-b
(`b9c1b72`) stays — no frozen-gate regression observed.

---

## 7. P3.2 probe (2026-06-28, read-only) — `rs_burst_ratio` source resolved

**Verdict: §5 outcome (1) — FEATURE-EXTRACTION BUG (wrong source), NOT genuine absence.**

`_rs_features` (src/features.py:103) keys off `group["datetime_utc"]`, which in the parquet
path is built **only from the snapshot stream (十盘档口 `TickTime`)** — see
`ingest_parquet._clean_snapshot:211` → `pipeline_parquet.build_feature_matrix_for_panel`
loads snapshot as the cleaned frame; the deal stream is read only for *sizes*
(`read_deal_sizes_parquet`) and the order stream only for *cancels*. **The true tick
timestamps never reach `_rs_features`.**

### Burst by source — 0625 labeled keys (n=16), burst = share of inter-event intervals <100ms
| source (stream / col) | what feeds it | mean burst | median interval | rows/stock |
|---|---|---|---|---|
| **snapshot 十盘档口 `TickTime`** | **used by `_rs_features` today** | **0.000 (all 16)** | **3000 ms** (exact) | ~3k–5k |
| deal 逐笔成交 `DealTime` | NOT fed to RS | 0.59–0.95 | **0–10 ms** | 8k–769k |
| order 逐笔委托 `OrderTime` | NOT fed to RS | 0.33–0.96 | 0–240 ms | 14k–794k |

Snapshot is **~3 s sampled → zero sub-100 ms intervals are even possible**, so `rs_burst_ratio≡0`
for every stock by construction. The sub-100 ms burst signal **exists abundantly** in the tick
streams. (Same root afflicts `rs_interval_cv`: snapshot's single lunch-gap outlier dominates →
~18 for *every* stock → also non-discriminating. The whole RS cadence block is snapshot-degenerate.)

### Directional-day discrimination spot check (mean burst by p3 truth class)
| truth | n | mean **deal**_burst | mean **order**_burst |
|---|---|---|---|
| 散户 | 4 | 0.635 | 0.472 |
| 游资 | 6 | 0.778 | 0.705 |
| 量化 | 6 | 0.808 | 0.776 |

- **Ordering is correct** (散户 < 游资 < 量化) — a re-sourced burst dim adds **genuine** signal,
  strongest at separating **散户 (low) from {游资,量化} (high)**.
- **But it does NOT cleanly fix the p3 量化→游资 boundary**: on a directional day 量化 (0.808) and
  游资 (0.778) overlap heavily, and individual genuine 游资 (600584 deal_burst **0.915**, 000783
  **0.903**) out-burst several true 量化 (002687 0.691, 300961 0.703). A naive "high burst → 量化"
  vote would mis-pull those high-burst 游资 into 量化. `order_burst` separates 量化/游资 marginally
  better (Δ0.07 vs Δ0.03) but is still weak.

### Recommendation (needs human go — NOT implemented; code change out of this read-only scope)
1. **Re-source the RS cadence block** (`rs_burst_ratio`, `rs_interval_cv`, `rs_split_similarity`)
   from the tick stream (deal `DealTime` and/or order `OrderTime`) instead of snapshot `TickTime`.
   This is a **measurement correction**, decided by the **frozen gates**, never the board.
2. **Calibrate expectations:** treat this as reviving a dead 散户-vs-rest discriminator, **not** a
   targeted p3 fix. Promote only if {through-0624} 0.6773 / {through-0625} 0.6500 **do not regress**
   and 量化 recall rises. Do **not** pair it with a limit-up→量化 nudge (§5).
3. Decide deal vs order source on the frozen gate (order = "订单爆发", closer to the feature's intent;
   deal = "成交爆发"). The feature name `订单/成交爆发比率` covers both — pick by gate delta, not by board.

Probe: `scratchpad/p3_burst_probe.py` (read-only; filtered pyarrow reads, never writes under data/).
