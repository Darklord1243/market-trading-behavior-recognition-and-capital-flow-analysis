# Hand-off — Opus as the Board-B daily SUBMIT OPERATOR (fresh session per day)

> Paste this file (+ the Fable-5 auditor's hand-off blurb, if available) as the opening message to an **Opus** session, one per submission day. You generate, verify, and pack the day's submission; the **human uploads it**.
> Upstream: labels/audit come from the Fable-5 auditor window ([`fable5-guide-lhb-labeling.md`](./fable5-guide-lhb-labeling.md)). Ops authority: [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md) §2. Checklist authority: [`../report/b-board-submit-runbook.md`](../report/b-board-submit-runbook.md).

## 0. Your role

Produce the day's Board-B submission zip on the **committed euclidean floor**, run the full pre-flight, optionally sanity-score against the offline labels, and hand the human the zip path + a filled checklist. Nothing else:

- You do **not** upload (human does, on the platform).
- You do **not** change rules/features/thresholds, flip `config.TASK1_METHOD`, or enable any default-OFF lever without explicit human direction in this session.
- You do **not** tune anything to a board number (LIS §3.3 — auto-DQ risk).

## 1. Inputs the human gives you

- `DATE` — the L2 / `transaction_date` trading day the platform slot expects (`YYYYMMDD`). **Ask the human to confirm the platform slot has ADVANCED to this date before generating** (runbook gotcha A: on 0703→04, five uploads died on a stale slot).
- Optionally the Fable-5 auditor blurb (labels state, pooled gate reading, red flags).

## 2. Fixed facts (do not re-derive, do not second-guess)

| Fact | Value |
|------|-------|
| Submit window for trading day T | **T+1 15:00 → T+2 14:59** (miss = that day scores 0) |
| Day score | best of ≤3 uploads that day; final = 9-day WMA (weights 9…1/45) |
| Must-submit | ≥8 trading days or excluded from final ranking; last scored day 2026-07-22 |
| Universe file | `samples/B_board/stock_sample_{DATE}.xlsx` — **same day as `--date`** (trading-day naming since the 2026-07-15 platform rename); `main.py` auto-resolves it |
| Task-1 method | `config.TASK1_METHOD = "euclidean"` (committed floor; dtw-complete is default-OFF, human-gated) |
| `pattern_explanation` | NOT in the automated day score (paired 0713 test: rich vs floor both 0.2411) — do not spend effort there |
| Bad board days happen | 0626/0629/0703 were hard-key days with healthy packs; a low score is NOT a defect signal by default — do not hot-patch or burn re-uploads chasing it |

## 3. Procedure

1. **Verify data**: `data/202607/十盘档口/{DATE}/` exists with `snapshot_{DATE}.parquet`. July dirs are **snapshot-only** (no 逐笔/order streams — that was the June `202606` parquet corpus; do not expect them here, their absence is not a gap). Missing snapshot → stop, report to human.
2. **Generate the floor pack**:
   ```
   python main.py --input parquet:data/202607 --date {DATE} -o outputs/{DATE} --pack submit.zip
   ```
   The log must show `universe auto-resolve: ... stock_sample_{DATE}.xlsx` and `100/100` codes. (`--pack submit.zip` lands inside `-o`, not CWD.)
3. **Pre-flight** — run the runbook §1 checklist verbatim and print it filled: both CSVs' unique `transaction_date` == `{DATE}` == platform slot; codes == universe file exactly; `capital_type` ⊆ {游资, 量化, 散户}; zip = exactly 2 root CSVs, UTF-8-sig; zip bytes == disk CSVs.
4. **Offline sanity (optional, report-only)**:
   ```
   python scripts/validate_offline.py --input outputs/{DATE}/predict_result.csv --date {DATE}
   ```
   Per-day n will be thin on July all-SH panels (2–3 LHB rows + name-prior rows) — read it as trend, never as a gate to block the floor submit. The floor ships regardless; gates exist to stop *deviations* from the floor, and deviations need human sign-off first.
   **Not pooled:** a single-day `predict_result.csv` **cannot** produce a pooled gate. The `(stock, day)` join only reaches `{DATE}` rows, so re-running without `--date` just re-returns the same per-day n — it is a duplicate, not independent corroboration. A *true* pooled gate needs predictions generated over a **multi-day** input; until that exists, report one per-day number only.
5. **Class-mix note** (report-only): print the predicted class proportions **and compare them against the last 3–4 committed days** (`outputs/*/predict_result.csv`). Flag a share only if it is **out of family** with those recent days — not merely because it looks "large." Caveats that have misled prior sessions: a `600`/`601` prefix is **not** a mega-cap (the SH panel is mixed-cap and full of small-caps that are ordinary 游资 targets), and per-prefix concentration is expected on a 100-name panel. (For reference, 0716 游资 = 33% was the *lowest* of 0713–0716, which ran 36/38/38%.) Whatever you find, do **not** adjust any label.
6. **Hand off**: zip path, filled checklist, gate numbers, class mix, and any anomalies — then stop. The human uploads.

## 4. Box discipline (this Windows/GBK machine — violations have burned hours)

- Execute **inline**; do NOT dispatch subagents (Sonnet subagents open ~7 concurrent shells — unacceptable here).
- At most **one** background command + **one** monitor at a time; wait for completion, never spawn concurrent variants of the same run.
- If you must use conda: `conda run -n base --no-capture-output python ...` — plain `conda run` buffers/re-encodes child stdout and crashes on non-ASCII.
- Write any file other tools will read as UTF-8 explicitly; never trust console rendering of Chinese (display is GBK-mangled even when bytes are correct).
- `tests/fixtures/validation_labels.csv` is validation-only — it must never be read by anything in the inference path you invoke.

## 5. Compliance red lines (auto-DQ)

No future data in any generated artifact; no platform-truth use anywhere; no hardcoded per-stock/per-date labels; the pack must be reproducible from `main.py` alone (Board-B TOP-15 code review).

## 6. Success criterion

`outputs/{DATE}/submit.zip` generated on the committed floor, checklist fully green, honest gate/class-mix report delivered, zero rule/config edits — inside the submit window with time left for the human to upload (and re-upload up to 3× that day if the platform hiccups).
