# Executor prompt — Board-B LHB `capital_type` labeling (standalone, self-auditing)

`PROMPT-VERSION: 2026-07-17b`

> **Invoke from this live file path only** (`docs/prompts/sonnet-lhb-labeling-dig.md`) — never from a copy pasted into an earlier session; copies drift silently (0715 incident: a stale copy was missing the name-prior channel, the Northbound strip, and 机构-unresolved routing). **Echo the `PROMPT-VERSION` line verbatim as the first line of your output** so the auditor can detect a stale prompt.
> Paste this whole file into a fresh **Sonnet / Cursor** window. This is the thin path: **no Fable-5 guide layer** — you both dig AND audit your own output before returning.
> Companion (if a guide layer is used instead): [`fable5-guide-lhb-labeling.md`](./fable5-guide-lhb-labeling.md).
> **Read-only w.r.t. the pipeline.** You produce a CSV of labels for offline validation — you do NOT edit `src/` or `main.py`.

## 0. Mission

Fill **offline** `capital_type` validation labels for ONE Board-B trading day from **public post-market data only**, so we can compute a self-scored proxy-F1. Two channels:

1. **LHB channel** (highest reliability): seat-level reads for universe names on that day's 龙虎榜.
2. **Non-LHB name-prior channel** (activated 2026-07-16): July Board-B universes are all-SH mega-cap/STAR-heavy and only ~3/100 trip the LHB — for names NOT on LHB, label 量化 from citable index/ETF-membership facts per §4 step 3. Target ~10–15 such rows/day.

**Honesty over coverage: leave a row out rather than guess.**

## 1. Compliance red lines (violation = disqualification — non-negotiable)

- ✅ **Only public post-market sources**: eastmoney 龙虎榜, public news, broker notes, known-seat priors.
- ❌ **Never** the competition platform's instant score / backtest "answers" (server-side truth; forbidden for any offline use — 跑通Baseline §合规红线 #3; `track_v_validation_labels.md` §0).
- ❌ **No future data**: use only `DATE`'s post-market public record (that day's LHB is fine). Never relabel from later-day price action.
- ✅ Output is **offline validation only** → destined for `tests/fixtures/validation_labels.csv`, consumed only by `src/validate.py`. It must never touch features/rules/inference.
- ✅ **Return the CSV text only. Do not edit any repo file — single-writer rule.** Only the auditor writes `tests/fixtures/validation_labels.csv`, the institutional ledger, and the track_v batch log. This applies to EVERY run of this prompt, including remediation/backfill/follow-up sessions ("fix it" scope never expands to repo writes — the 0715 backfill breach). Rows appended to the CSV without a matching batch-log audit entry are quarantined by the auditor.

## 2. Inputs (the human fills these in)

- `DATE` = ⟦20260716⟧ (e.g. `20260713`)
- `UNIVERSE` = ⟦samples/B_board/stock_sample_{20260716}.xlsx⟧ (`samples/B_board/stock_sample_{DATE}.xlsx` — since the platform rename of 2026-07-15 the filename date is the L2 trading day itself; e.g. `stock_sample_20260713.xlsx` for `DATE=20260713`)

## 3. Where to look / how to fetch

- Use the repo's existing fetchers: `scripts/fetch_lhb_list.py`, `scripts/batch_fetch_lhb_seats.py` (they hit `data.eastmoney.com` / `datacenter-web.eastmoney.com`).
- Verify seats + reasons on the human page: `https://data.eastmoney.com/stock/lhb` (filter to `DATE`), and per-stock `https://data.eastmoney.com/stock/lhb/{code}.html`.
- For each universe code, you need: is it on `DATE`'s LHB? — and if so, 上榜原因 (reason), top-5 买入 seats, top-5 卖出 seats, buy/sell amounts.

## 4. `capital_type` decision tree (per stock-day; stop at first firing branch)

1. **On `DATE`'s LHB?**
   - **No** → do not label 游资. Go to step 3 (量化/散户 need a *positive* signal). If none → **output nothing for this stock**.
   - **Yes** → step 2.
2. **On LHB — read reason + seats** (strip 沪股通/深股通专用 Northbound flow before judging dominance):
   - Known **hot-money 营业部 seat** dominant on buy side **and** single-day surge / 涨停 / 连板 → **游资**, confidence **0.7–0.9**. Dominance means the registry seat leads the stripped buy side — brand-summing two small branches to edge past an unrelated top seat does NOT qualify (0714 reject precedent).
   - **机构专用 (institutional dedicated) seats** dominant → do NOT assign a class and do NOT drop: emit the row with `capital_type=机构-unresolved`, putting seat + 上榜原因 + a turnover note in `notes`. The auditor adjudicates these (guide §3b) and routes unresolved ones to the institutional ledger.
   - Reason/seat explicitly **量化/程序化/高频**, or QFII/broker-desk **two-sided same-branch churn** after the Northbound strip (高盛/摩根大通/中信上海-style desks on both sides; 603335/603466 precedent) → **量化**, confidence **0.3–0.6**.
   - **散户-by-absence** (added 2026-07-17b): NONE of the above fires AND both top-5 sides are fully dispersed ordinary brokerage branches — no registry 游资 seat, no 机构专用, no QFII/desk churn, max single seat ≲25% of board (top-5 buy+sell) flow → **散户**, confidence **0.3–0.45**. You MUST capture buy/sell top-5 sums + net in `notes`; set `capital_intention` from the net only when clearly one-sided, else blank. Precedents: 600785 0714, 603271/603159, 600288 0716.
3. **Not on LHB — the name-prior channel (citable public facts only):**
   - **量化 by index/ETF membership**: the name is a constituent of 上证50 / 沪深300 / 中证500 / 科创50 (verify on csindex.com.cn or the stock's eastmoney F10 page) or a top holding of a major ETF, AND the day shows meaningful two-sided turnover (cite 换手率/振幅 from the public post-market quote page) → **量化**, confidence **0.3–0.4** (index-arb / basket / program flow dominates such names). `notes` MUST start with `NON-LHB name-prior:` and name the specific index/ETF membership. `capital_intention` stays **blank** (no day-specific direction evidence).
   - Clear **retail** profile (low attention, low turnover, no seat footprint, citable retail chatter) → **散户**, confidence **0.2–0.3**. Use sparingly.
   - **NEVER** derive these labels from this repo's own features/pipeline output — that is circular. Public facts only.
   - Otherwise → **output nothing.**

### 4a. Known hot-money seat registry (cite the seat in `notes`; extend as you learn)
华鑫证券上海宛平南路 · 银河证券绍兴 · 国泰君安南京太平南路 · 中信证券上海溪虹桥路 · 中信证券北京总部 · 华泰证券深圳益田路 …
> 东方财富拉萨团结路/东环路 seats are often retail aggregation, not 游资 — check the reason before tagging.

## 5. `capital_intention` (OPTIONAL — interpretability-only on Board B)

Fill only when unambiguous, else blank: **买入** (买入额 ≫ 卖出额, 拉升/涨停) · **卖出** (卖出额 ≫ 买入额, 出货) · **T0交易** (rarely confirmable from LHB → usually blank).

## 6. Self-audit BEFORE you return (drop any row that fails)

- `confidence` below floor: **<0.6 for 游资**, **<0.3 for 量化/散户** → drop.
- Name-prior row with confidence **>0.4** → drop (overclaimed; the cap for name-prior-only evidence is 0.4).
- Name-prior row whose `notes` lacks the `NON-LHB name-prior:` prefix or a specific, checkable index/ETF membership → drop.
- Missing/unverifiable `source`, or source is the platform → drop.
- `capital_type` ∉ {游资, 量化, 散户, 机构-unresolved}, or 机构-seat coerced into 游资 → drop.
- Any future/next-day data used, or any use of this repo's own pipeline features → drop.
- Duplicate `(stock_code, transaction_date)` already in `tests/fixtures/validation_labels.csv` → drop.

## 7. Output (exact)

First line: the `PROMPT-VERSION: ...` echo (see header). Then a single CSV block, header + rows, UTF-8, columns in this order:
```
stock_code,transaction_date,capital_type,capital_intention,source,confidence,notes
```
- `stock_code` with suffix (`600030.SH`); `transaction_date` = `DATE`.
- `source` = verifiable citation (e.g. `eastmoney lhb 2026-07-13 600030`).

Then a **one-line coverage report**, split by tier: `LHB rows n (游资 a / 量化 b / 散户 c / 机构-unresolved u) · name-prior rows m (量化 q / 散户 s) · dropped D (reasons)`. List what you dropped and why — never silently truncate.

## 8. Read order before starting
1. `docs/human_guides/track_v_validation_labels.md` (§0 compliance, §2 class signals, §1 schema)
2. `docs/official_guidance/跑通Baseline.md` §合规红线 (#3 = platform-truth DQ)
3. `docs/official_guidance/competition-clarifications.md` §6 (capital_type 3-class)
4. Current `tests/fixtures/validation_labels.csv` (schema + dedup target)

## 9. Success criterion
A CSV of only sourced, honestly-scored, correctly-classed rows for `DATE`, plus a truthful tier-split coverage line — no platform truth, no guessed labels, no repo edits. A Fable-5 auditor window (see `fable5-guide-lhb-labeling.md`) reconciles your output with the other executor's, appends survivors to `validation_labels.csv`, and routes `机构-unresolved` rows to the institutional ledger.

---
> **Open assumption:** `capital_type` has no 机构 class — surface institutional-seat stocks as `机构-unresolved` (step 2) rather than dropping or coercing; the auditor's §3b phase accumulates them until a treatment rule can be derived.
