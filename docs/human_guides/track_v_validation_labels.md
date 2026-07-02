# Human Guide — Track V: seeding the offline validation labels

> **Goal:** hand-label a small set of `(stock, day)` rows with their true capital type, so we can compute an
> **offline proxy-F1** and know whether H1–H3 actually *help* — instead of only proving the scorer "responds"
> on synthetic panels. **You do the labeling; the pipeline never sees these labels at inference.**
>
> **Output file:** `tests/fixtures/validation_labels.csv` · **Spec:** LIS §6 *Track V* · **Compliance:** LIS §3.3 / §5.1

## 0. The compliance line (read first — this is what keeps us un-DQ'd)

| ✅ Allowed | ❌ Forbidden (auto-DQ, LIS §3.3) |
|---|---|
| Label from **public post-market info**: 龙虎榜, news, research notes, known-name priors | Copy labels from the **platform instant score / backtest answers** |
| Use those labels **offline only**, to score our own output | Feed validation labels into any **feature or the inference path** (LIS §3.1) |
| Store them in `tests/fixtures/` | Tune thresholds/weights to **maximize the leaderboard** |

§5.1 explicitly permits **post-market, non-real-time information for retrospective validation**. These are
**your** labels from public sources — not the board's answers. Keep them in `tests/fixtures/` and consume them
**only** with `src/validate.py` (the offline scorer). They must never touch `src/features.py` / `src/rules.py` /
`main.py`.

## 1. CSV schema (exact columns)

`tests/fixtures/validation_labels.csv` — UTF-8:

| Column | Meaning | Example |
|---|---|---|
| `stock_code` | with exchange suffix | `000001.SZ` |
| `transaction_date` | trading day `YYYYMMDD` | `20260611` |
| `capital_type` | one of `游资` / `量化` / `散户` (3-class; LIS §2 lock) | `游资` |
| `capital_intention` | `买入` / `卖出` / `T0交易` (optional; blank if unsure) | `买入` |
| `source` | URL or citation backing the label | `eastmoney lhb 2026-06-11` |
| `confidence` | `0.0`–`1.0`, **your honesty dial** (see §3) | `0.8` |
| `notes` | one line of reasoning | `华鑫宛平南路买一封板` |

Leave `capital_intention` blank rather than guess. Leave a whole row out rather than invent a `source`.

## 2. What each class looks like — and how reliably you can label it

| Class | Public signal you can cite | Reliability | Typical confidence |
|---|---|---|---|
| **游资** (hot money) | On **龙虎榜** with a **known hot-money 营业部 seat** as a top buyer (e.g. 华鑫证券上海宛平南路, 银河绍兴, 国君南京太平南路, 中信上海溪虹桥). Single-day surge / 涨停 / 连板. | **Highest** — 龙虎榜 names the seat | 0.6–0.9 |
| **量化** (quant) | **Rarely on 龙虎榜** (quants spread across the day, seldom trip single-seat thresholds). Cite: known **quant/index-arb/ETF-heavy** names, high intraday turnover + two-sided flow, broker notes naming 量化/高频. | **Medium-low** — indirect | 0.3–0.6 |
| **散户** (retail) | Low attention, low turnover, **not** on 龙虎榜, no institutional/seat footprint, diffuse all-day trading, retail-forum chatter. | **Lowest** — defined by absence | 0.2–0.5 |

> **Critical honesty point:** do **not** label `量化`/`散户` by eyeballing our own features (cancel rate,
> burst, CV). That is circular — you'd be "validating" the model against labels the model itself would produce.
> Label from **independent external evidence** (龙虎榜 seats, news, name priors) only.

## 3. Confidence guidance (it weights the proxy-F1)

- **0.8–0.9** — 龙虎榜 names a hot-money seat as the dominant top-buyer on that day → strong `游资`.
- **0.5–0.7** — solid news/research attribution, or seat present but not clearly dominant.
- **0.3–0.4** — name-prior only (e.g. "this is a known quant playground") with no day-specific evidence.
- **< 0.3** — a guess; better to omit the row. We weight/filter by `confidence`, so noisy low-confidence
  rows mostly hurt.

## 4. Where to search (public, free)

| Source | What it gives | URL |
|---|---|---|
| 东方财富 龙虎榜 | Daily 龙虎榜, per-stock seat detail (买/卖 top-5 营业部) | https://data.eastmoney.com/stock/lhb.html |
| 同花顺 龙虎榜 | Same, alt view | http://data.10jqka.com.cn/market/longhu/ |
| 新浪 龙虎榜 | Daily list | https://vip.stock.finance.sina.com.cn/q/go.php/vInvestConsult/kind/lhb/index.phtml |
| 东方财富个股资金流 | Intraday main-force net flow (corroboration) | https://data.eastmoney.com/zjlx/ |
| News / 研报 | "游资/主力/量化 active in X today" narratives | 东方财富股吧, 财联社, 雪球 |

**Reading 龙虎榜 seats:** `机构专用` = institution (公募/社保—**not** our `量化` class). Named retail-brokerage
营业部 that recur on speculative limit-ups = **游资**. Maintain a small personal list of hot-money seats as you go.

**Provisional — 机构 vs named 游资 dominance (20260626 batch):** when buy-top mixes net-buy-skewed `机构专用`
with a tier-2 seat (e.g. 华鑫绍兴胜利东路), compare **net-buy 万** on the same side. If named directional
seats **rival or exceed** the top-4 `机构专用` net-buy block → lean **游资** BORDERLINE (e.g. 300264: 华鑫+国信
+3339万 vs 机构 +2087万). If named seat net-buy is **&lt;~25%** of the top-4 `机构专用` net-buy block → stay
**量化** BORDERLINE (000100/002025 family; e.g. 002962: 华鑫 +1956万 vs 机构 +8422万 ≈ 23%). Use **exact**
sums in `notes` (audit-grade). Threshold is a **working hypothesis** — calibrate on future batches, not settled.

## 5. Recipe — seed ≥8 rows in ~30 minutes

1. Pick a labeling day we have data for: **`20260611`** or **`20260612`** (local corpus; see
   `docs/data_inventory_report.md`). Using these days lets us score the proxy on **real stock-days we can run**.
2. Open 东方财富 龙虎榜 for that date. Pull **4–6 clear `游资`** names where a known hot-money seat is the
   dominant buyer → rows with `confidence` 0.6–0.9, `source` = the lhb URL, `notes` = the seat.
3. Add **2–3 `量化`** candidates from name-priors / broker notes (`confidence` 0.3–0.6). Expect these to be weaker.
4. Add **1–2 `散户`** names: low-turnover, not on 龙虎榜, no footprint (`confidence` 0.2–0.4).
5. Fill `capital_intention` only when obvious (封板买入 → `买入`; clear distribution → `卖出`; else blank).
6. Save to `tests/fixtures/validation_labels.csv`. Commit (labels are public-sourced text, safe to commit).

A starter template with the header and a couple of clearly-marked **example** rows already exists at that path —
replace the examples with real, cited rows.

## 6. Honest limits (keep expectations calibrated)

- **Class-imbalanced & 游资-heavy.** 龙虎榜 over-represents hot-money big-movers; `量化`/`散户` are weakly
  attributable. The proxy's class mix ≠ the hidden T+5 truth's. It is a **smoke detector, not a leaderboard
  simulator**: trust a **big regression**, discount a **small win** as noise.
- **Seat-present ≠ whole-day dominance.** A hot-money seat in the top-5 doesn't mean it drove every tick — hence `confidence`.
- **Does not resolve class-set questions.** (OQ-1 is already resolved: eval is **3-class** per the organizer.)
- **Small N.** Start at ~8 rows; grow opportunistically. Ten good cited rows beat fifty guesses.

## 7. What happens next (engineering, not your job)

Once `src/validate.py` exists (Track V V.1–V.2 — needs **no** labels to build) and this CSV has rows, each
H1/H2/H3 PR reports **proxy-F1 before/after** on your seed set, alongside the synthetic-panel assertion. A change
that moves the synthetic panel but **not** the proxy gets flagged before we trust it.
