> ⚠️ **SUPERSEDED (2026-06-14) — capital_type findings A1 / A1b are OVERTURNED.**
> A direct organizer answer (DingTalk) confirmed `capital_type` is **3 classes
> `{游资, 量化, 散户}`** with the **bare `量化`** (not `量化机构`), and `散户` is a real
> modelled class — not a placeholder/leak. This report's A1/A1b conclusions
> (which "byte-verified" `量化机构` and the 2-class set against the baseline guide)
> are exactly the bug the organizer answer corrects; **do not treat them as
> authoritative.** The baseline guide was wrong on both the class count and the
> quant string. The current code, tests, and brief Rev. 7 encode the corrected
> 3-class set. All *other* findings below (CSV format, cumulative-diff, Beijing
> clock, etc.) remain valid. Kept for audit history only.

# Verification Report — Project Brief vs. Official Competition Materials

**Scope:** Fact-check `docs/AFAC2026_Track1_Project_Brief.docx` (Rev. 4) against every official
file in the repo and against the raw bytes of the data files.
**Role:** Fact-checker only. No code written, no brief edited. Findings only.
**Date:** 2026-06-12.

## Sources inspected (all opened, not assumed)

| Source | What it is | How inspected |
|--------|-----------|---------------|
| `docs/AFAC2026_Track1_Project_Brief.docx` | The brief under test (Rev. 4, ~177 blocks) | `python-docx`, full paragraph + table extraction |
| `docs/official_guidance/baseline-guide.md` | English baseline guide (= reorg of `跑通Baseline.md`) | Read in full |
| `docs/official_guidance/跑通Baseline.md` | Chinese original baseline guide | Read in full — confirms English is faithful |
| `docs/official_guidance/score-improvement-tutorial.md` / `提分教程.md` | Score-improvement tutorial (EN/中) | Read in full |
| `docs/official_guidance/competition-clarifications.md` / `官方答疑与提交说明.md` | FAQ / submission notice (precedence file) | Read in full |
| `samples/AFAC2026.xlsx` + `raw_data/.../AFAC2026-training-data.xlsx` | Raw L2 fixture | `pandas`/`openpyxl` — shape, cols, dtypes, JSON, MD5 |
| `samples/predict_result.csv` + `raw_data/...` | Task-2 sample CSV | `pandas` — exact label `repr()`, counts, BOM bytes, MD5 |
| `samples/pattern_reco.csv` + `raw_data/...` | Task-1 sample CSV | `pandas` — pattern strings, BOM bytes, MD5 |
| `samples/stock-samples.xlsx` + `raw_data/...` | Stock whitelist | `pandas` — shape, code count, MD5 |

> **Note on the "competition spec/PDF":** there is **no PDF** in the repo. The official spec is
> present only as the markdown guides above (the `跑通Baseline.md` header states it was "reorganized
> from official competition guidance"). All "official" citations below are to those markdown files.

---

## Findings table

| # | Item | Status | Source (file + loc) | Brief § | Finding / recommended amendment |
|---|------|--------|---------------------|---------|---------------------------------|
| **A1** | `capital_type` = {游资, 量化机构} only; no 散户 | ✅ consistent | baseline-guide.md L78, L129, L424 (`assert isin(['游资','量化机构'])`); 跑通Baseline.md L74, L114, L489 | §3.1 (P21–24) | Brief locks exactly {`游资`,`量化机构`} and explicitly marks `散户` as a placeholder to **not** model. Verified against bytes: `predict_result.csv` actually contains `散户`(372)/`游资`(369)/`量化`(357) — so 散户 *does* physically appear, confirming the brief's warning is warranted, not hypothetical. |
| **A1b** | Exact string is `量化机构`, not bare `量化` | ✅ consistent (sharpened) | Sample bytes: `predict_result.csv` `capital_type` uniques = `散户`,`游资`,**`量化`** (NOT `量化机构`); official required = `量化机构` (baseline-guide L78/L424) | P24, P37 | Brief explicitly warns "emit `量化机构`, not `量化` alone." The sample file uses the **truncated `量化`** — extra confirmation the brief is right. **Optional amendment:** the brief notes the `散户` leak but could also note the sample's bare-`量化` truncation as a second placeholder defect. |
| **A2** | `capital_intention` = 买入/卖出/T0交易 (not "neutral") | ✅ consistent | baseline-guide L78, L129, L424; 跑通Baseline L74, L114; sample bytes: intuitions = `买入`/`卖出`/`T0交易` exactly | §3.2 (P25–26) | Brief locks the three exact strings and correctly states `T0交易` is the third slot. The word "neutral" the brief references ("loose English in Part II of the original spec") does **not** appear in any repo file — it cites an external/earlier spec not present here, but the **conclusion (`T0交易`) is correct and byte-verified.** |
| **A3** | CSV format: 4 cols fixed order/names, `transaction_date` YYYYMMDD, UTF-8-sig, no nulls/blank lines | ✅ consistent (one footnote) | baseline-guide L126–131; 跑通Baseline L112–116; clarifications L23, L81; sample bytes: both CSVs are 4-col, dates `20260507`-style | P18, P60, P129 | All rules correctly carried. **Footnote (not a brief error):** the *provided sample* CSVs are plain UTF-8 with **no BOM** (first bytes `b'sto'`, not `b'\xef\xbb\xbf'`), whereas submission must be UTF-8-**sig**. Brief correctly requires `sig` for output; just be aware the samples themselves are not sig. Brief calls the date an "8-digit integer" while clarifications say "use `dt` as string" — same on-disk digits, no conflict. |
| **A4** | `pattern_type` is open/free-form | ✅ consistent | clarifications L29–40 (Q3/A3 "自由打标签，不限个数"); baseline-guide L71; 官方答疑 L31 | §3.3 (P29), §6 (P67–68) | Brief states names are the team's design choice, scored on rationality/interpretability, not string match. Matches official FAQ verbatim. |
| **B5** | `AFAC2026.xlsx` = raw L2 (~4,937 rows, 65 cols, 1 stock 603997.SH, dt=20260507, nested-JSON bids/asks) — NOT an ~89-col feature table | ✅ consistent | **Byte check:** shape (4937, 65); `symbol` nuniq=1 → `603997.SH`; `dt` nuniq=1 → `20260507`; `bids`/`asks` are 10-level nested JSON with `order`/`bigOrderPercent` | P24, P27 | Exact match to brief's numbers. Confirmed raw L2 snapshot, not a reference feature matrix. |
| **B6** | No separate reference-feature-table file exists | ✅ consistent | `git ls-files` (no such file); clarifications L50 ("赛题是没有参考字段的，只有特征集参考"); baseline-guide L104–118 (7 feature **families**, computed by us) | P17, P27 | Confirmed: repo ships only raw L2 + samples; the "§3.1 field list" is a spec to compute, not data to load. The brief's specific "~89-column" figure is unverifiable (no such file to count) but the **negative claim is correct.** |
| **B7** | Official sample labels are random → read no signal | ✅ consistent | clarifications L51 ("样例为随机标签，仅供选手上传参考"); 官方答疑 L51 | P30, P50 | Brief instructs reading ZERO signal from sample labels (not the coupling, not the balance). **Internal-consistency caveat — see X1 below.** Byte check: sample is near-balanced (372/369/357 ≈ 1:1:1), so a naive reader *would* be misled; brief's warning is well-placed. |
| **C8** | Cumulative fields (`volume`/`amount`/`transactions`/`bigordervolume`) need `diff()` | ✅ consistent | baseline-guide L217 (Finding 1), L335; 跑通Baseline L205, L360. **Byte check:** `volume` monotonic increasing 0 → 30,193,038 | §4.2 (P40) | Correct. Brief adds `.clip(lower=0)` after sort — matches baseline code exactly. |
| **C9** | `hh` (Beijing) vs `date` (UTC epoch-ms) timezone trap | ✅ consistent | baseline-guide L218 (Finding 2), L322–328; 跑通Baseline L206, L351. **Byte check:** `date` = epoch-ms (1778118226000); `hh` uniques = [8,9,10,11,12,13,14,15,16] | §4.1 (P37), §4.2 (P42) | Brief states use `hh` (Beijing 8–16) for sessions, `date.dt.hour` is UTC 0–8 → PI all-zero. Byte-verified `hh` range is exactly 8–16. Brief also correctly flags `tradedate` 100% null and `date`/`snapshotdate` as per-row unique epoch-ms (byte check: `tradedate` nonnull=0/4937; `snapshotdate` nuniq=4937). |
| **C10** | CB (cancel) features zero in snapshot-only data; need tick-cancel table | ✅ consistent | baseline-guide L114, L390, L441; score-improvement L41–43, L111–135 (Path 2); 提分教程 L43. **Byte check:** the 65 cols contain no cancel-detail field; `bidaskrate`/`bidaskdifference` both ≡ 0 | §4.2 (P71), §4.3 (P48) | Correct: CB is unreconstructable from the snapshot stream; brief plans to source the separate tick-cancel table and to degrade gracefully when absent. `bidaskrate`/`bidaskdifference` ≡ 0 confirmed (matches score-improvement L29). |
| **C11** | OSS thresholds 50k / 10k / 1k | ✅ consistent | baseline-guide L341–344; 跑通Baseline L370–374 (Mega ≥50000, Large 10000–50000, Mid 1000–10000, Small <1000) | §4.2 (P41) | Exact match. |
| **D12** | DQ hard rules: intraday-only, no hard-coding, no answer-feedback in training, reproducibility/audit | ✅ consistent | baseline-guide L159–164 (4 hard rules); 跑通Baseline L144–149 | §1 (P11,P17), §5.1 (P96), §8 BRIGHT-LINE (P127), §9 (P130–140) | All four official red lines are carried correctly, including the subtle one (#3: no platform eval labels in training/tuning) which the brief elevates to a "BRIGHT LINE" against instant-score fitting. |
| **D13** | Nightly 18:00→08:00 cadence; `transaction_date` = yesterday's trading day | ✅ consistent | clarifications L10–23 ("18:00 更新…次日 08:00 前上传"; date must be yesterday); 官方答疑 L12–23 | §8 (P119–129) | Matches Q&A exactly. Brief adds "holiday-aware/dynamic date logic" — a reasonable inference, not contradicted. |

---

## E. Unsupported claims, contradictions, omissions

### E14 — Claims in the brief NOT supported by any official repo file (inference stated as fact)

| Tag | Brief claim | Brief § | Status | Note |
|-----|------------|---------|--------|------|
| U1 | **"Case 1 / Shrinking Volume Game"** worked example, with **CV ~24 ms**, **~70 % cancellation**, **iceberg split**, **bid-sweeping** — used as the labelling-logic source and "our ONLY feature ground-truth" | P11, P56, P84, P114 | ❌ unsupported | **No "Case 1", "案例", "24ms", or "70% 撤单" appears in any repo file** (grep across all official guidance = 0 hits). The numbers `51% / 70.9% / 31.8%` the brief cites elsewhere (P75) *do* match an **illustrative LLM-prompt example** in score-improvement-tutorial.md L271–277 — but that is a prompt demo, not a labeled "Case 1," and the 24 ms / 70 %-cancel figures appear nowhere. **Recommended amendment:** relabel "Case 1" as an *external/assumed* anchor (or cite its true source) and remove the "our ONLY ground-truth" weight until the source is produced; the feature unit-tests (P84, P114) currently depend on numbers not present in the repo. |
| U2 | Scoring is "validated against the **following 3 trading days**, ranked ~T+5, aggregated as a **moving weighted average**" | P12 | ⚠️ partly unsupported | Official says only **"T+5 日实盘回溯"** (baseline-guide L62/L151; 跑通Baseline L58/L136) and a **T+1** answer lag (clarifications L20). "following 3 trading days" and "moving weighted average" are **not in any repo file.** Mark as assumption. |
| U3 | "**A-board: 3 submissions/day**" budget | P85, P92, P117 | ⚠️ unsupported | No submission-count limit appears in any repo file (clarifications only describes the 18:00→08:00 window). Likely from the Tianchi page; flag as to-confirm. |
| U4 | "**B-board: submit ≥ 8 trading days (fewer = excluded)**" | P167, P170 | ⚠️ unsupported | Not in any repo file. Material (it gates final ranking) — confirm against the live Tianchi rules. |
| U5 | Competition calendar (A-board → Jul 10, B-board Jul 13–24), **real-name auth by Jul 20**, **team 2–3 members** | P5 header table, P160–170 | ⚠️ unsupported | None of these dates/limits are in the repo's official files. Plausibly from the Tianchi entry page; not verifiable here — flag as external. |

> All U2–U5 are competition-logistics facts that likely come from the live Tianchi page (not shipped
> into this repo). They are not necessarily *wrong* — they are simply **unverifiable from the materials
> provided** and should be tagged as "confirm against Tianchi" rather than presented as established.

### E15 — Things in official files that contradict / sit in tension with the brief

| Tag | Issue | Source | Brief § | Note |
|-----|-------|--------|---------|------|
| C-a | **Report-weight vs scoring-formula tension** (inherited from official): scoring is "Total = 0.4×Task1 + 0.6×Task2" (sums to 100 %), yet the tutorial says "the written solution report **accounts for 20 % of the final score**" | baseline-guide L136 vs score-improvement L289; brief P5 (0.4/0.6) + P96/P105 (20 %) | P5, P96 | The brief faithfully repeats **both** official numbers but does not reconcile them. This is an **official internal inconsistency**, not a brief fabrication. Recommend a one-line footnote in the brief acknowledging the 20 % report weight is a separate (likely final-round) component, not part of the 0.4/0.6 split. |
| C-b | **T+1 vs T+5**: clarifications frames evaluation as **T+1** (answer lag); baseline frames it as **T+5** backtest | clarifications L20 vs baseline-guide L62 | P12 | Both are official; they describe different things (data-availability lag vs backtest horizon). Brief blends them but adds the unsupported "3 days/moving average" gloss (see U2). Not a hard contradiction. |

### E16 — Material official content the brief omits

| Tag | Omission | Source | Note |
|-----|----------|--------|------|
| O1 | **`submit.zip` "no nested folders"** rule | baseline-guide L126; 跑通Baseline L112; clarifications L81 | Brief mentions `submit.zip` (P165) and CSV format guards (P129) but never states the explicit "no nested folders" packaging rule. Minor but a real DQ-adjacent format rule — recommend adding to the output-guard checklist (§8/§9). |
| O2 | **8th feature family `TRD`** (Tick-Trade structure) — the baseline's own extension to the 7 official families (architecture is "8 categories / 56 dims") | baseline-guide L370, L289; 跑通Baseline L216, L309 | Brief's §3.1 enumerates the 7 families (rs/cb/oss/ap/obp/pd/pi) but omits the baseline's TRD extension. Minor — the brief's MVP covers the same ground via OSS buckets — but worth noting for parity with the baseline code. |
| O3 | **Davies-Bouldin index** used in offline evaluation | baseline-guide L421; score-improvement L352 | Not material to *scoring* (the four scored metrics — silhouette/CH/Wasserstein/DTW — are correctly listed by the brief). DB is only an offline diagnostic; listing it is optional. |

### X — Internal consistency within the brief itself

| Tag | Issue | Brief § | Note |
|-----|-------|---------|------|
| X1 | The data-inventory table says to use `predict_result.csv` to "**reverse-engineer … class balance**" and as a "**joint-distribution sanity check**," but §3 later instructs reading "**ZERO signal**" from those labels and to "**drop even the earlier 'classes may be balanced' prior**." | P22 (table) vs P50 | Mild internal contradiction. §3 (P50) is clearly the intended, FAQ-aligned position (labels are random); the data-inventory cell (P22) reads as a leftover from an earlier revision. **Recommend:** soften the P22 cell to "format reference only (column names, order, date format, encoding)" to match P50. |

---

## Cross-checks that passed cleanly (byte-level)

- **File duplication:** `samples/*` and their `raw_data/*` twins are **MD5-identical** (predict_result, pattern_reco, AFAC2026 ↔ AFAC2026-training-data, stock-samples). Confirms the brief's "AFAC2026.xlsx / AFAC2026-training-data … the SAME file" (P24). ✅
- **`predict_result.csv`:** exactly **1,098 rows · 198 unique stocks · 19 unique dates (20260421–20260522)** — matches the brief's data-inventory numbers (P22) to the digit. ✅
- **`pattern_reco.csv`:** exactly **20 rows · 10 unique `pattern_type`** values = {大单吸筹, 尾盘突袭, 日内套利, 对倒拉升, 压单吸货, 集合竞价异动, 分时脉冲, 连续小单推升, 盘中诱多, 涨停板打开} — matches the brief's listed 10 names (P48) exactly. ✅
- **`stock-samples.xlsx`:** exactly **100 rows × 2 cols** (`股票代码`, `股票简称`) — matches "List of 100 stock codes + names" (P25). ✅ (Side note: the 198 stocks in `predict_result` are largely disjoint from this 100-stock whitelist — only ~52 overlap — consistent with the sample being a throw-away format demo, not tied to the whitelist.)
- **Intent gate thresholds:** brief's Stage-1 gate (买入: `active_buy_pct>0.6 ∧ imbalance>+0.08`; 卖出: `active_sell_pct>0.6 ∧ imbalance<−0.08`; else T0交易) reproduces the baseline `get_intention()` **verbatim** (跑通Baseline L467–479). ✅
- **Dual-sourced imbalance** `0.4×snapshot + 0.6×full-day` (P28) matches baseline L472. ✅

---

## VERDICT

**Sound to build from after a small set of amendments (N = 4 substantive + a few minor).**

The brief's **high-stakes core is correct and byte-verified**: the locked label vocabularies
(`游资`/`量化机构`; `买入`/`卖出`/`T0交易`), the CSV format rules, the data inventory (raw L2,
4,937×65, one stock-day, nested JSON, no reference feature table), the engineering traps
(cumulative→`diff`, `hh`-vs-`date` timezone, OSS thresholds, CB-zero-without-cancel-table), the
compliance red lines, and the nightly cadence **all match the official materials and the actual
bytes.** No ❌ errors exist in Sections A–D. This is a solid, accurate foundation.

The amendments needed before/while building:

1. **U1 (most important):** Excise or re-source the **"Case 1 / 24 ms CV / 70 % cancellation"**
   anchor. It is cited as the labelling-logic source *and* the "only feature ground-truth" for unit
   tests (P84, P114), but **no such case exists in the repo.** Either produce its real source or
   demote it to an explicit assumption, and base the Case-1-anchored feature tests on numbers that
   actually exist (e.g. the tutorial's 51 %/71 %/32 % prompt demo, clearly labeled as illustrative).
2. **U2–U5:** Tag the competition-logistics facts (T+5/"3-day moving average", 3 submissions/day,
   ≥8 B-board days, the Jul calendar, team size) as **"to confirm against the live Tianchi page"** —
   they are not in the shipped materials. U4 (≥8 B-board days) and U5 (Jul 20 auth) are
   ranking/DQ-critical, so verify them first.
3. **X1:** Reconcile the internal P22-vs-P50 contradiction (drop "reverse-engineer class balance"
   from the data-inventory cell to match the "labels are random" position).
4. **O1:** Add the "`submit.zip`, no nested folders" packaging rule to the output-guard checklist.

Minor/optional: C-a (footnote the 20 %-report vs 0.4/0.6 tension), A1b (note the sample's bare-`量化`
truncation), O2 (mention the baseline's 8th `TRD` family).

None of these block the architecture or the label design — they are citation hygiene and two real
omissions. **Recommendation: apply amendments 1–4, then proceed to build. Do not treat the "Case 1"
numbers as ground truth until their source is confirmed.**

*— End of report. No code written, no brief modified. Awaiting human review before any build step.*
