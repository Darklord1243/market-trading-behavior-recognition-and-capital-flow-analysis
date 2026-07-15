# Competition Clarifications — FAQ & Submission Instructions

> **Source:** Platform notices and FAQ screenshots (not part of the main “Baseline Guide” or “Score Improvement Tutorial” body text).  
> **Precedence:** Where this conflicts with Baseline documentation, **this file takes precedence**.  
> **Board B ops (window / WMA / calendar):** see [`b-board-rules.en.md`](./b-board-rules.en.md) (authoritative from **2026-07-13**).

---

## 1. Result Notification and Submission Instructions

> **Scope:** The “18:00 → next-day 08:00” text below is the **A-board** instant-feedback window.  
> **Board B uses a new window:** predictions for trading day **T** must be submitted between **T+1 15:00 and T+2 14:59** (see [`b-board-rules.en.md`](./b-board-rules.en.md) §2).  
> The rule that `transaction_date` = the **predicted** trading day is **unchanged**.

**【结果通知及提交说明】 / [Result Notification and Submission Instructions]** (A-board original, retained for history)

Due to the T+1 data lag, we will update yesterday’s answers at around 18:00 each evening. After the answers are updated, you may upload yesterday’s prediction results after the answer update and before 08:00 the following day. You will then be able to see an instant score, which you can also use to verify your results. Please note that the current score is not the final result.

**Note:** The format of `transaction_date` must be yesterday’s date; otherwise an error will occur.

### Project implications

| Point | Detail |
|-------|--------|
| Evaluation cadence | Data lag: same-day ground truth unavailable; submit answers for the sample’s trading day |
| A-board instant window (historical) | Answers ~**18:00** → upload before **08:00** next day |
| **Board B submit window (current)** | **T+1 15:00 – T+2 14:59**; samples day T 10:00–12:00; answers day T 16:00–18:00 |
| Instant score | Sanity check only — **not the final result** (final = 9-day WMA) |
| `transaction_date` | Must be the **predicted trading day** — `dt` string (e.g. `20260713`), not snapshot epoch `date` |

---

## 2. Q&A on `pattern_type`

**Q3:** Besides the 10 types provided in the submission sample, can `pattern_type` be supplemented according to the actual situation? Is the submission sample only an example?

**A3:** Contestants may label freely, with no limit on the number of labels. We will ultimately score based on the rationality and interpretability of your labels.

### Project implications

| Point | Detail |
|-------|--------|
| Label vocabulary | **Fully open** — not limited to the sample’s ~10 types or Baseline’s 8 types |
| Scoring emphasis | **Rationality and interpretability** of `pattern_type` and `pattern_explanation` |
| Baseline | Fixed 8 patterns + hard-coded thresholds are a starting point only |
| Recommended strategy | Let clustering pick K in a bounded range (e.g. 6–12), then assign finance-grounded Chinese labels and explanations |

---

## 3. Frequently Asked Questions (FAQ)

| Common Questions | Answers |
|------------------|---------|
| There is only one stock in the training data—shouldn’t there be 100? | The sample set indeed contains only one. For details, please read the competition document again: https://tianchi.aliyun.com/competition/entrance/532489 |
| For the stock samples, does the organizer only provide stock names, and do contestants obtain the detailed data on their own? | Yes. Contestants may obtain detailed data through public channels. The stock sample file can be downloaded at the top of the 【Competition & Data】 section on the left side of the competition page: https://tianchi.aliyun.com/competition/entrance/532489/information |
| The data obtained using an API does not match the competition fields. Must it correspond exactly to the fields required by the competition, or is it sufficient as long as it is L2 data? | The competition problem has no reference fields—only feature-set references. It does not need to correspond exactly to the fields required by the competition. |
| Is the data in the official submission sample from the real market? | The sample uses random labels and is provided only as an upload reference for contestants. |

> Original FAQ text reads 「L2数据」 (Level-2 data). If a screenshot shows 「LR」, it should be read as Level-2 in competition context.  
> The four rows above **duplicate** Board B Q&A; §6 does not repeat them — cross-link only.

### Project implications

| Point | Detail |
|-------|--------|
| Sample training file | `AFAC2026-training-data.xlsx` = **1 stock × 1 day** — expected |
| Full universe | Download stock list from Tianchi 【Competition & Data】; **source L2 detail data yourself** |
| Input schema | **No need** to match the sample Excel’s 65 columns exactly — align to the official **7 feature families** |
| Submission sample CSVs | Labels in `pattern_reco` / `predict_result` are **random placeholders** — do not use for training or tuning |

---

## 4. How this relates to other guidance files

| File | What this document adds |
|------|-------------------------|
| [`b-board-rules.en.md`](./b-board-rules.en.md) | **Board B authority:** submit window, best-of-day, 9-day WMA, calendar cutoffs |
| `跑通Baseline.md` / `baseline-guide.md` | Submission loop, `transaction_date`, open `pattern_type`, self-sourced data, invalid sample labels (Baseline 2-class wording is stale) |
| `提分教程.md` / `score-improvement-tutorial.md` | Optimization paths unchanged; labeling / interpretability follow §2 and §6 |
| [`../report/b-board-submit-runbook.md`](../report/b-board-submit-runbook.md) | Daily operator checklist |

---

## 5. Pre-submission checklist

- [ ] `transaction_date` = predicted trading day `dt`, not UTC-ms `date`
- [ ] Inside the **Board B submit window** (T+1 15:00 – T+2 14:59); see [`b-board-rules.en.md`](./b-board-rules.en.md)
- [ ] Each `pattern_type` has a defensible `pattern_explanation` (**scored on Board B**)
- [ ] `capital_type` ∈ `{游资, 量化, 散户}` (bare `量化`; never `量化机构`)
- [ ] Submission sample CSV labels were not used for supervised training
- [ ] No look-ahead in prediction (history OK for training; non-L2 OK if not future)
- [ ] `submit.zip` contains both CSVs, UTF-8-sig encoding, no nested folders

---

## 6. Board B Q&A addendum (official — deduplicated)

> Source: AFAC2026 Track 1 Board B official Q&A. Items already covered in §2 / §3 are pointers only.

### 6.1 Submission & fields (existing → see §3)

| Question | Handling |
|----------|----------|
| Must API fields match the competition schema exactly? | **Existing** — §3: no need for 1:1 column match; align feature families |
| Are submission-sample labels from the real market? | **Existing** — §3: random labels, format only |
| Must every row fill `pattern_explanation`? Can it be blank? | **Board B new:** interpretability encouraged; not scored on A-board; **scored on Board B** → practically **fill a grounded explanation for every stock** |

### 6.2 Label rules

#### Capital attributes

| Question | Answer |
|----------|--------|
| Is `capital_type` two classes (游资/量化) or three including 散户? | **Three classes: 游资 / 量化 / 散户** (bare `量化`; matches `config.CAPITAL_TYPES`) |
| Must Task-1 labels stay within the sample set? | `capital_type` must be 「游资/量化/散户」 or submit errors; **cluster labels unrestricted** |
| Is `capital_intention` limited to 买入/卖出/中性, or is T0 allowed? | **Content unrestricted**; scoring uses **weighted F1 on `capital_type`**; `capital_intention` is **interpretability only** |

#### Trading patterns

| Question | Answer |
|----------|--------|
| Must `pattern_type` use only the ~10 sample types? | **Existing** — §2: free labels, no count limit |
| Is clustering scored vs official answer labels or contestants’ own? | **Contestants’ own cluster labels**; interpretability assessed; content unrestricted |

### 6.3 Data & model use

| Question | Answer |
|----------|--------|
| Inference only same-day Level-2? | **No restriction** |
| May use non–Level-2 data? | **Yes**, as long as prediction uses **no future information** |
| What does “no future function” mean? | Features must not contain future-period info; training may use historical days (e.g. for global norms) |
| Multi-day history for training? | **Training data use unrestricted** (not limited to single-day train+infer) |
| Different intraday regimes — how to pick the dominant behavior? | Produce one final prediction from intraday HF data; a dominant side exists; judgment is contestant’s |
| Does same-day submit predict the *next* day? | Predict labels for the **sample’s trading day** from that day’s L2; lag + window mean you submit the **prior trading day’s** answers (not “forecast tomorrow”) |

### 6.4 Scoring logic

| Question | Answer |
|----------|--------|
| What are market-phase / Task-1 separation & cohesion based on? | Submitted **cluster labels**: same label → cohesion; different labels → separation |
| Does Task 1 score only `pattern_type`? Does `pattern_explanation` count? | A-board does not score `pattern_explanation`; **Board B includes it in interpretability** |

### Project implications (§6)

| Point | Detail |
|-------|--------|
| Task 2 F1 | Optimize `capital_type` 3-class; still emit intention, but official F1 is not intention-primary |
| Task 1 | Custom `pattern_type` + **strong** `pattern_explanation` (Board B scored) |
| Data | Multi-day train + non-L2 auxiliaries OK; no look-ahead at inference |
| Ops calendar / WMA | [`b-board-rules.en.md`](./b-board-rules.en.md) — do not use the A-board 08:00 window |
