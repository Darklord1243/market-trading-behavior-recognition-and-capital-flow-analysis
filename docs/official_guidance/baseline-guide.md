# Baseline Guide | Track 1: Market Participant Trading Behavior Recognition and Capital Flow Analysis

> Reorganized from official competition guidance. Structured as: competition brief → modeling approach → Baseline implementation → run instructions.  
> **Platform clarifications** (open `pattern_type` labels, A-board submission loop, `transaction_date` format, self-sourced data, invalid sample labels, etc.) see [`competition-clarifications.md`](./competition-clarifications.md).

---

## Table of Contents

**Part I: Competition Brief**

1. [Project Overview](#1-project-overview)
2. [Task Description](#2-task-description)
3. [Data and Dataset Composition](#3-data-and-dataset-composition)
4. [Rules and Submission](#4-rules-and-submission)

**Part II: Problem Modeling**

5. [Core Competition Analysis](#5-core-competition-analysis)
6. [Layered Task Breakdown](#6-layered-task-breakdown)
7. [Development Recommendations](#7-development-recommendations)
8. [Problem-Solving Workflow](#8-problem-solving-workflow)

**Part III: Baseline Solution**

9. [Baseline Architecture and Code](#9-baseline-architecture-and-code)
10. [Core Code Walkthrough](#10-core-code-walkthrough)
11. [Run Instructions](#11-run-instructions)
12. [Design Rationale and Core Logic](#12-design-rationale-and-core-logic)

---

# Part I: Competition Brief

## 1. Project Overview

### Competition Background

This track asks participants to build a systematic solution for **market participant trading behavior recognition and capital flow analysis**. The solution must combine tick-by-tick trade data, order-book microstructure features, and stock fundamentals to automatically parse buy/sell behavior and capital flows from massive high-frequency data, and infer underlying intent—for example:

- Identifying order capital attributes (hot-money traders / quantitative private funds / retail investors, etc.)
- Analyzing capital intent (accumulation, market probing, matched-order wash trading, rally pumping, distribution/exiting, etc.)
- Producing clear, interpretable capital flow analysis (who dominates, buy or sell, and the true intent)

A successful solution helps investors see through complex order flow, follow institutional capital more rationally, improve timing, and reduce the risk of being misled by hot-money activity or spoofed orders—moving from "gut-feel herding" to **data-informed auxiliary decisions**.

In equity investing, large buy/sell activity by market participants (public funds, quantitative private funds, hot-money traders, etc.) often moves prices significantly; their capital flows are treated as important market signals. Yet retail investors face two major pain points with Level-2 data:

| Pain Point | Description |
|------------|-------------|
| **Fragmented information** | A single indicator rarely reconstructs true accumulation, pumping, or distribution intent—institutions often hide actions via order splitting and matched trading |
| **Delayed interpretation** | Most capital-flow indicators are daily aggregates; intraday dynamics are missed, and by the time a signal is clear, price has often already moved far from an ideal entry |

**Plain-language example**: As a retail investor, you see a stock suddenly surge on heavy volume. You need to know—is this hot money pumping toward a limit-up exit, or a quant fund running programmatic T+0 arbitrage? If the former, you might follow; if the latter, you might avoid. This competition trains AI to answer that question automatically.

Participants use four full Level-2 data types for A-share stocks—tick orders, tick trades, tick cancellations, and 10-level order-book snapshots—to build a complete methodology that finely separates **hot-money (游资)** and **quantitative institution (量化机构)** capital, identifies buy/sell direction and trading intent, and outputs actionable pattern recognition and capital flow analysis.

---

## 2. Task Description

The track has two core tasks. All outputs must strictly match the prescribed format and will be evaluated via **T+5 live-market backtesting** on the platform.

### Task 1: Trading Pattern Recognition (Unsupervised Clustering)

| Item | Content |
|------|---------|
| **Objective** | Cluster single-stock, single-day trading behavior using full Level-2 features; produce distinguishable, interpretable pattern types with business explanations |
| **Requirements** | Clusters must show high intra-cluster cohesion and high inter-cluster separation; pattern explanations must align with real A-share trading logic without business errors |
| **Output file** | `pattern_reco.csv` — exactly 4 fields in fixed order: `stock_code`, `transaction_date`, `pattern_type`, `pattern_explanation` |
| **Labeling note** | **`pattern_type` is fully open—no fixed count.** Scoring emphasizes label rationality and `pattern_explanation` interpretability. The Baseline below defaults to **k=8** with **8 built-in candidate names** as a reference implementation only, not a mandatory enum. See [`competition-clarifications.md`](./competition-clarifications.md). |

### Task 2: Capital Type and Trading Intent Recognition (Rule-Based Discrimination Without Ground Truth)

| Item | Content |
|------|---------|
| **Objective** | Identify the dominant capital type for a single stock on a single day and determine core trading intent from Level-2 features |
| **Requirements** | Capital type must be exactly **游资** or **量化机构**; trading intent must be exactly **买入**, **卖出**, or **T0交易** |
| **Output file** | `predict_result.csv` — exactly 4 fields in fixed order: `stock_code`, `transaction_date`, `capital_type`, `capital_intention` |

> **Terminology note for English readers**
>
> | Chinese (submission value) | Recommended English meaning |
> |----------------------------|----------------------------|
> | 游资 | Hot-money / speculative capital traders |
> | 量化机构 | Quantitative institutions |
> | 买入 | Buy (net accumulation intent) |
> | 卖出 | Sell (net distribution intent) |
> | T0交易 | T+0 / intraday round-trip trading |

---

## 3. Data and Dataset Composition

### Raw Data Fields

The official **sample** training file contains **65 core fields** across four dimensions:

- Tick orders
- Tick trades
- Tick cancellations
- 10-level order-book snapshots

> **Data sourcing note:** The sample set is **1 stock × 1 day** only. The full stock list and L2 detail data must be obtained by contestants via public channels. Self-sourced API data **need not** match the sample’s 65 column names—align to the **7 feature families** below. See [`competition-clarifications.md`](./competition-clarifications.md).

### Official Reference Feature Sets

The competition provides **7 standardized reference feature categories**. All features are computed from intraday-available data only—**no look-ahead bias**.

| # | Category | Description |
|---|----------|-------------|
| 1 | **OSS** — Order Size Segmentation | Mega/large/mid/small order amount and count shares; hot-money baseline shares, etc. |
| 2 | **RS** — Order Sequence / Rhythm | Inter-trade interval CV, split-order similarity, order burst ratio, buy/sell interval divergence, etc. |
| 3 | **CB** — Cancel Behavior | Fast-cancel ratio, buy/sell cancel divergence, cancel-interval CV, etc. |
| 4 | **AP** — Active Participation | Active buy/sell share, consecutive trade runs, unilateral intensity, net active share, etc. |
| 5 | **OBP** — Order Book Profile | Best-level quotes, spread crossing, quote offset, order-book imbalance, etc. |
| 6 | **PD** — Price Discovery | Multi-dimensional price impact, book imbalance, execution efficiency, etc. |
| 7 | **PI** — Period Intraday | First-30-min / last-10-min turnover share, Herfindahl concentration, price volatility, etc. |

---

## 4. Rules and Submission

### Submission Format

- Package results as `submit.zip` containing `pattern_reco.csv` and `predict_result.csv` — **no nested folders**
- Field order and names must match exactly—no adding, removing, or renaming fields
- `capital_type`: only `游资` or `量化机构`
- `capital_intention`: only `买入`, `卖出`, or `T0交易`
- All results must use **intraday-available data only** — no look-ahead
- Encoding: **UTF-8-sig**; no blank lines; no missing values
- A-board instant feedback: `transaction_date` must be **yesterday’s trading day**; answers update ~18:00 daily; upload before 08:00 next day for an instant (non-final) score. See [`competition-clarifications.md`](./competition-clarifications.md).

### Scoring

**Total A/B score = Pattern recognition score × 0.4 + Participant recognition score × 0.6**

#### Task 1 — Trading Pattern Recognition (40%)

Evaluated on silhouette score, CH index, Wasserstein distance, and DTW time-series distance:

| Metric | Description |
|--------|-------------|
| Silhouette score | Intra-cluster cohesion and inter-cluster separation; range [-1, 1], closer to 1 is better |
| CH index | Ratio of between-cluster to within-cluster variance; higher is better |
| Wasserstein distance | Distribution difference across trading patterns; larger means better separation |
| DTW distance | Time-series difference across trading behaviors; larger means better separation |

#### Task 2 — Capital Type Recognition (60%)

Weighted F1-Score against **T+5 live-market backtest labels**:

| Metric | Description |
|--------|-------------|
| Weighted F1-Score | Core classification metric; closer to 1 is better |
| Precision | Among samples predicted as class X, share truly class X |
| Recall | Among samples truly class X, share correctly predicted |

### Compliance Requirements (Hard Rules)

1. **No look-ahead / future data**: Features, models, and rules may use only intraday Level-2 data—never post-close or future-session data
2. **No hard-coded per-stock labels**: Rules must generalize; no fixed labels for specific stocks or dates
3. **No platform evaluation labels in training**: T+5 backtest labels are for online scoring only—using them in training or rule tuning disqualifies results
4. **Reproducibility**: Top 15 on leaderboard B must submit full code reproducible by reviewers, consistent with the written report

---

# Part II: Problem Modeling

## 5. Core Competition Analysis

### Context

This is a specialized finance-AI competition on full Level-2 high-frequency data, addressing the industry pain point that institutional capital behavior in A-shares is opaque and hard for retail investors to penetrate. Participants may obtain tick order/trade/cancel and 10-level snapshot data through various channels (as noted in official materials). Technical approach is not mandated—LLMs and classical quant methods are both encouraged.

### Problem Nature

The core problem is **unsupervised financial time-series mining and behavior recognition**, decomposed into two coupled sub-problems:

1. **Task 1 — Unsupervised clustering**: No labels; cluster single-stock single-day behavior from high-dimensional Level-2 time-series features; maximize cohesion/separation and assign interpretable business meaning to each cluster
2. **Task 2 — Rule-based discrimination without ground truth**: No official training labels; build multi-dimensional scoring rules from A-share industry conventions to separate hot-money vs. quantitative capital and infer trading intent; maximize alignment with live-market behavior

**Key challenges**

- High-dimensional, noisy Level-2 data—extract features strongly linked to institutional behavior
- Institutions hide intent via splitting, matched trading, and spoofing—penetrate to true capital attributes
- No labels—cannot rely on standard supervised ML; solutions must be financially grounded, unsupervised/rule-based, and interpretable

### Baseline Technical Framework

Four layers, end-to-end, no look-ahead, unsupervised/rule-based:

```
Raw Level-2 input (tick trades / orders / cancels / 10-level book)
        ↓
Preprocessing: cleaning, time normalization, JSON book parsing, outlier filtering, temporal sorting
        ↓
Feature engineering: official 7-category features + derived book features → per (stock, day) matrix
        ↓
Modeling
    ├ Task 1: KMeans (default k=8) → cluster profiles → multi-condition `pattern_type` mapping (8 built-in candidates)
    └ Task 2: 11-dim normalized multi-factor scoring → capital type + joint book/active-trade intent rules
        ↓
Output: format validation, null handling, UTF-8-sig encoding → two CSV files
```

---

## 6. Layered Task Breakdown

### Layer ① Data Understanding

| Item | Content |
|------|---------|
| **Goal** | Understand Level-2 snapshot structure and field semantics |
| **Actions** | Learn all 65 fields; parse `bids`/`asks` JSON for depth and large-order shares |
| **Finding 1** | `volume`/`amount`/`transactions`/`bigordervolume` are **cumulative intraday values**—use `diff()` for per-tick increments |
| **Finding 2** | `date` is UTC epoch milliseconds—`.dt.hour` gives UTC hours (0–8). **`hh` is Beijing time hour (8–16)**—must use `hh` for session windows |
| **Finding 3** | `bigordervolume`, `changepercent`, `rangepercent` are directly usable—no need to recompute |

### Layer ② Feature Engineering

| Item | Content |
|------|---------|
| **Goal** | Extract discriminative features for behavior and capital flow |
| **Actions** | Cumulative-to-tick conversion; OSS tiering; TRD structure; RS rhythm; AP active trade; PI intraday sessions; PD price discovery; OBP from first snapshot JSON (Plan A) and full-day aggregates (Plan B) |

### Layer ③ Model Building

| Item | Content |
|------|---------|
| **Task 1** | KMeans (Baseline default **k=8**, dynamic downgrade when samples are few); multi-condition matching (≥3 conditions) maps to **8 built-in candidate** `pattern_type` labels (competition permits custom labels) |
| **Task 2** | 11-dimension weighted scoring; intent from dual-source book imbalance + active trade rules |

### Layer ④ Output

| Item | Content |
|------|---------|
| **Files** | `pattern_reco.csv`, `predict_result.csv` |
| **Validation** | Field order, allowed label values |
| **Submit** | `submit.zip` |

---

## 7. Development Recommendations

1. **Start simple**: Run Baseline first; understand data flow before optimizing
2. **Prioritize feature engineering**: Microstructure features (OFI, spread dynamics, large-order impact) matter most
3. **Cumulative → tick**: Misusing cumulative `volume`/`amount` breaks OSS tiering
4. **Timezone trap**: Use `hh` (Beijing hour), not UTC hour from `date`
5. **Rule quality**: Task 2 has no labels—financial plausibility of rules drives performance
6. **Reproducibility**: Fixed random seed, relative paths, clear comments
7. **Use existing fields**: `changepercent`, `rangepercent`, `bigordervolume` are often best used as-is

---

## 8. Problem-Solving Workflow

### Step 1: Read the brief carefully

Clarify task boundaries, output constraints, compliance rules, and CSV format.

### Step 2: Explore data

Inspect 65 fields; parse `bids`/`asks` JSON; confirm minimal sample unit is **(stock_code, transaction_date)**; study distributions and outliers.

### Step 3: Decompose and select approaches

Preprocessing pipeline; official 7-category features + book derivatives; KMeans + multi-condition naming for Task 1; multi-factor scoring for Task 2; joint rules for intent.

### Step 4: Implement end-to-end

Preprocess → features → Task 1 → Task 2 → CSV output with format checks.

### Step 5: Evaluate and iterate

Tune clustering (k, features, distance); tune scoring weights and thresholds; refine features and pattern/intent rules.

### Step 6: Package for submission

Clean code structure; written report; final CSV validation; `submit.zip`.

---

# Part III: Baseline Solution

## 9. Baseline Architecture and Code

**Pipeline**: Feature engineering (8 categories, 56 dimensions) → KMeans (Task 1) + multi-factor scoring (Task 2)

**Run**

```bash
python main.py
python main.py --input data.xlsx
python main.py --input "data/*.xlsx" -o out/
```

**Outputs**: `pattern_reco.csv`, `predict_result.csv`

---

## 10. Core Code Walkthrough

Five modules: data processing, feature extraction, model training, prediction, offline evaluation.

### Data Processing — `load_and_preprocess()`

```python
def load_and_preprocess():
    df = pd.read_excel(INPUT_PATH, engine='openpyxl')
    df['transaction_date'] = df['dt'].astype(str)
    df['datetime'] = pd.to_datetime(df['date'], unit='ms')
    df['hour'] = df['hh']  # Beijing hour for PI intraday features
    df['minute'] = df['datetime'].dt.minute
    df = df.rename(columns={'symbol': 'stock_code'})
    df = df[(df['price'] > 0) & (df['volume'] >= 0) & (df['amount'] >= 0)]
    df = df.sort_values(by=['stock_code', 'transaction_date', 'datetime'])
    return df
```

**Critical timezone note**

- `date` → UTC milliseconds
- **`hour` must be `df['hh']` (Beijing)**, not `df['datetime'].dt.hour` (UTC 0–8)
- Beijing session 9:30–15:00 will never match PI windows if UTC hours are used → PI features become all zeros
- `minute` from `datetime` is fine (consistent 8-hour offset)
- After sorting, `volume` is monotonic—`diff()` yields correct tick increments

### Feature Extraction

**Cumulative to tick**

```python
group['tick_volume'] = group['volume'].diff().fillna(0).clip(lower=0)
group['tick_amount'] = group['amount'].diff().fillna(0).clip(lower=0)
```

**OSS tiering (share thresholds)**

- Mega: ≥ 50,000 shares
- Large: ≥ 10,000 and < 50,000
- Mid: ≥ 1,000 and < 10,000
- Small: < 1,000

**AP active trade** — infer aggressor side from price changes:

```python
group['price_change'] = group['price'].diff()
active_buy_amt = group.loc[group['price_change'] > 0, 'tick_amount'].sum()
active_sell_amt = group.loc[group['price_change'] < 0, 'tick_amount'].sum()
feature['ap_active_buy_pct'] = active_buy_amt / (active_buy_amt + active_sell_amt)
```

**PI intraday (Beijing `hh`)**

```python
open_30min = group[
    ((group['hour'] == 9) & (group['minute'] >= 30)) |
    ((group['hour'] == 10) & (group['minute'] == 0))
]
close_10min = group[(group['hour'] == 14) & (group['minute'] >= 50)]
feature['pi_time_concentration'] = (
    open_30min['tick_amount'].sum() + close_10min['tick_amount'].sum()
) / total_tick_amount
```

**OBP — dual approach**

- Plan A: first-snapshot `bids`/`asks` JSON → spread, `book_imbalance`, large-quote shares
- Plan B: full-day `totalbidvolume`/`totalaskvolume` statistics

### Model Training

**Task 1 — KMeans + multi-condition matching**

- Dynamic cluster count: `min(N_CLUSTERS, n_samples)`
- Pattern assigned only if ≥3 conditions match; else fallback `机构长线配置`
- The 8 candidate names and thresholds are Baseline defaults only; contestants may define their own `pattern_type` vocabulary per [`competition-clarifications.md`](./competition-clarifications.md).

Example conditions for hot-money limit-up rally pattern:

- `oss_mega_amount_pct > 0.12`
- `book_imbalance > 0.2`
- `ap_active_buy_pct > 0.55`
- `pi_time_concentration > 0.3`

**Task 2 — 11-dimension scoring**

Dimensions cover OSS, RS, CB, AP, OBP, PD, PI, consecutive buys, book large orders, sell cancels, unilateral intensity.

Hot-money-leaning dimension indices: `{0, 3, 5, 6}` (large size, active buy, impact, time concentration).

```python
return '游资' if score_yz >= score_qt else '量化机构'
```

### Prediction — Intent Rules

```python
def get_intention(row):
    buy_pct = row.get('ap_active_buy_pct', 0.5)
    sell_pct = row.get('ap_active_sell_pct', 0.5)
    imbalance = 0.4 * row.get('book_imbalance', 0) + 0.6 * row.get('obp_imbalance_mean', 0)

    if buy_pct > 0.6 and imbalance > 0.08:
        return '买入'
    elif sell_pct > 0.6 and imbalance < -0.08:
        return '卖出'
    else:
        return 'T0交易'
```

Weighted blend: first snapshot (0.4) + full-day mean (0.6) for stabler all-day buy/sell balance.

### Offline Evaluation

```python
sil_score = silhouette_score(X_scaled, df_feature['cluster_id'])
ch_score = calinski_harabasz_score(X_scaled, df_feature['cluster_id'])
db_score = davies_bouldin_score(X_scaled, df_feature['cluster_id'])

assert df_result['capital_type'].isin(['游资', '量化机构']).all()
assert df_result['capital_intention'].isin(['买入', '卖出', 'T0交易']).all()
```

---

## 11. Run Instructions

### Environment

- Python >= 3.8
- pandas, numpy, scikit-learn, openpyxl

```bash
python3 -m pip install pandas numpy scikit-learn openpyxl
python main.py
```

### Expected Console Output (sample training data)

```
【1/5】数据预处理开始
预处理完成 | 有效数据行数: 4937 | 覆盖股票数: 1
【2/5】全量特征提取开始
特征提取完成 | 总特征数: 52 维 | 总样本数: 1
【3/5】Task1 交易模式聚类开始
>>> 样本数 (1) < 预设聚类数 (8)，动态调整为 1
交易模式分布: 游资强势连板拉升    1
【4/5】Task2 资金与意图识别开始
资金类型分布: 游资    1
交易意图分布: T0交易    1
【5/5】结果保存与离线评估开始
所有流程完成！
```

**Note**: Sample training data = 1 stock × 1 day → 1 sample → clusters downgrade to 1. A/B leaderboards have 100 stocks × multiple days → Baseline **default k=8** runs with full metrics when samples allow. Final `pattern_type` labeling strategy: [`competition-clarifications.md`](./competition-clarifications.md).

### Output Files

| File | Fields |
|------|--------|
| `pattern_reco.csv` | `stock_code`, `transaction_date`, `pattern_type`, `pattern_explanation` |
| `predict_result.csv` | `stock_code`, `transaction_date`, `capital_type`, `capital_intention` |

---

## 12. Design Rationale and Core Logic

### Design Principles — "Features first, rules before models, simple before complex"

1. **Cumulative → tick** before OSS and turnover stats
2. **Beijing `hh`** for session features
3. **Eight feature families** aligned with official reference sets
4. **Financial priors** in rules (hot money aggressive, quant balanced)
5. **≥3-condition matching** for Task 1 patterns
6. **Dual-source intent signals** (snapshot + full-day book imbalance)
7. **Robust edge cases**: dynamic cluster count, null/inf handling, label validation

### Core Logic Summary

| Layer | Logic |
|-------|-------|
| Data safety | Intraday-only; no look-ahead; no hard-coded labels |
| Task 1 | Math clustering → cluster profiles → multi-condition `pattern_type` mapping (8 Baseline candidates; open vocabulary per platform FAQ) |
| Task 2 | 11-dim normalized scoring; hot money = large/active/imbalanced; quant = small/frequent/balanced |
| Cross-task | Task 1 clusters can sanity-check Task 2 capital type |
| Interpretability | Every feature, rule, and pattern has financial rationale—no black box |
