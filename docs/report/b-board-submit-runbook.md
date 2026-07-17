# B-board Submit Runbook — daily cadence + paired-A/B protocol

> **Status:** operational runbook, Phase 3a. This file **consolidates** the standing directives that
> already live in `docs/hypotheses/p5.7-board-paired-ab-0701.md` §§1–5 (the authority) and the
> reproducibility contract in `docs/report/code-parity-ledger.md` (Rows 1, 18, 19). It adds nothing
> new to policy — it is the single checklist an operator follows each day so nothing is
> re-derived under time pressure. Where this file and the paired-A/B doc disagree, **the paired-A/B
> doc wins**; fix this file.

**Scope / calendar (as of 2026-07-06):**

| Window | Board | Requirement |
|---|---|---|
| through **Jul 10** | A-board | daily submit; keep euclidean floor; explore only on explicit human say-so |
| **Jul 13 – Jul 24** | B-board | **both CSVs required daily**; target **≥ 8 submit-days** (moving average restarts here) |
| Jul 28 – Aug 5 | Report phase (top-15) | `project_solution_report.docx` + `project_solution.zip` (spec §5.5) |

Two scoring mechanics govern everything below (spec §5.1; ledger Rows 18–19):

- **Deterministic:** an identical zip re-uploaded reproduces its instant score exactly (0.5245 twice).
- **Best-not-latest:** each day's slot keeps the **best** upload, and a missed day counts as **0**.
  A paired A/B therefore costs **0** on the moving average — you can explore for free, but you can
  never skip a day.

---

## 1. Pre-flight checklist (mandatory — every upload)

From paired-A/B §3, plus the two ops gotchas that have actually bitten us:

```text
[ ] Platform slot has ADVANCED to today's transaction_date   ← check FIRST (see gotcha A)
[ ] config.TASK1_METHOD for this run: euclidean | dtw-complete   (LOGGED; euclidean is the floor)
[ ] predict_result.csv  unique transaction_date : __________
[ ] pattern_reco.csv    unique transaction_date : __________
[ ] Platform expected transaction_date          : __________
[ ] All three dates match EXACTLY
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

Generate → pack (2-root zip) → run pre-flight → upload. **Do not** flip to `dtw-complete` on a scored
day without explicit human direction. Note (memory `dtw-candidate-needs-config-flip`): setting
`$env:TASK1_METHOD` is a **no-op** — dtw-complete requires flipping `config.TASK1_METHOD` in-process
(scratchpad runner) or shipping a separately-generated pack; never assume an env var switched it.

---

## 3. Paired-A/B explore protocol (free under best-not-latest)

Allowed **only on explicit human direction** (paired-A/B §2): a non-scored/practice slot, a B-board
soak day with time to accumulate, or a deliberate second paired test (accept a possible ~−0.02/day
drag while both are live). Protocol:

1. Hold **Task 2 byte-identical** between the two variants (change only Task-1 labels).
2. Upload the **euclidean** floor first, then the **dtw-complete** explore — the slot keeps the better.
3. Both must pass the §1 pre-flight independently.
4. Any resulting Δ is a Task-1-only measurement; log it, **do not** tune to it.

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
