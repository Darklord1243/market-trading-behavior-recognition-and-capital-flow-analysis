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
- **Batch log.** `20260701`: +16 rows (游资 6 / 量化 6 / 散户 4; `capital_intention` 买入 8 / T0交易 5 /
  卖出 1 / blank 2), all sourced from 东方财富龙虎榜 per-stock pages. CSV total now **n=138** across
  10 labeling days (20260616–20260701). Parquet corpus `data/202607` verified for 20260701 (all 5 streams;
  `snapshot_20260701.parquet` present, 76 cols / 22.3M rows). Combined multi-root offline gate (dates
  `<20260701` → `data/202606`, `20260701` → `data/202607`): capital **FULL n=138 0.6627**, through-0629
  **0.6438 / n=122** (floor held, byte-identical), 0701-only **0.8006 / n=16**; intention **FULL n=129 0.6638**,
  through-0629 **0.6750 / n=115** (floor held, byte-identical), 0701-only **0.5595 / n=14** (2 blank intention).
- **Batch log.** `20260702`: +16 rows (游资 6 / 量化 6 / 散户 4; `capital_intention` 买入 8 / T0交易 6 /
  卖出 1 / blank 1), all sourced from 东方财富龙虎榜 per-stock pages (`scripts/lhb_0702_audit_report.md`).
  CSV total now **n=154** across 11 labeling days (20260616–20260702). Parquet corpus `data/202607`
  verified for 20260702 (`snapshot_20260702.parquet` present under `十盘档口/20260702/`).
- **Batch log.** `20260715`: +3 rows (游资 2 @0.75/0.60 both 买入 / 量化 1 @0.38 blank), dual-executor dig
  (Cursor + Sonnet) audited per auditor guide §6; hit sets matched exactly (6/100 LHB hits — all-SH
  coverage collapse persists). Rejected: 688433.SH 游资 (one-labels-one-drops borderline; 中信上海溧阳路
  has no registry entry and no CSV precedent → fails §6.2(b)), 603949.SH (both agree: diffuse desks, no
  footprint). 605133.SH 量化 accepted over a Cursor drop via §6.2 borderline test (高盛世纪大道 desk-churn,
  audit-grade sums + 603466/603335 precedents). 600288.SH routed to institutional ledger (机构专用 buy-side
  one-directional into limit-down, first held case). Name-prior channel: 0 rows proposed by either executor
  despite 2026-07-16 activation — flagged to human. CSV total now **n=159**.
- **Batch log addendum.** `20260715` name-prior backfill: root cause of the 0-rows flag confirmed —
  the Sonnet dig that produced the LHB-channel rows above ran on a **standalone/pre-alignment copy**
  of the executor prompt (pasted inline, dated to the same schema as `sonnet-lhb-labeling-dig.md` but
  missing the step-4 non-LHB name-prior channel, the Northbound-strip instruction, and `机构-unresolved`
  routing — all three landed in the canonical file on 2026-07-16). Backfilled step 4 directly against
  the canonical spec: fetched live 上证50/沪深300/中证500 constituent lists (sina `vII_NewestComponent`,
  纳入日期 2026-06-15) and 20260715 daily 振幅/换手 (eastmoney kline API) for the 94 non-LHB universe
  names; 32 hit an index, kept the top 13 by tier + two-sided turnover (SSE50 ×6 @0.40, CSI300-only ×4
  @0.35, CSI500 ×3 @0.30), all `NON-LHB name-prior:`-prefixed, intention blank, self-audited against
  §6.1 (no dupes, cap held, sourced). CSV total now **n=172**. **Process fix for the 0716+ dig:** always
  hand executors the live file `docs/prompts/sonnet-lhb-labeling-dig.md` (or `fable5-guide-lhb-labeling.md`
  for the auditor), never a copy frozen in a prior message/session — the two diverge silently otherwise.
  **Auditor retro-audit (same day):** 13/13 backfill rows pass §6.1 — all in `stock_sample_20260715.xlsx`,
  disjoint from the 6 LHB hits, `NON-LHB name-prior:` prefix present, tier caps held (≤0.40), intention
  blank, sources cited, 0 duplicates — rows STAND. Noted as a **single-writer breach**: the executor
  appended to the gate CSV + batch log directly instead of returning rows for audit; harmless this time,
  but appends bypassing the auditor are quarantined-by-default going forward. Pooled July panel is now
  量化-heavy by construction (15/18 rows 量化, 13 of them weak name-priors ≤0.4) — the July gate chiefly
  measures mega-cap 量化 recall; confidence-weighting bounds their pull.
- **Batch log.** `20260714`: +2 rows (散户 1 @0.38 卖出 / 量化 1 @0.40 blank), dual-executor dig
  (Cursor + Sonnet) audited per guide §6; 1 candidate rejected (600844.SH 游资 — buy side not
  dominated by a registry seat; independent reads disagreed). CSV total now **n=156**.
  **Coverage collapse is structural, not a rules failure:** the July B-board universes turned
  all-SH mega-cap/STAR-heavy (`stock_sample_20260714.xlsx` = 100 SH codes) and only **3/100**
  tripped the LHB at all (both executors independently agree on the hit set). LHB-only digging
  cannot cover these panels; see guide discussion on pooling days + activating the step-4
  non-LHB name-prior channel. No 机构-unresolved cases (机构专用 sell-side only, non-dominant);
  institutional ledger unchanged (0 held).

## 7. What happens next (engineering, not your job)

Once `src/validate.py` exists (Track V V.1–V.2 — needs **no** labels to build) and this CSV has rows, each
H1/H2/H3 PR reports **proxy-F1 before/after** on your seed set, alongside the synthetic-panel assertion. A change
that moves the synthetic panel but **not** the proxy gets flagged before we trust it.
