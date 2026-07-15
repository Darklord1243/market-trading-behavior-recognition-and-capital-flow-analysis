# Track 1 — Topic Specifications & Data

**AFAC2026 Challenge Group — Track 1: Market Participant Trading Behavior Recognition and Capital Flow Analysis**

> **Source:** Tianchi 【赛题与数据】page, reorganized from web copy-paste.  
> **中文:** [`topic-specifications-and-data.zh.md`](./topic-specifications-and-data.zh.md)  
> **Feature table:** [`reference-feature-set.md`](./reference-feature-set.md) (89 fields)

---

## I. Task introduction

In stock investment, large-scale trading by market participants (public mutual funds, quantitative private equity, hot money, etc.) significantly impacts prices; capital flow is a crucial market indicator. Ordinary investors face two pain points with public Level-2 data, Dragon-Tiger lists, or simple net-flow indicators:

1. **Information fragmentation** — a single indicator (e.g. large-order net buy) cannot reconstruct true intent (accumulation, driving price, unloading). Institutions hide actions via order splitting, wash trading, etc.
2. **Interpretation lag** — most flow indicators are daily; intraday dynamics are missed; by the time a signal is clear, price has often moved.

This track builds a systematic solution for **market participant trading behavior recognition and capital flow analysis**: combine tick execution data, order-book microstructure, and fundamentals to parse behaviors and flows from high-frequency data — capital attributes (hot money / quant / retail), intent (accumulation, testing, wash trading, pull-up, unloading), and readable analysis (who dominates, buy or sell, true intent).

---

## II. Task objectives

Build a complete methodology on A-share **tick orders, tick trades, tick cancellations, and 10-level snapshots** (data may be sourced via Taobao, Xianyu, Baidu Netdisk, etc.). Fine-grained distinction between **hot money and quantitative funds**; identify trading direction and intent. Methods are open; LLMs + classical quant encouraged.

**Daily output for hot money / quant funds:**

1. Dominant participant type + confidence
2. Buy / sell / neutral directional intention + confidence

> **Label note:** English spec uses "neutral"; worked examples and baseline code use **`T0交易`**. Submitted CSVs must use Chinese: `游资`, `量化机构`, `买入`, `卖出`, `T0交易`.

---

## III. Task data

Participants obtain Level-2 A-share data independently. Organizers provide a **reference feature set** (field list only — see [`reference-feature-set.md`](./reference-feature-set.md)) for model design.

### 3.1 Reference feature set

89 fields in 7 families (rs, cb, oss, ap, obp, pd, pi) plus window metadata. **Not shipped as a downloadable table** — compute from raw L2.

---

## IV. Dataset composition

### 4.1 Data samples

Download reference materials from the top of the competition details page (see repo `samples/`).

### 4.2 Data distribution (preliminary round)

| Dataset | Stocks | Period |
|---------|--------|--------|
| Sample set 1 | 20 | 2026/05/07 |
| Test set A | 100 | 2026/06/08 — 2026/07/10 |
| Test set B | 100 | 2026/07/13 — 2026/07/24 |

---

## V. Task rules & submission

### 5.1 Data & scoring cadence

- Submissions on day **T** are validated over the **next 3 trading days**; rankings published around **T+5**
- Only the **latest** solution is evaluated; multiple updates are scored via **time-series tracking** (moving weighted average of daily scores)
- **Post-market non-real-time information** (news, social media) may be used to retrospectively verify/correct modeling — but **final predictions must be derived from intraday high-frequency data only**

#### A-board

| Rule | Detail |
|------|--------|
| Period | 2026/06/09 — 2026/07/10 |
| Data | Live market data for same period |
| Submissions | **Up to 3 per day**; only the **latest** counts (e.g. 17:00, 18:00, 19:00 → 19:00 used) |
| Deadline | Submit before **23:59** on each trading day; miss → **0 for the day** |
| Final A deadline | **July 10 (Fri) 23:59**; A-board results published **July 13** |
| Scoring | Moving weighted average of daily scores |

> **Ops note (A-board):** Platform FAQ historically added instant-feedback **~18:00 → 08:00**.  
> **Do not use that window for Board B** — see [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md).

#### B-board

| Rule | Detail |
|------|--------|
| Period | 2026/07/13 — 2026/07/24 17:00 |
| Underlying data | 2026/07/10 — 2026/07/23 |
| Submissions | **At least once** per trading day; **up to 3** per day |
| Submit window | **T+1 15:00 – T+2 14:59** (late → day score 0) |
| Minimum days | **Fewer than 8 trading days → excluded from final ranking** |
| Daily aggregation | **Best** score of the day (not latest) |
| Scoring | **9-day WMA** (weights 9…1, denom 45); refresh ~T+5 |
| Eval cutoff | **2026-07-24 15:00**; last scored trading day **2026-07-22**; **no new samples on 2026-07-24** |
| Results | Tentatively **2026/07/28** |
| Audit | **Top 15** replication audit for roadshow eligibility |

> **Authoritative detail (window example, WMA formula, vs A-board):** [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md). Table above is a summary; that file wins on conflict.

> **Chinese spec adds:** valid A-board result required to enter B-board.

### 5.2 Task requirements

**Task 1 — Trading pattern recognition**

- Cluster trading patterns from data features
- Metrics: inter-cluster separation + intra-cluster cohesion
- Distance: **Wasserstein + DTW**

**Task 2 — Pattern classification & capital type recognition**

- Output recognition for **two participant types** (hot money / quant)
- Metric: **weighted F1**

### 5.3 A/B-board scoring

```
Total score = (Task 1 score × 0.4) + (Task 2 score × 0.6)
```

All evaluation uses latest real market data. Task 2 F1 components include participant type, directional intent, and (per spec wording) market-phase recognition — all via F1. Standard definitions:

- **Precision** P = TP / (TP + FP)
- **Recall** R = TP / (TP + FN)
- **F1** = 2PR / (P + R) × 100%

> See [README cross-reference notes](./README.md) on the "market phase" wording vs our two CSV outputs.

### 5.4 Submission files

#### A-board

Daily `submit.zip` containing `pattern_reco.csv` + `predict_result.csv`. Final deadline **July 10, 23:59**.

**`pattern_reco.csv`** — exactly 4 columns, fixed order:

| stock_code | transaction_date | pattern_type | pattern_explanation |
|------------|------------------|--------------|---------------------|
| stock1 | 20260710 | Large Order Accumulation | Capital buys via large pending orders |
| … | … | … | … |

**`predict_result.csv`** — exactly 4 columns, fixed order:

| stock_code | transaction_date | capital_type | capital_intention |
|------------|------------------|--------------|-------------------|
| stock1 | 20260710 | 游资 | 买入 |
| stock2 | 20260615 | 游资 | 卖出 |
| stockN | 20260715 | 量化机构 | T0交易 |

> Examples above mix English pattern names (illustrative) with **Chinese** capital labels (required). See project brief §3.

#### B-board

Same format and naming as A-board; **both files required daily**.

#### Report phase (B-board top 15)

Submit **July 28 — August 5**:

| File | Content |
|------|---------|
| `project_solution_report.docx` | Methodology, system design, features, modeling, evaluation |
| `project_solution.zip` | Full reproducible Python code matching the report |

### 5.5 Code review

Top 15 B-board teams submit complete Python code (preprocessing → features → train → predict).

| Requirement | Detail |
|-------------|--------|
| Dependencies | Declared in `init_env.sh` |
| Entry point | `main.py` → writes `predict_result.csv` |
| Hard-coding ban | No random fill, no per-stock-code rules, no ignoring L2 features |
| Timing | Results must be producible from intraday data by market close |
| Paths | Relative (e.g. `../data/XX`); thorough comments |
| Audit | Full pipeline replication; code/doc/result mismatch → disqualification |

---

## VI. Shortlisting

B-board top 15 notified by committee must submit on time. Violations or non-submission → disqualification; spots filled from Tianchi leaderboard.

---

## VII. Task example

Illustrative scenario (stock codes in examples are **not** the sample fixture).

### 7.1 Overall approach

From four raw streams (order, trade, cancel, snapshot), use statistics, feature engineering, ML, or rules to profile daily behavior:

- Execution rhythm, order-size distribution, cancellation, price impact
- Order-book microstructure for order/cancel strategy differences
- Snapshot dynamics for buy/sell power shifts
- Secondary modeling on the reference feature set

### 7.2 Case 1 — "Shrinking Volume Game" (precision manufacturing stock)

> **This is the official anchor cited in the project brief (competition spec §7.2).**

![Case 1 illustration from Tianchi spec §7.2](./assets/7.2-case-1.png)

*Official spec screenshot (恒工精密 intraday chart, 2026-04-28). Illustrative — the narrative below uses a generic precision-manufacturing scenario; stock codes in §7 are not the repo fixture (603997.SH).*

**Market background:** A precision manufacturing stock retraced >30% from highs, entered low-volume consolidation. One day: ~200M RMB turnover (extremely light), Doji candlestick — looked ignored, but Level-2 told a different story.

**Tick-by-tick observation:**

| Signal | Detail |
|--------|--------|
| Order volume | ~2,300 entrustments, ~1.26B RMB declared value |
| Execution | ~350M RMB actually traded |
| Cancellation | **~70% of orders cancelled** — not an "ignored" day |
| Rhythm split | Some intervals **CV ~24ms** (machine/algorithmic); others manual — intermittent large orders held long |
| Cancel timing | Some cancelled within seconds (depth testing); others survived minutes, pulled before opponent price shifts |
| Behavior tags | **Iceberg splitting** (large orders into small batches); **aggressive selling** (wiping multiple bid levels) |
| Time distribution | **>70% of orders** at open and close; sparse midday |

---

## VIII. Notes

1. Comply with laws, privacy, IP
2. Active interaction encouraged
3. Winning solutions may be shared publicly (with consent) after competition
4. Cheating → immediate disqualification
5. Organizers hold final interpretation
6. Join official DingTalk Q&A group (QR on Tianchi page)
