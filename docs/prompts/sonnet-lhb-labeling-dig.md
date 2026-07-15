# Executor prompt — Board-B LHB `capital_type` labeling (standalone, self-auditing)

> Paste this whole file into a fresh **Sonnet / Cursor** window. This is the thin path: **no Fable-5 guide layer** — you both dig AND audit your own output before returning.
> Companion (if a guide layer is used instead): [`fable5-guide-lhb-labeling.md`](./fable5-guide-lhb-labeling.md).
> **Read-only w.r.t. the pipeline.** You produce a CSV of labels for offline validation — you do NOT edit `src/` or `main.py`.

## 0. Mission

Fill **offline** `capital_type` validation labels for ONE Board-B trading day from **public 龙虎榜 (dragon-tiger) data only**, so we can compute a self-scored proxy-F1. Coverage will be low (often only a handful of the 100 names are on LHB) — that is expected. **Honesty over coverage: leave a row out rather than guess.**

## 1. Compliance red lines (violation = disqualification — non-negotiable)

- ✅ **Only public post-market sources**: eastmoney 龙虎榜, public news, broker notes, known-seat priors.
- ❌ **Never** the competition platform's instant score / backtest "answers" (server-side truth; forbidden for any offline use — 跑通Baseline §合规红线 #3; `track_v_validation_labels.md` §0).
- ❌ **No future data**: use only `DATE`'s post-market public record (that day's LHB is fine). Never relabel from later-day price action.
- ✅ Output is **offline validation only** → destined for `tests/fixtures/validation_labels.csv`, consumed only by `src/validate.py`. It must never touch features/rules/inference.
- ✅ **Return the CSV text only.** Do not edit any repo file.

## 2. Inputs (the human fills these in)

- `DATE` = ⟦YYYYMMDD⟧ (e.g. `20260713`)
- `UNIVERSE` = ⟦stock list file⟧ (e.g. `samples/B_board/stock_sample_20260714.xlsx`; release-day filename maps to L2 day `DATE` = release−1)

## 3. Where to look / how to fetch

- Use the repo's existing fetchers: `scripts/fetch_lhb_list.py`, `scripts/batch_fetch_lhb_seats.py` (they hit `data.eastmoney.com` / `datacenter-web.eastmoney.com`).
- Verify seats + reasons on the human page: `https://data.eastmoney.com/stock/lhb` (filter to `DATE`), and per-stock `https://data.eastmoney.com/stock/lhb/{code}.html`.
- For each universe code, you need: is it on `DATE`'s LHB? — and if so, 上榜原因 (reason), top-5 买入 seats, top-5 卖出 seats, buy/sell amounts.

## 4. `capital_type` decision tree (per stock-day; stop at first firing branch)

1. **On `DATE`'s LHB?**
   - **No** → do not label 游资. Go to step 3 (量化/散户 need a *positive* signal). If none → **output nothing for this stock**.
   - **Yes** → step 2.
2. **On LHB — read reason + seats:**
   - Known **hot-money 营业部 seat** dominant on buy side **and** single-day surge / 涨停 / 连板 → **游资**, confidence **0.7–0.9**.
   - **机构专用 (institutional dedicated) seats** dominant → **SKIP** (no valid 3-class label — do NOT coerce into 游资).
   - Reason/seat explicitly **量化/程序化/高频** with a citable source → **量化**, confidence **0.3–0.6**.
3. **Not on LHB — only with a positive public signal:**
   - Known **index-arb / ETF-heavy / high-frequency** name + high two-sided intraday turnover + source naming 量化 → **量化**, confidence **0.3–0.5**.
   - Clear **retail** profile (low attention/turnover, no seat footprint, citable retail chatter) → **散户**, confidence **0.2–0.4**.
   - Otherwise → **output nothing.**

### 4a. Known hot-money seat registry (cite the seat in `notes`; extend as you learn)
华鑫证券上海宛平南路 · 银河证券绍兴 · 国泰君安南京太平南路 · 中信证券上海溪虹桥路 · 中信证券北京总部 · 华泰证券深圳益田路 …
> 东方财富拉萨团结路/东环路 seats are often retail aggregation, not 游资 — check the reason before tagging.

## 5. `capital_intention` (OPTIONAL — interpretability-only on Board B)

Fill only when unambiguous, else blank: **买入** (买入额 ≫ 卖出额, 拉升/涨停) · **卖出** (卖出额 ≫ 买入额, 出货) · **T0交易** (rarely confirmable from LHB → usually blank).

## 6. Self-audit BEFORE you return (drop any row that fails)

- `confidence` below floor: **<0.6 for 游资**, **<0.3 for 量化/散户** → drop.
- Missing/unverifiable `source`, or source is the platform → drop.
- `capital_type` ∉ {游资, 量化, 散户}, or 机构-seat coerced into a class → drop.
- Any future/next-day data used → drop.
- Duplicate `(stock_code, transaction_date)` already in `tests/fixtures/validation_labels.csv` → drop.

## 7. Output (exact)

A single CSV block, header + rows, UTF-8, columns in this order:
```
stock_code,transaction_date,capital_type,capital_intention,source,confidence,notes
```
- `stock_code` with suffix (`600030.SH`); `transaction_date` = `DATE`.
- `source` = verifiable citation (e.g. `eastmoney lhb 2026-07-13 600030`).

Then a **one-line coverage report**: `accepted N/100 · 游资 a / 量化 b / 散户 c · dropped D (reasons)`. List what you dropped and why — never silently truncate.

## 8. Read order before starting
1. `docs/human_guides/track_v_validation_labels.md` (§0 compliance, §2 class signals, §1 schema)
2. `docs/official_guidance/跑通Baseline.md` §合规红线 (#3 = platform-truth DQ)
3. `docs/official_guidance/competition-clarifications.md` §6 (capital_type 3-class)
4. Current `tests/fixtures/validation_labels.csv` (schema + dedup target)

## 9. Success criterion
A CSV of only sourced, honestly-scored, correctly-classed rows for `DATE`, plus a truthful coverage line — no platform truth, no guessed labels, no repo edits. The human appends it to `validation_labels.csv` and scores with `src/validate.py`.

---
> **Open assumption:** `capital_type` has no 机构 class — this prompt DROPS institutional-seat stocks. If the organizer folds 机构 into 游资/量化, step 2 changes by one line; flag it rather than guessing.
