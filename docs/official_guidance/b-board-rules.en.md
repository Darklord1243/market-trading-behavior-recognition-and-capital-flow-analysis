# AFAC2026 Track 1 — Board B Rules (Official Update)

> **Status:** Active Board B operating rules (from **2026-07-13**).  
> **Chinese source:** [`b-board-rules.zh.md`](./b-board-rules.zh.md)  
> **Related FAQ:** [`competition-clarifications.md`](./competition-clarifications.md) §6 (Board B addendum)  
> **Precedence:** The Board B table in [`../competition-spec/topic-specifications-and-data.en.md`](../competition-spec/topic-specifications-and-data.en.md) §5.1 is an earlier paste — **this file wins**. The A-board instant-feedback window (18:00 → next-day 08:00) does **not** apply to Board B.

---

## 1. Competition basics

| Item | Detail |
|------|--------|
| Event | AFAC2026 Track 1 **Board B** |
| Underlying data | Live market data **2026/07/10 – 2026/07/23** |
| Board B period | **2026-07-13 – 2026-07-24 17:00** |
| Final evaluation cutoff | **2026-07-24 15:00** |
| Last scored trading day | **2026-07-22** |
| Sample updates | **No new stock samples on 2026-07-24** |
| Results | Tentatively **2026-07-28** — final Board B scores and ranking |

---

## 2. Submission rules

### 2.1 Frequency

- Each team **must submit at least once** per trading day
- At most **3** submissions per day
- Teams with fewer than **8** submitted trading days are **excluded from the final ranking**

### 2.2 Timing and day mapping (T = the trading day being scored)

| Event | When | Meaning |
|-------|------|---------|
| Sample release | **Day T, 10:00–12:00** | Official releases the **100 rotating stocks for day T−1** |
| Official answers update | **Day T, after close, 16:00–18:00** | Answers for the **T−1** sample are published |
| **Submission window** | **Day T+1 15:00 – Day T+2 14:59** | Submit predictions for **trading day T** |
| Late | Outside that window | That trading day scores **0** automatically |

**Example (scored trading day T = 2026-07-13):**

1. Morning of **2026-07-14**: stock sample released (maps to T = 2026-07-13)
2. Contestants answer using **2026-07-13** real market data
3. Submit after answers update from **2026-07-14 15:00**, before **2026-07-15 14:59**
4. Late → **2026-07-13** day score = 0

> **Project implication — date pairing (critical):**
>
> | Concept | Example (Jul 14 upload) | Where it appears |
> |---------|-------------------------|------------------|
> | Sample **release** day | **2026-07-14** | When the file appears on the platform (day T morning) |
> | Predicted / L2 **trading** day (T−1) | **2026-07-13** | Filename `stock_sample_20260713.xlsx`; parquet `--date`; CSV `transaction_date` |
>
> On day T morning the organizer publishes the sample for day **T−1** — and since **2026-07-15 the filename uses that trading day T−1**, not the release day. Submitting on Jul 14 therefore uses **`stock_sample_20260713.xlsx` + parquet `20260713`**, with `transaction_date=20260713` — sample filename, `--date`, and `transaction_date` all carry the **same** day.
>
> Pipeline auto-resolve: `--date` = L2 day → universe = `stock_sample_{--date}.xlsx`.
>
> **History (pre-rename):** before 2026-07-15 the platform named samples by **release** day (`stock_sample_20260714.xlsx` held the 2026-07-13 universe), and pairing `stock_sample_20260713.xlsx` with `--date 20260713` was a platform reject (seen 2026-07-14). The repo's `samples/B_board/` files were renamed to trading-day stems on 2026-07-15; docs/commits earlier than that use the old convention.

Board B’s window is later/wider than the A-board FAQ’s “18:00 → next 08:00” — follow this section.

---

## 3. Scoring rules

1. **Daily score:** up to 3 uploads per day; keep the day’s **highest** score (not “latest”)
2. **Final score:** compute each trading day’s score, then aggregate with a **9-day linear weighted moving average (9-day WMA)**
3. **Weights:** nearer days weigh more — current day (day 9) weight **9**, then 8… down to earliest day weight **1**; denominator (sum of weights) = **45**
4. **Formula:**

$$
WMA_9 = \frac{9P_t + 8P_{t-1} + 7P_{t-2} + 6P_{t-3} + 5P_{t-4} + 4P_{t-5} + 3P_{t-6} + 2P_{t-7} + 1P_{t-8}}{45}
$$

5. **Score refresh cadence:** around **T+5**, rankings are updated through trading day T

---

## 4. Leaderboard & promotion

1. **Boards:** a daily time-limited board shows only that day’s **best single-day score**; the **final ranking** uses the **9-day WMA**
2. **Promotion:** Board B **TOP 15** undergo result replication and review. Organizers jointly consider model score, solution soundness, completeness, and reproducibility for final roadshow eligibility

---

## 5. Quick delta vs A-board / older docs

| Dimension | A-board / older paste | **Board B (this file)** |
|-----------|----------------------|-------------------------|
| Submit window | FAQ: ~18:00 → next 08:00; old spec: same-day 23:59 | **T+1 15:00 – T+2 14:59** |
| Multi-upload day | Older text often “latest wins” | **Best score of the day** |
| Final aggregate | Vague “moving weighted average” | **Explicit 9-day WMA (weights 9…1 / 45)** |
| Sample / eval cutoff | — | Last scored day **7/22**; eval cutoff **7/24 15:00**; no samples on 7/24 |
| `pattern_explanation` | Not scored on A-board | **Counted in Board B interpretability** (see FAQ §6) |

---

## 6. Doc index (for later agents)

| Document | Role |
|----------|------|
| This file / [`b-board-rules.zh.md`](./b-board-rules.zh.md) | Board B ops & scoring authority |
| [`competition-clarifications.md`](./competition-clarifications.md) | Labels / data / interpretability Q&A (incl. Board B addendum) |
| [`../report/b-board-submit-runbook.md`](../report/b-board-submit-runbook.md) | Daily submit operator checklist |
| [`../competition-spec/README.md`](../competition-spec/README.md) | Tianchi paste index + cross-refs |
| [`../LIS.md`](../LIS.md) | Implementation locks & executor entry |
