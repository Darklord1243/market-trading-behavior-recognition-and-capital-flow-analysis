# B-board Submit Runbook — daily cadence + paired-A/B protocol

> **Status:** operational runbook for **Board B (from 2026-07-13)**.  
> **Rules authority:** [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md)  
> (中文: [`../official_guidance/b-board-rules.zh.md`](../official_guidance/b-board-rules.zh.md)).  
> **FAQ / interpretability:** [`../official_guidance/competition-clarifications.md`](../official_guidance/competition-clarifications.md) §6.  
> This file **consolidates** standing directives from `docs/hypotheses/p5.7-board-paired-ab-0701.md` §§1–5
> and `docs/report/code-parity-ledger.md` (Rows 1, 18, 19). Where this file and the paired-A/B doc
> disagree on *experiment protocol*, **the paired-A/B doc wins**; where they disagree on *Board B
> calendar/window/scoring*, **`b-board-rules.*` wins**.

**Scope / calendar:**

| Window | Board | Requirement |
|---|---|---|
| through **Jul 10** | A-board (closed) | historical |
| **Jul 13 – Jul 24** | B-board | **both CSVs required daily**; ≥ **8** submit-days or excluded from final ranking |
| Eval cutoff | — | **Jul 24 15:00**; last scored trading day **Jul 22**; **Jul 24 no new stock samples** |
| Jul 28 – Aug 5 | Report phase (top-15) | `project_solution_report.docx` + `project_solution.zip` (spec §5.5) |

Scoring mechanics (`b-board-rules` + ledger Rows 18–19):

- **Best-of-day:** up to 3 uploads; the platform keeps the day’s **highest** score (not latest).
- **Missed / late window → 0** for that trading day (window = **T+1 15:00 – T+2 14:59** for day T).
- **Final rank:** **9-day WMA** (weights 9…1, denom 45), not a simple average.
- **Deterministic:** identical zip re-upload reproduces its instant score (historical check).

**Example:** sample for T=20260713 posts morning **2026-07-14**; submit that day’s answers after **15:00 on 07-14** and before **14:59 on 07-15**.

---

## 1. Pre-flight checklist (mandatory — every upload)

From paired-A/B §3, plus Board B window and ops gotchas:

```text
[ ] Universe = samples/B_board/stock_sample_{transaction_date}.xlsx
    (same day as --date since the 2026-07-15 platform rename; e.g. date 20260713 → stock_sample_20260713.xlsx)
[ ] Inside Board B window for this transaction_date (T+1 15:00 – T+2 14:59)
[ ] Platform slot has ADVANCED to today's expected transaction_date   ← check FIRST (see gotcha A)
[ ] config.TASK1_METHOD for this run: euclidean | dtw-complete   (LOGGED; euclidean is the floor)
[ ] predict_result.csv  unique transaction_date : __________
[ ] pattern_reco.csv    unique transaction_date : __________
[ ] Platform expected transaction_date          : __________
[ ] All three dates match EXACTLY
[ ] pattern_explanation filled for every row (Board B interpretability)
[ ] capital_type ∈ {游资, 量化, 散户} only
[ ] Zip contains exactly 2 root CSVs (predict_result.csv + pattern_reco.csv), nothing else
[ ] Zip built into the intended -o dir (see gotcha B: bare --pack lands in -o, not CWD)
```
**Gotcha A — platform date advance.** On 2026-07-03→04, five uploads failed because Tianchi had
**not advanced** to the 20260702 slot; the writer rejected the zip (`expected 20260701, got
['20260702']`). **Confirm the platform's current slot before generating**, and match both CSVs'
`transaction_date` to the slot the platform will accept — not necessarily the literal calendar
"yesterday." (Source: paired-A/B §"Episode context".)

**Gotcha B — `--pack` path.** A bare `--pack submit.zip` now resolves into the `-o` output dir (fixed;
memory `main-pack-writes-to-cwd`). A `--pack` value that contains a path separator is honored as-is.
Verify the zip landed where you expect before uploading.

**Gotcha C — GBK box / conda.** If generating via `conda run`, use `--no-capture-output`; this Windows
GBK box otherwise buffers and crashes child stdout on non-ASCII (memory `conda-run-gbk-buffering`).

---

## 2. Default submit path — scored days (the floor)

```python
# config.py — committed production default; do NOT change per-day
TASK1_METHOD = "euclidean"
```

**Example Board B generate (auto universe):**

```text
python main.py --input parquet:data/202607 --date 20260713 \
  -o outputs/20260713 --pack submit.zip
```

- `--date 20260713` = L2 / CSV `transaction_date` (predicted trading day)
- Auto universe → `samples/B_board/stock_sample_20260713.xlsx` (**same** trading day — filename convention since the 2026-07-15 platform rename)
- Pass `--universe` explicitly to override

**History:** before 2026-07-15 samples were named by **release** day (next trading day), and pairing `stock_sample_20260713.xlsx` with `--date 20260713` was a platform reject (2026-07-14). Repo samples were renamed to trading-day stems; the reject can no longer happen with correctly-named files.

Generate → pack (2-root zip) → run pre-flight → upload. **Do not** flip to `dtw-complete` on a scored
day without explicit human direction. Note (memory `dtw-candidate-needs-config-flip`): setting
`$env:TASK1_METHOD` is a **no-op** — dtw-complete requires flipping `config.TASK1_METHOD` in-process
(scratchpad runner) or shipping a separately-generated pack; never assume an env var switched it.

---

## 3. Paired-A/B explore protocol (free under best-of-day)

Allowed **only on explicit human direction** (paired-A/B §2): a non-scored/practice slot, a B-board
soak day with time to accumulate, or a deliberate second paired test (accept a possible drag while
both are live under the **9-day WMA**). Protocol:

1. Hold **Task 2 byte-identical** between the two variants (change only Task-1 labels).
2. Upload the **euclidean** floor first, then the **dtw-complete** explore — the slot keeps the **better** (Board B best-of-day).
3. Both must pass the §1 pre-flight independently.
4. Any resulting Δ is a Task-1-only measurement; log it, **do not** tune to it.
5. Both uploads must fall inside the Board B window for that `transaction_date`.

This is the exact mechanism that produced the H1 discovery (§4.3 / §5.4). It is an experiment, not a
score-chase.

---

## 4. After each upload — log only, no tuning

Record in `p5.7-board-paired-ab-0701.md` changelog (§6) or session notes (paired-A/B §4):

- data day · upload time · `TASK1_METHOD` · instant score
- any platform error text (verbatim)

That changelog is the audit trail behind ledger Rows 10/18/19 — keep it current so the report's board
claims stay reproducible.

---

## 5. Do-not-do (unchanged — paired-A/B §5)

- Do **not** tune Task-2 rules to instant scores (auto-DQ per LIS §3.3 / spec §3.3).
- Do **not** reopen P5.7 engineering without new falsifying evidence.
- Do **not** skip a submit to "finish analysis" — a missed day scores 0.
- Do **not** expand 龙虎榜 labels as a score lever this week.
- Do **not** edit `rules.py` / `features.py` / `label.py` / `validation_labels.csv` without an
  explicit human ask.
