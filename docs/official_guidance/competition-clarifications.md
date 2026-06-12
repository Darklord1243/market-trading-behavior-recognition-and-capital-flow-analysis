# Competition Clarifications — FAQ & Submission Instructions

> **Source:** Platform notices and FAQ screenshots (not part of the main “Baseline Guide” or “Score Improvement Tutorial” body text).  
> **Precedence:** Where this conflicts with Baseline documentation, **this file takes precedence**.

---

## 1. Result Notification and Submission Instructions

**【结果通知及提交说明】 / [Result Notification and Submission Instructions]**

Due to the T+1 data lag, we will update yesterday’s answers at around 18:00 each evening. After the answers are updated, you may upload yesterday’s prediction results after the answer update and before 08:00 the following day. You will then be able to see an instant score, which you can also use to verify your results. Please note that the current score is not the final result.

**Note:** The format of `transaction_date` must be yesterday’s date; otherwise an error will occur.

### Project implications

| Point | Detail |
|-------|--------|
| Evaluation cadence | T+1 — same-day ground truth is not available |
| Instant-feedback window | Answers posted ~**18:00** → upload yesterday’s predictions before **08:00** next day |
| Instant score | For sanity checks only — **not the final result** |
| `transaction_date` | Must be the **predicted trading day (yesterday)** — use `dt` as string (e.g. `20260507`), not snapshot epoch `date` |

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
| `跑通Baseline.md` / `baseline-guide.md` | A-board submission loop, `transaction_date` = yesterday, open `pattern_type`, self-sourced data, invalid sample labels |
| `提分教程.md` / `score-improvement-tutorial.md` | Optimization paths unchanged; labeling strategy should follow Section 2 above |

---

## 5. Pre-submission checklist

- [ ] `transaction_date` = trading day `dt` (yesterday), not UTC-ms `date`
- [ ] Each `pattern_type` has a defensible `pattern_explanation`
- [ ] Submission sample CSV labels were not used for supervised training
- [ ] Features use intraday-available data only (no look-ahead)
- [ ] `submit.zip` contains both CSVs, UTF-8-sig encoding, no nested folders
