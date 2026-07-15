# Board B 20260713 — score 0.2411 triage (read-only)

**Status:** COMPLETE · diagnosis only · **no code / config / rules / label change**  
**Date:** 2026-07-14 · Instant score **0.2411** logged 2026-07-14 22:22:23  
**Artifact:** `outputs/20260713/submit.zip` (generated ~22:20)  
**Compliance:** LIS §3.3 — board number used for verification only; no threshold/weight tuning to 0.2411.  
**Audit script:** `scratchpad/b0713_score_triage_audit.py` (session scratch; safe to delete)  
**Related:** `score-boost-direction-20260704.md`, `hard-key-case-control-20260706.md`, `p0626-score-collapse-triage.md`, `b-board-rules.en.md`, `competition-clarifications.md` §6
**Naming note:** written pre-rename — `stock_sample_20260714.xlsx` below is the old release-day name of the **20260713**-universe file (renamed `stock_sample_20260713.xlsx` on 2026-07-15; see `b-board-rules.en.md` §2.2).

---

## TL;DR — verdict

**0.2411 is (C) mixed: most consistent with a hard-key / Task-2 key day on a new rotating Board-B panel, with a plausible additive Board-B interpretability drag — not a submission defect and not a Task-1 geometry failure.**

| What we can rule out | What remains open |
|----------------------|-------------------|
| Zip / date / universe / format bugs (H0 **PASS**) | Exact Task-1 vs Task-2 split of the 0.2411 |
| Unusually weak Euclidean cluster geometry (H2 **rejected**) | Whether `pattern_explanation` templates are the *extra* drag below the ~0.33 A-collapse floor |
| Obvious capital-class skew (36/33/31) | Offline Task-2 F1 on 0713 names (no labels) |

**Do not** thrash `rules.py` / thresholds / `TASK1_METHOD` for this day. **Do** keep daily submits alive. Prefer a §3.3-safe explanation-quality explore on a later best-of-day slot if human approves.

---

## Evidence summary

### Offline comparison table (submitted `pattern_type` silhouette on 31-col Euclidean finance matrix)

| day | board | sil_pat | CH | n_pat | top_share | 游资 | 量化 | 散户 | T0 | 卖出 | 买入 |
|-----|-------|---------|-----|-------|-----------|------|------|------|-----|------|------|
| **20260713** | **0.2411** | **0.1384** | **17.3** | 5 | **0.27** | 0.36 | 0.31 | 0.33 | 0.62 | 0.31 | 0.07 |
| 20260626 | 0.3265 | 0.0975 | 14.0 | 4 | 0.43 | 0.42 | 0.30 | 0.28 | 0.63 | 0.21 | 0.16 |
| 20260629 | 0.3333 | 0.0383 | 9.3 | 4 | 0.64 | 0.42 | 0.28 | 0.30 | 0.66 | 0.03 | 0.31 |
| 20260701† | 0.5245 | 0.0922 | 11.8 | 5 | 0.55 | 0.48 | 0.22 | 0.30 | 0.59 | 0.03 | 0.38 |
| 20260702 | 0.5566 | 0.1352 | 15.5 | 4 | 0.52 | 0.41 | 0.30 | 0.29 | 0.70 | 0.10 | 0.20 |

† Euclidean backup labels (`pattern_reco_euclidean_backup.csv`) — the pack that scored 0.5245.

**Decisive geometric fact:** 0713 silhouette / CH are **at or above** the best A-board day (0702), and clearly **better** than both A-collapse days. Geometry alone cannot explain dropping below the prior ~0.33 floor.

### Explanation template audit

| day | board | unique_expl | tpl share (“显著高于市场均值”) | len med |
|-----|-------|-------------|-------------------------------|---------|
| 20260713 | 0.2411 | 6 | **0.80** | 53 |
| 20260701 | 0.5245 | 9 | 0.45 | 53 |
| 20260702 | 0.5566 | 6 | 0.48 | 53 |
| 20260626 | 0.3265 | 6 | 0.57 | 52 |
| 20260629 | 0.3333 | 8 | 0.36 | 53 |

Same `_SUBSTR_LEXICON` templates as A-board. 0713 is **more** feature-attributed (fewer `机构长线配置` fallbacks: 20 vs ~55% on 0701), not less diverse than 0702 (both 6 unique strings). So “0713 explanations uniquely worse than our good A days” is **not** supported by diversity metrics — but A never scored explanations, so A history cannot clear the new Board-B channel.

### Universe / labels

- B sample ∩ A-list = **9 / 100** (rotating panel; rules transfer unvalidated on most names).
- `validation_labels.csv`: **0** rows for `20260713`; any-date labeled ∩ 0713 universe = **2** codes (`603318.SH`, `603379.SH`) — no usable offline F1.

---

## H0–H5 verdict table

| ID | Hypothesis | Verdict | Evidence |
|----|------------|---------|----------|
| **H0** | Submission integrity failure | **Rejected (PASS)** | Zip = 2 root CSVs; UTF-8-sig; 100/100; `transaction_date=20260713`; codes == `stock_sample_20260714.xlsx`; reject-list codes absent; zip ≡ disk; `TASK1_METHOD=euclidean` |
| **H1** | Board-B interpretability / `pattern_explanation` channel collapsed | **Inconclusive as sole cause; supported as new risk surface** | Official: explanations **scored on B, not A**. Ours remain ~50-char templates. Diversity does **not** show 0713 uniquely worse than 0.52+ A days (same lexicon; even higher template share). Can explain *additive* drag vs A-collapse floor, not the whole 0.24 alone without a controlled B A/B |
| **H2** | Task-1 Euclidean geometry weak on rotating panel | **Rejected** | sil_pat **0.1384** (best in set), CH **17.3** (best), 5 non-degenerate patterns, top_share 0.27 (least degenerate). Collapse days had *worse* geometry and *higher* board scores |
| **H3** | Task-2 `capital_type` mismatch on new B names | **Inconclusive** | Cap mix healthy 36/33/31; no 0713 labels; 9/100 A-overlap only. Cannot compute weighted F1. Intention T0=62% is interpretability-only on B (FAQ §6) — do not chase first |
| **H4** | Hard-key / answer-key day (unfixable offline) | **Supported as primary residual** | Same playbook as 0626/0629/hard-key case-control: H0–H2 find no fixable defect; offline mix/geometry do not separate bad board days. 0.2411 **below** prior A floor → treat as hard-key **plus** possible B-rule delta (H1), not pure copy of A-collapse |
| **H5** | Wrong scoring mental model | **Rejected (model holds)** | Still believe Total ≈ **0.4·Task1 + 0.6·Task2**. B Q&A: cluster scored on **contestant’s own labels** (cohesion/separation); F1 on **`capital_type`**; intention interpretability-only; explanations in Task-1 interpretability on B |

---

## Classification vs success criterion

| Option | Fit |
|--------|-----|
| **(A) Board-B-specific fixable defect** | Partial only — explanation templates are a **real new scored channel** and are fixable without §3.3, but evidence does **not** prove they alone caused 0.2411 |
| **(B) Another hard-key day** | Strong residual after H0–H2; consistent with A-board hard-key case-control (no offline signature) |
| **(C) Mixed** | **Best fit** — hard-key / Task-2 key on new panel **+** possible B interpretability drag; no integrity/geometry bug |

Back-of-envelope (illustrative only, not tuning): holding Task-1 geometry “good” (~A mid) while Task-2 collapses harder on a new key, and/or Task-1 interpretability haircut, can land near ~0.24 under 40/60 weights. We **cannot** identify which sub-channel without organizer detail or a controlled paired upload.

---

## Ranked next actions (max 3) — await human OK before implementing

### 1. Stock-grounded `pattern_explanation` upgrade (recommended explore)

| | |
|--|--|
| **What** | Keep `pattern_type` / clusters / Task-2 unchanged; rewrite explanations to cite **per-stock** dominant features + magnitudes (not only cluster-centroid template), avoid identical 53-char clones across many rows |
| **Offline test** | Pre-submit audit: unique_expl ↑, length variance ↑, name↔feat coherence checklist; silhouette of `pattern_type` must stay ≈ current (labels unchanged) |
| **§3.3 risk** | **Low** — interpretability quality, not threshold search against 0.2411 |
| **Day-score lever** | Board-B Task-1 interpretability channel (new vs A). Expected magnitude unknown; paired best-of-day can bound it |
| **Paired plan** | Floor = current euclidean zip; Explore = same predict_result + richer pattern_reco explanations only |

### 2. Do nothing to rules / method — ship next day on euclidean floor

| | |
|--|--|
| **What** | Next trading day: auto universe resolve + `TASK1_METHOD=euclidean` + full 100 rows; do **not** flip dtw; do **not** retune `rules.py` |
| **Offline test** | Runbook pre-flight only |
| **§3.3 risk** | **None** |
| **Day-score lever** | Avoids 0 from a missed day under 9-day WMA (miss ≫ weak day) |

### 3. Track-V style LHB labels on Board-B names (when post-market seats exist)

| | |
|--|--|
| **What** | Append public LHB/news labels for B-universe codes into `validation_labels.csv` for **offline** capital_type F1 — diagnosis only |
| **Offline test** | Weighted F1 on labeled subset; no rule change from a single bad day |
| **§3.3 risk** | **Low** if labels are public post-market and not platform answers; **high** if used to chase board F1 |
| **Day-score lever** | Indirect — only helps if it later justifies a principled feature/rule change on **internal** metrics |

---

## Explicit non-actions (binding unless human overrides)

- Do **not** change `rules.py` / thresholds / weights to chase 0.2411.
- Do **not** switch scored-day floor to `dtw-complete` (0701 paired A/B: dtw **hurt** board).
- Do **not** treat intention mix (T0 62%) as the primary Board-B F1 lever.
- Do **not** revert `resolve_default_universe` / Board-B date-pairing docs.

---

## Optional paired best-of-day explore (later slot)

Only if action **#1** is approved and a concrete explanation variant is ready:

1. Generate **A (floor):** production euclidean as today.  
2. Generate **B (explore):** identical `predict_result.csv`; `pattern_reco` with upgraded explanations only.  
3. Upload both inside the Board-B window; platform keeps **best-of-day**.  
4. Log both instant scores as verification; if B ≥ A, promote explanation path; if B ≪ A, revert and document.

---

## One-line success criterion (met)

**0.2411 is mixed (C): format-valid submit with healthy Task-1 geometry; residual looks like hard-key / Task-2 on a new rotating panel, with Board-B explanation scoring as a plausible additive (not proven sole) drag. Next move: keep euclidean daily floor; optionally A/B richer explanations — no rule thrash.**
