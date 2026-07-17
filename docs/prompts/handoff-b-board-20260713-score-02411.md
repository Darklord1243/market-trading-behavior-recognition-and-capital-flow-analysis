# Handoff — Board B 20260713 score collapse triage (0.2411)

> **Paste this entire file into a new Cursor / Claude Code window as the opening message.**  
> **Mode:** read-only diagnosis first → propose fixes → wait for human approval before code/config changes.  
> **Compliance:** `docs/LIS.md` §3.3 — board/instant scores are **verification only**; do **not** tune thresholds/weights/rules to the 0.2411 number.

---

## 0. Mission

Figure out **why the accepted Board B submit for trading day `20260713` scored `0.2411`**, and what (if anything) is **fixable** before the next upload window — without violating §3.3.

Instant score logged: **2026-07-14 22:22:23 → 0.2411** (after a corrected re-upload).

---

## 1. What already happened this session (do not re-litigate)

### 1.1 Ops bug (FIXED) — wrong stock sample pairing
First upload was **rejected** by the platform:

> `predict_result.csv` … 100 … `['600110.SH', '600149.SH', '600172.SH', '600176.SH', '600186.SH']` …

**Cause:** we used `stock_sample_20260713.xlsx` with parquet `--date 20260713`.  
**Correct Board B pairing:**

| Concept | Jul 14 upload | Path / field |
|---------|---------------|--------------|
| Sample **release** day | **20260714** | `samples/B_board/stock_sample_20260714.xlsx` (platform stock list) |
| L2 / predicted trading day | **20260713** | `parquet:data/202607 --date 20260713`, CSV `transaction_date` |

Code fix shipped in working tree: `resolve_default_universe(--date)` → `stock_sample_{next_trading_day}.xlsx`.  
Docs: `docs/official_guidance/b-board-rules.{zh,en}.md` (date-pairing callout), `docs/report/b-board-submit-runbook.md`.

> **⚠ Superseded by the 2026-07-15 platform rename:** sample filenames now use the L2 **trading** day
> (`stock_sample_{--date}.xlsx`), repo files were renamed to match, and `resolve_default_universe` now
> resolves same-day. All `stock_sample_20260714.xlsx` references in this document are the **pre-rename**
> name of the file that holds the **20260713** universe (now `stock_sample_20260713.xlsx`).
> Authority: `b-board-rules.en.md` §2.2.

### 1.2 Accepted zip (scored 0.2411)
**Path:** `outputs/20260713/submit.zip`  
**Generated:** 2026-07-14 ~22:20  
**Log confirms:**
- universe auto-resolve → `samples/B_board/stock_sample_20260714.xlsx`
- `transaction_date=20260713`, **100/100**, **0 missing**
- Task1 method: **euclidean** (floor; `config.TASK1_METHOD`)
- capital: 游资 36 / 散户 33 / 量化 31
- intent: T0 62 / 卖出 31 / 买入 7
- patterns (5): 盘口撤单博弈 27, 卖压主动出货 20, 机构长线配置 20, 量化高频T0套利 17, 游资强势拉升 16
- `pattern_explanation`: non-empty for all rows; lengths ~49–53 chars (template-ish)

Sanity check already done: reject-list codes **absent**; codes **exact-match** 0714 sample.

→ **0.2411 is a real scored result on a format-valid submit**, not a reject artifact.

---

## 2. Score context (A-board history — for calibration)

Typical A-board instant band for this pipeline:

| Band | Examples | Reading |
|------|----------|---------|
| Good | 0701 **0.5245**, 0702 **0.5566** | “good key” days |
| Mid | 0624/0625 ~**0.45–0.46**, 0703 **0.4160** | |
| Collapse | 0626 **0.3265**, 0629 **0.3333**, early 0623 **0.2597** | hard-key / intent-degen eras |
| **Board B day-1** | **20260713 → 0.2411** | **below prior collapse floor** |

Prior conclusion (do not ignore): day-to-day swings often **not** explained by offline Task-2 / output mix — see `docs/hypotheses/hard-key-case-control-20260706.md`, `p0626-score-collapse-triage.md`.  
But **0.2411 is worse than 0626/0629**, so treat as: **possible hard-key day OR new Board-B-specific failure** (rules changed).

Leaders historically ~0.77–0.85 on A-board (audit notes). Gap is large.

---

## 3. Board B rule deltas vs A-board (new failure surface)

Authoritative: `docs/official_guidance/b-board-rules.en.md` + `competition-clarifications.md` §6.

| Delta | Implication for 0.2411 triage |
|-------|-------------------------------|
| **`pattern_explanation` scored on B** (not on A) | Template explanations (~50 chars, “主导特征: …”) may now **hurt** Task-1 interpretability |
| **`capital_intention` = interpretability only**; F1 on **`capital_type`** | Intent mix (T0 62%) less central than capital 3-class; don’t chase intent first |
| Rotating 100-stock universe daily | Normalization / cluster geometry on a **new panel** each day; A-board static list habits may not transfer |
| Best-of-day + **9-day WMA** | One bad day is costly but not fatal; still need ≥8 submit-days |
| Submit window T+1 15:00 – T+2 14:59 | Ops already fixed; not the score issue |

---

## 4. Hypotheses to triage (ordered)

Work top-down. **Falsify with evidence** before proposing code.

### H0 — Submission integrity (quick, expected PASS)
- Zip root = 2 CSVs only; UTF-8-sig; 100 rows; date pin 20260713; codes ⊆ / == 0714 sample.
- Recompute SHA / row counts vs `outputs/20260713/*`.
- Confirm `TASK1_METHOD=euclidean` for the scored zip.

### H1 — Board-B interpretability channel collapsed (NEW, high priority)
- B now scores `pattern_explanation`. Ours look **generic templates** (same length, “显著高于市场均值”).
- Compare to A-board days that scored 0.52+ : were explanations the same templates? If yes, either (a) B weights them much more, or (b) not the main driver.
- Offline: diversity / specificity metrics on explanation text; cluster-name ↔ feature attribution coherence.

### H2 — Task-1 geometry weak on this rotating panel
- Euclid silhouette / CH for the submitted `pattern_type` partition on the 0713 feature matrix (board-aligned proxy per H1 in `score-boost-direction-20260704.md`).
- Compare to 0701/0702 (0.52–0.56 days) and 0626/0629 (~0.33 days).
- If sil is *not* unusually bad vs collapse days, geometry alone doesn’t explain dropping to 0.24.

### H3 — Task-2 capital_type mismatch on new Board-B names
- New universe ∩ A-board labels may be tiny (0714 ∩ A-list was ~9 historically).
- Offline proxy: if any LHB / validation labels exist for 0713 stocks, score weighted F1; if none, say so — don’t invent labels.
- Check for systematic class skew vs A-board good days (here: fairly balanced 36/33/31 — not obvious).

### H4 — Hard-key / answer-key day (unfixable)
- Same as A-board collapse triage: if H0–H3 find **no defect**, document as hard-key candidate and **do not** thrash rules for one day.
- Still propose **non-tuning** improvements that help average (explanations, Task-1 board-aligned metric).

### H5 — Wrong mental model of scoring formula
- Confirm we still believe Total ≈ 0.4·Task1 + 0.6·Task2.
- B Q&A: clustering scored on **contestant’s own labels** (cohesion/separation); intention not F1-primary.
- Ask only if evidence requires: DingTalk clarifications — don’t block triage on unanswered Qs.

---

## 5. Read order (mandatory)

1. `docs/official_guidance/b-board-rules.en.md` (§2 date pairing + scoring)
2. `docs/official_guidance/competition-clarifications.md` §6 (B Q&A — explanations, capital F1)
3. `docs/report/b-board-submit-runbook.md`
4. `docs/LIS.md` §2–§3 (locks + §3.3)
5. `docs/hypotheses/score-boost-direction-20260704.md` (score anatomy; H1 euclid proxy)
6. `docs/hypotheses/hard-key-case-control-20260706.md` + `p0626-score-collapse-triage.md` (collapse playbook)
7. `docs/hypotheses/p5.7-board-paired-ab-0701.md` (euclidean floor; don’t flip dtw on scored day without human ask)
8. Artifacts: `outputs/20260713/{predict_result,pattern_reco,submit.zip}`

---

## 6. Constraints

- **Do not** change `rules.py` / thresholds / `validation_labels.csv` to chase 0.2411.
- **Do not** switch scored-day floor to `dtw-complete` without explicit human approval (paired A/B previously showed dtw **hurt** board).
- **Do** prefer offline, label-free metrics (silhouette, explanation quality audits, distribution vs historical good/collapse days).
- **Do** keep daily submits alive (≥8 days); a 0 day from miss is worse under WMA than a weak day.
- Working tree has uncommitted Board-B docs + `resolve_default_universe` fix — don’t revert; extend carefully.
- Python via **conda** (`conda run -n base --no-capture-output …`).

---

## 7. Deliverables for this new window

1. **Triage note** under `docs/hypotheses/` e.g. `b-board-20260713-score-02411-triage.md` with:
   - H0–H5 verdict table (supported / rejected / inconclusive)
   - Whether 0.2411 looks **fixable defect** vs **hard-key / B-scoring shift**
2. **Ranked next actions** (max 3), each with: offline test, risk to §3.3, expected day-score lever.
3. If a fix is proposed: **design briefly → wait for human OK** before implementing.
4. Optional: one **paired best-of-day** explore plan for a later slot (euclidean floor first) — only if a concrete Task-1/explanation variant is ready.

---

## 8. Suggested first commands (after reading)

```text
# Confirm scored artifact
conda run -n base --no-capture-output python -c "from src.pipeline_parquet import resolve_default_universe, load_universe_codes; print(resolve_default_universe('20260713')); import pandas as pd; u=set(load_universe_codes('samples/B_board/stock_sample_20260714.xlsx')); p=pd.read_csv('outputs/20260713/predict_result.csv',encoding='utf-8-sig'); print(len(p), set(p.stock_code)==u, p.transaction_date.unique())"

# Rebuild feature matrix + Euclid silhouette of submitted pattern_type (label-free)
# (implement scratch audit; delete after writing triage note)
```

Compare silhouette / pattern mix / explanation specificity against at least one **good** day (0701 or 0702) and one **collapse** day (0626 or 0629) if those outputs+parquet still available.

---

## 9. One-line success criterion

You can explain, with evidence, whether **0.2411 is (A) a Board-B-specific fixable issue (esp. explanations / Task-1), (B) another hard-key day, or (C) mixed** — and the human has a clear, §3.3-safe next move for the following submit day.
