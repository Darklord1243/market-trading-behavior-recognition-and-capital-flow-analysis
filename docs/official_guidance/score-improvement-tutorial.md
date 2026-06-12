# Score Improvement Tutorial | Track 1: Market Participant Trading Behavior Recognition and Capital Flow Analysis

> Reorganized from official competition guidance. Structured for reference and implementation.

---

## Table of Contents

1. [Discussion: How to Optimize the Baseline](#1-discussion-how-to-optimize-the-baseline)
2. [Actionable Score-Improvement Paths](#2-actionable-score-improvement-paths)
3. [Appendix: Supplementary Knowledge](#3-appendix-supplementary-knowledge)
4. [References](#4-references)

---

## 1. Discussion: How to Optimize the Baseline

### 1.1 Optimization Directions Overview

#### Feature Engineering (Highest Priority, Best ROI)

**Order-Book Microstructure Features**

| Direction | Description |
|-----------|-------------|
| Order Flow Imbalance (OFI) | Compute changes in bid/ask resting volume between consecutive snapshots—a well-established strong feature in academic literature. Formula: `OFI = Δbid_volume - Δask_volume` |
| Depth-Weighted Price | Compute volume-weighted average bid/ask prices using order-book depth—more precise than simple best bid-ask spread |
| Spread Dynamics | Mean, standard deviation, and rate of change of the bid-ask spread—reflects liquidity shifts |
| `bidaskrate` / `bidaskdifference` | Both fields are 0 in the current training data, but may have values on the A/B leaderboards—extract as features when available |

**Time-Series Features**

- Rolling-window statistics: mean, standard deviation, and trend slope over the past N snapshots
- Autocorrelation features: autocorrelation coefficients of price and volume

**Volume-Price Relationship Features**

- Volume-price divergence: price rises while volume falls, or vice versa
- VWAP deviation: deviation of current price from volume-weighted average price

**Cancellation Behavior Features (currently zero due to missing cancel data in snapshots)**

- When tick-by-tick cancel data is available, add cancel rate, fast-cancel ratio, coefficient of variation of cancel intervals, etc.

#### Model Optimization

**Task 1 Clustering**

- Try density/probabilistic clustering methods such as DBSCAN, HDBSCAN, and GMM
- Replace Euclidean distance with DTW or Wasserstein distance to better align with competition evaluation metrics
- Build TimeSeriesKMeans on time series (DTW-based)

**Task 2 Classification**

- Introduce gradient boosting models (XGBoost, LightGBM, CatBoost) to replace pure rule-based scoring
- Build pseudo-labels from clustering outputs and train supervised classifiers
- Multi-task learning: jointly predict participant type and trading intention with shared representations

#### Pseudo-Label / Rule Quality Improvement

- Current rules are based on financial domain priors—thresholds can be further refined and quantified
- Use A-leaderboard F1 feedback to tune rule thresholds in reverse
- Semi-supervised learning: a small labeled set plus a large unlabeled set, improved via self-training

#### External Data Integration

- **Fundamental data**: market cap, sector, PE/PB, etc.—participant structure may differ across industries
- **Multi-day historical data**: build richer training sets from multi-day Level-2 data
- **News/sentiment data**: the competition permits post-market, non-real-time information for post-hoc validation and correction

#### Multi-Stock Generalization

The current training data contains only 1 stock; the A/B leaderboards have 100 stocks. Consider:

- Feature distribution differences across market caps and sectors
- Market-cap/sector neutralization of features
- Cross-stock pattern consistency when clustering

---

## 2. Actionable Score-Improvement Paths

> Ordered by difficulty and expected payoff, from easier to harder.

### Path 1: Order-Book Microstructure Features

**Core Idea**

The current Baseline uses only first-snapshot order-book features (`spread` / `book_imbalance`) and full-day aggregates. Order Flow Imbalance (OFI) is a well-established strong feature in microstructure research.

**Implementation**

```python
# In extract_all_feature, compute OFI for each snapshot
# OFI = (bid_volume_t - bid_volume_t-1) - (ask_volume_t - ask_volume_t-1)
# Positive → bid-side resting volume increasing, buy pressure building
# Negative → ask-side resting volume increasing, sell pressure building

group['ofi'] = (group['totalbidvolume'].diff() - group['totalaskvolume'].diff())
feature['ofi_mean'] = group['ofi'].mean()
feature['ofi_std'] = group['ofi'].std()
feature['ofi_positive_ratio'] = (group['ofi'] > 0).sum() / len(group)
```

**Why It Works**

OFI captures the direction of *new resting orders*. During speculative hot-money rallies, large buy orders are repeatedly posted to attract followers—OFI stays positive. During quantitative T+0 arbitrage, bid and ask orders alternate—OFI oscillates near zero.

---

### Path 2: Cancellation Behavior Features

**Core Idea**

CB features are all zero in the current Baseline because snapshot data lacks cancel details. If tick-by-tick cancel data is available (the competition dataset may include it), cancellation behavior is among the most effective features for distinguishing hot-money traders from quantitative institutions.

**Implementation**

```python
# Assume a cancels table with cancel_time, cancel_volume, cancel_direction
# Fast-cancel ratio: share of orders canceled within 1 second of placement
fast_cancel = cancels[cancels['cancel_interval_ms'] < 1000]
feature['cb_fast_cancel_ratio'] = len(fast_cancel) / len(cancels)

# Buy/sell cancel divergence
feature['cb_buy_cancel_ratio'] = len(cancels[cancels['direction'] == 'buy']) / len(cancels)
feature['cb_sell_cancel_ratio'] = len(cancels[cancels['direction'] == 'sell']) / len(cancels)

# Cancel amount as share of total tick amount
feature['cb_cancel_amount_ratio'] = cancels['cancel_amount'].sum() / total_tick_amount
```

**Why It Works**

Quantitative institutions frequently place and cancel orders to probe market depth—their fast-cancel rate is far higher than hot-money traders, who cancel less and trade with execution intent.

---

### Path 3: XGBoost / LightGBM Instead of Rule-Based Scoring

**Core Idea**

Task 2 currently uses pure rule-based scoring, which is subjective. Use clustering labels as pseudo-labels to train a supervised model.

**Implementation**

```python
from xgboost import XGBClassifier

# Step 1: Generate pseudo-labels from current rules
df_feature['pseudo_label'] = df_feature.apply(calc_score, axis=1)

# Step 2: Train XGBoost classifier
X = df_feature[all_feature_cols].values
y = (df_feature['pseudo_label'] == '游资').astype(int)

model = XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    random_state=42
)
model.fit(X, y)

# Step 3: Predict with probability calibration
proba = model.predict_proba(X)[:, 1]
df['capital_type'] = np.where(proba > 0.5, '游资', '量化机构')
```

> **Note**: Submission CSV values must remain the exact Chinese strings `游资` and `量化机构` per competition requirements.

**Why It Works**

XGBoost learns nonlinear feature interactions automatically—more flexible than hand-crafted rules—and outputs probabilities for confidence assessment.

---

### Path 4: Dynamic Threshold Optimization

**Core Idea**

Clustering pattern-matching thresholds are hard-coded (e.g., `oss_mega_amount_pct > 0.12`). Grid search or Bayesian optimization can find better thresholds.

**Implementation**

```python
# 1. Collect candidate conditions for each pattern
# 2. Search each condition in [0.05, 0.50] with step 0.01
# 3. Select the threshold combination that maximizes silhouette score

best_thresholds = {}
for threshold in np.arange(0.05, 0.50, 0.01):
    # Re-match patterns with updated threshold
    # Compute silhouette score
    # Record best threshold
```

**Why It Works**

Fixed thresholds perform inconsistently across stocks; data-driven search adapts automatically.

---

### Path 5: Time-Series Modeling

**Core Idea**

The current approach aggregates full-day data into a single sample, losing temporal structure. Try LSTM or Transformer models directly on snapshot sequences.

**Implementation**

```python
# Feed daily snapshot sequences (N × feature_dim) into LSTM/Transformer
# Output: participant type + trading intention
# Requires substantial training data (many stocks × many days)
```

**Why It Works**

Sequence models capture dynamic behavior evolution (e.g., "accumulate first, then pump") that static aggregates cannot.

---

### Path 6: Large Language Model (LLM) Solutions

**Core Idea**

Leverage LLMs (GPT-4, Claude, DeepSeek, Qwen, etc.) for semantic understanding, reasoning, and code generation across multiple dimensions. LLMs excel at financial domain logic, feature-engineering code generation, and multi-dimensional reasoning.

#### 6.1 LLM-Assisted Feature Engineering

Have the LLM analyze field semantics and recommend/generate feature code.

```python
prompt = """
You are a quantitative finance expert. Below is a field list for A-share Level-2 snapshot data:
- symbol: stock code
- price: last traded price
- volume: cumulative daily volume (diff required for per-tick volume)
- amount: cumulative daily turnover
- bids: 10-level bid JSON (fields: price, volume)
- asks: 10-level ask JSON
- totalbidvolume: total bid resting volume
- totalaskvolume: total ask resting volume
- weightedbidprice: volume-weighted bid price
- weightedaskprice: volume-weighted ask price
- bigordervolume: large-order traded volume
- changepercent: price change percent
- rangepercent: intraday range percent
- ...

Task: Recommend 20 features that effectively distinguish 「游资」(hot-money traders)
from 「量化机构」(quantitative institutions), with Python implementation for each.
Requirements:
1. Features must be based on Level-2 microstructure
2. Explain why each feature separates hot-money from quantitative behavior
3. Cover order-book dynamics, order flow, and cancellation behavior
"""
```

**Why It Works**: LLMs draw on broad financial literature and can infer feature combinations analysts might miss—wider coverage and higher efficiency than manual design.

#### 6.2 LLM-Assisted Pattern Interpretation and Report Generation

Use LLM text generation to produce financial semantic explanations for clusters and draft solution reports.

```python
prompt = """
Trading features for one stock on one trading day:
- Mega-order turnover share: 51%
- Large-order turnover share: 31.7%
- Active buy share: 70.9%
- Time concentration: 31.8%
- Order-book imbalance: 0.0
- Price volatility: 1.9%
- Price impact: 13.1

Analyze:
1. Which trading pattern best matches? Choose one:
   游资强势连板拉升, 量化高频T0套利, 尾盘资金突袭, 主力分批吸筹,
   日内均衡T0套利, 对倒洗盘, 散户零散交易, 机构长线配置
2. Provide a detailed explanation within 200 Chinese characters
3. Determine whether hot-money or quantitative capital dominates, with reasoning
"""
```

**Advanced use—batch report generation**: Feed architecture, feature list, and model design to the LLM to draft `project_solution_report.docx`.

**Why It Works**: The written solution report accounts for 20% of the final score—LLM drafting frees time for model optimization.

#### 6.3 LLM-Assisted Rule Threshold Optimization

Have the LLM provide financially grounded threshold recommendations and sensitivity analysis for multi-condition pattern matching.

**Why It Works**: LLMs can suggest market-cap-differentiated thresholds with microstructure theory backing—more principled than naive grid search.

#### 6.4 Multi-Agent Pipeline (Agent-Based Workflow)

Build specialized LLM agents for feature engineering, model building, evaluation/diagnosis, and report writing, orchestrated end-to-end.

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                        │
│         (task allocation, result aggregation, flow control)  │
└───────┬──────────────┬──────────────┬──────────────┬────────┘
        ▼              ▼              ▼              ▼
 Feature Engineer   Model Builder   Eval Analyst   Report Writer
     Agent              Agent           Agent          Agent
```

**Why It Works**: Decomposes complex work into specialized subtasks—well suited for finance AI competitions requiring multi-domain expertise.

#### 6.5 LLM Fine-Tuning

If labeled training data is available (or sufficient pseudo-labels via self-training), fine-tune open-source LLMs (Qwen, DeepSeek) for dedicated trading-behavior analysis.

**Why It Works**: Fine-tuned models output structured financial analysis—participant type, intention, and rationale—improving report quality and interpretability.

**Recommended Strategy**

Start with lower-effort paths (feature engineering assistance, pattern explanation/report generation). After gaining experience and data, advance to multi-agent pipelines and LLM fine-tuning.

---

## 3. Appendix: Supplementary Knowledge

### Appendix A: Hot-Money Traders vs. Quantitative Institutions

> The original document listed this section by title only. See Baseline rule design and competition materials for concrete behavioral contrasts.

### Appendix B: Common Trading Patterns

Eight patterns defined in the Baseline:

| Pattern (Chinese) | English Meaning |
|-------------------|-----------------|
| 游资强势连板拉升 | Aggressive hot-money limit-up rally |
| 量化高频T0套利 | High-frequency quantitative T+0 arbitrage |
| 尾盘资金突袭 | End-of-day capital surge |
| 主力分批吸筹 | Main-force phased accumulation |
| 日内均衡T0套利 | Balanced intraday T+0 arbitrage |
| 对倒洗盘 | Matched-order wash trading |
| 散户零散交易 | Fragmented retail trading |
| 机构长线配置 | Institutional long-term allocation (default fallback) |

### Appendix C: Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **Silhouette Score** | Clustering quality in [-1, 1]; closer to 1 is better. Combines intra-cluster cohesion and inter-cluster separation |
| **Calinski-Harabasz (CH) Index** | Variance ratio criterion; higher is better |
| **Davies-Bouldin (DB) Index** | Inter-cluster similarity; lower is better |
| **Weighted F1 Score** | `F1 = 2 × Precision × Recall / (Precision + Recall)`; weighted version accounts for class imbalance |
| **Wasserstein Distance** | "Earth mover's distance" between distributions; sensitive to financial distribution shifts |
| **DTW (Dynamic Time Warping)** | Time-series similarity with elastic time alignment |

### Appendix D: Feature Category Quick Reference

Official reference feature sets (7 categories; Baseline extends to 8):

| Code | Full Name | Core Content |
|------|-----------|--------------|
| OSS | Order Size Segmentation | Mega/large/mid/small order amount and count shares |
| RS | Order Rhythm / Sequence | Inter-trade interval CV, split-order similarity, burst ratio |
| CB | Cancel Behavior | Fast-cancel ratio, buy/sell cancel divergence, cancel-interval CV |
| AP | Active Participation | Active buy/sell share, consecutive trade runs, unilateral intensity |
| OBP | Order Book Profile | Best-level quotes, spread, order-book imbalance |
| PD | Price Discovery | Price impact, execution efficiency |
| PI | Period Intraday | Open/close session turnover share, time concentration, price volatility |
| TRD | Tick Trade Structure | Average trade size, size dispersion, large-order share (Baseline extension) |

---

## 4. References

1. [scikit-learn — KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
2. [scikit-learn — Clustering performance evaluation](https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation)
3. [XGBoost documentation](https://xgboost.readthedocs.io/)
4. Dynamic Time Warping algorithm references
5. [Python official tutorial (Simplified Chinese)](https://docs.python.org/zh-cn/3/tutorial/)
6. Liao Xuefeng's Python tutorial
7. [Microsoft AutoGen multi-agent framework](https://github.com/microsoft/autogen)
8. pocketflow agent development framework
9. A-share Level-2 market data API practical guide
10. Level-2 data is more than tick + 10-level book: four hard dimensions for extracting main-force order behavior in A-shares
11. A-share market microstructure tools: from order-book data to quantitative trading decisions
12. Using AI to analyze order-book microstructure, detect iceberg orders, and identify main-force capital flows
