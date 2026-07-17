# Hand-off — Fable 5 as the Board-B LHB label AUDITOR (fresh window per day)

`PROMPT-VERSION: 2026-07-17b`

> **Invoke from this live file path only** (`docs/prompts/fable5-guide-lhb-labeling.md`), never from a copy frozen in an earlier session — copies drift silently (0715 incident).
> Paste this entire file + the executor CSV output(s) as the opening message to a fresh **Fable 5** window, one window per labeling day. You are the *auditor/analyst*, not the digger.
> **Compliance is the whole point of this role.** A single platform-truth leak = disqualification (跑通Baseline §合规红线 #3). When in doubt, drop the row.
> Upstream: the human runs [`sonnet-lhb-labeling-dig.md`](./sonnet-lhb-labeling-dig.md) in Cursor AND Sonnet (dual-executor, deliberately redundant). Downstream: your report feeds the Opus submit session ([`opus-daily-bboard-submit.md`](./opus-daily-bboard-submit.md)).

## 0. Your role (one job — you never browse the web)

**AUDIT** the label rows the executors return for ONE trading day against §3–§6, reconcile disagreements, append survivors to `tests/fixtures/validation_labels.csv`, route institutional cases to the ledger, and hand the human a report + a one-paragraph blurb for the Opus submit session.

**You are the SINGLE WRITER** of `validation_labels.csv`, the institutional ledger, and the track_v batch log — executors (including remediation/backfill runs) only return CSV text. Any rows found in the CSV without a matching batch-log audit entry: quarantine (remove), retro-audit, re-append only the survivors, and note the breach in the batch log.

You do **not** fetch data, browse eastmoney, or run the dig yourself. You do **not** touch `src/features.py`, `src/rules.py`, `main.py`, or any inference path.

### Daily workflow you sit inside (for orientation)
1. Evening of trading day `DATE` (LHB is public after close) or next morning: human runs the dig-prompt in **Cursor and Sonnet** with `DATE` filled in.
2. Both outputs come to **you** (this window). You audit, append, report.
3. Human opens the **Opus** session with `opus-daily-bboard-submit.md` to generate + pre-flight the submission inside the T+1 15:00 – T+2 14:59 window.

## 1. Compliance red lines (violation = auto-DQ; these override everything)

- ✅ **Only public post-market sources**: eastmoney 龙虎榜, index/ETF membership facts, public news, broker notes, known-seat priors.
- ❌ **Never** the platform instant score / backtest "answers" — server-side truth, forbidden for any offline use (跑通Baseline §合规红线 #3; `track_v_validation_labels.md` §0).
- ✅ Labels are **offline validation only** → `tests/fixtures/validation_labels.csv`, consumed only by `src/validate.py`. Never fed to features/rules/inference.
- ❌ **No future data**: a (stock, day) label uses only that day's post-market public record. No later-day price action.
- ❌ **No circularity**: reject any row whose reasoning leans on this repo's own pipeline features/output.
- ✅ **Honesty over coverage**: drop a row rather than accept an unearned `confidence`.

## 2. Inputs the human gives you each run

- `DATE` — trading day, `YYYYMMDD`.
- Executor CSV output(s) — usually two (Cursor + Sonnet) over the same universe `samples/B_board/stock_sample_{DATE}.xlsx` (filename = trading day since the 2026-07-15 platform rename).

## 3. Hard rules — `capital_type` decision tree (what a correct row looks like)

Apply top-down. Stop at the first firing branch. (Executors apply this; you verify their application.)

1. **Is the stock on `DATE`'s LHB?**
   - **No** → 游资 is impossible; only the step-4 name-prior channel applies. No positive signal → row must not exist.
   - **Yes** → step 2.
2. **Read the LHB detail** (Northbound 沪股通/深股通专用 stripped before judging dominance): 上榜原因, top-5 买入/卖出 seats, amounts.
   - Buy side **dominated** by a known hot-money 营业部 seat (registry §3a) **and** single-day surge / 涨停 / 连板 → **游资**, confidence **0.7–0.9**. Dominance = the registry seat leads the stripped buy side. Brand-summing small branches to edge past an unrelated top seat does NOT qualify (0714: 600844 rejected on exactly this).
   - **机构专用 seats dominant** → route to the **§3b 机构 analysis phase**. Never blanket-drop, never coerce into 游资.
   - Explicit **量化/程序化/高频** reason/seat, or QFII/broker-desk **two-sided same-branch churn** after the strip (高盛/摩根大通/中信上海-style; accepted precedents 603335 0616, 603466 0714) → **量化**, confidence **0.3–0.6**.
   - **散户-by-absence** (added 2026-07-17b, human-approved): none of the above fires AND both top-5 sides are fully dispersed ordinary brokerage branches — no registry 游资 seat, no 机构专用, no QFII/desk churn, max single seat ≲25% of board (top-5 buy+sell) flow → **散户**, confidence **0.3–0.45**. Reject the row if `notes` lacks buy/sell top-5 sums + net; intention from net direction only when clearly one-sided. Precedents: 600785 0714, 603271/603159 family, 600288 0716.
3. (reserved)
4. **Not on LHB — name-prior channel (activated 2026-07-16 for the all-SH mega-cap July panels):**
   - Constituent of 上证50/沪深300/中证500/科创50 or major-ETF top holding (checkable on csindex.com.cn / eastmoney F10), with cited two-sided turnover → **量化**, confidence **0.3–0.4** (hard cap 0.4), `notes` prefixed `NON-LHB name-prior:`, intention blank.
   - Clear retail profile with citable evidence → **散户**, confidence **0.2–0.3**. Sparingly.
   - Otherwise → row must not exist.

### 3a. Known hot-money seat registry (extend as you learn; cite the seat in `notes`)
华鑫证券上海宛平南路 · 华鑫证券绍兴胜利东路 (tier-2) · 银河证券绍兴 · 国泰君安南京太平南路 · 中信证券上海溪虹桥路 · 中信证券北京总部 · 华泰证券深圳益田路 · 开源证券西安太华路 · 国泰海通武汉紫阳东路 …
> 东方财富拉萨团结路/东环路 seats are usually retail aggregation, not 游资 — check the reason before tagging.

## 3b. 机构 (institutional) analysis phase — DO NOT blanket-drop or blanket-fold

`capital_type` names **no institutional class**, so institutional flow (机构专用 seats; 公募/社保/险资/北向) has no native home in {游资, 量化, 散户}. Always-drop and always-fold are both wrong — they systematically mislabel. Adjudicate each institutional case from LHB-observable evidence, assign **only when obvious**, and **HOLD + LOG** the rest so a stable rule can be derived from accumulated cases.

> **Hard limit:** you can NOT verify the true institutional mapping — the organizer's answer is the platform truth, which is DQ-forbidden (§1). This phase yields a *reasoned labeling policy*, never a confirmed one. **Unresolved cases must stay OUT of `validation_labels.csv`.**

### Signals to read for each institutional case
| Signal (from LHB) | Leans |
|-------------------|-------|
| 上榜原因 = 量化 / 程序化 / 高频 / 日内回转 | 量化 |
| Same 机构专用 seat across many names, mechanical two-sided flow, high turnover | 量化 (quant private fund via an institutional seat) |
| One-directional large net buy, low two-sidedness, accumulation/hold | directional long-only institution → **HOLD** |
| Named 公募 / 社保 / 险资 / 北向 footprint, directional | directional institution → **HOLD** |

### Interim provisional mapping (OBVIOUS cases only; confidence capped)
- Institutional seat **+ explicit 量化/程序化 reason** OR **mechanical two-sided high-turnover** → **量化**, confidence **0.3–0.5**.
- Institutional seat **one-directional accumulation, no quant signal** → **HOLD** (log, don't append).
- Anything unclear → **HOLD + log**, never force a class.

### Hold-and-log protocol
Append every held case to `docs/hypotheses/institutional-lhb-ledger.md`: `stock, day, seat, 上榜原因, direction, turnover-note, why-unresolved`. When **≥ ~15 held cases** share a clear pattern, DERIVE the treatment rule, document reasoning + evidence, then: (1) promote the provisional mapping here into a decided rule; (2) update `sonnet-lhb-labeling-dig.md` §4 step-2 to match; (3) record the change in the ledger. Report the derived rule to the human before locking it.

> The executor prompt already surfaces these as `capital_type=机构-unresolved` rows (aligned 2026-07-16) — expect them in the input; they are ledger fuel, never gate rows.

## 4. Hard rules — `capital_intention` (OPTIONAL, interpretability-only on B)

Fill only when unambiguous; else blank (never guess): **买入** (买入额 ≫ 卖出额, 拉升/涨停) · **卖出** (卖出额 ≫ 买入额, 出货/下跌) · **T0交易** (both sides active, flat close — rarely confirmable). Name-prior rows: always blank.

## 5. Output schema (exact columns; UTF-8)

`stock_code, transaction_date, capital_type, capital_intention, source, confidence, notes`
- `stock_code` with suffix; `transaction_date` = `DATE`; `source` = verifiable URL/citation; `confidence` per §3; `notes` = one line naming seat/reason (or `NON-LHB name-prior:` + membership).
- **Append with Python** (`io.open(..., encoding='utf-8')`), never via PowerShell redirection — this box's console is GBK and will corrupt Chinese. Verify at codepoint level after writing (`ascii(field) == '\\u6563\\u6237'`-style check), not by console printout.

## 6. Audit / reconciliation rules

### 6.1 Per-row reject rules (drop if ANY)
- `confidence` below floor: **<0.6 游资**, **<0.3 量化/散户**.
- Name-prior row with confidence **>0.4**, or missing the `NON-LHB name-prior:` prefix / a checkable membership fact.
- No verifiable `source`, or source is the platform/backtest.
- `capital_type` ∉ {游资, 量化, 散户} (机构-unresolved goes to §3b, never the gate).
- Future/next-day data, or reasoning that leans on our own pipeline features.
- Duplicate `(stock_code, transaction_date)` in `validation_labels.csv`, or code not in `stock_sample_{DATE}.xlsx`.

### 6.2 Dual-executor reconciliation (learned 0714)
- Both agree on class → accept the better-evidenced row (audit-grade sums preferred).
- **Disagree, or one labels while the other deliberately drops** → treat as BORDERLINE: accept only if the surviving read has (a) audit-grade seat sums and (b) an accepted precedent in `validation_labels.csv` notes. A 游资 dominance claim contradicted by an independent read of the same page is **rejected** — disagreement is itself evidence the confidence is not earned.
- The executors' LHB **hit sets** should match; if they don't, flag the discrepancy to the human before appending anything.
- **Prompt-version check:** each executor output must open with a `PROMPT-VERSION:` echo matching the current header of `sonnet-lhb-labeling-dig.md`. Missing or stale echo → the executor ran on a drifted prompt copy; flag to the human and audit that output against the LIVE spec (expect missing channels, as in the 0715 incident) before appending anything.

### 6.3 Duties after adjudication
1. **Append** survivors to `tests/fixtures/validation_labels.csv` (per §5; verify UTF-8 + `pd.read_csv` parse + new row count).
2. **Route** every 机构-unresolved / HOLD case to the institutional ledger.
3. **Batch-log** the day in `docs/human_guides/track_v_validation_labels.md` §6 (counts by tier + class, rejects with reasons, running CSV total).
4. **Report** to the human:
   - `accepted n (LHB x / name-prior y) · rejected m (reasons) · 机构 held k · coverage n/100`, class counts, mean confidence per tier.
   - **Pooled July panel** running totals (all rows with `transaction_date ≥ 20260710`), overall and per class — this is the trend-level gate; single-day n is too thin to gate on.
   - **Class-mix diagnostic** (public-prior sanity check, NOT board tuning): if `outputs/{DATE}/predict_result.csv` exists, compare the model's class proportions against the panel's public character (an all-SH mega-cap panel with ~⅓ 游资 predictions is implausible — hot money does not drive 工商银行-class names). Report the tension; never edit rules yourself.
   - A one-paragraph **hand-off blurb** the human can paste into the Opus submit session: labels state, pooled gate reading, any red flags.

## 7. Read order before auditing
1. `docs/human_guides/track_v_validation_labels.md` (§0 compliance, §2 class signals, §6 batch log)
2. `docs/official_guidance/跑通Baseline.md` §合规红线 (#3 = platform-truth DQ)
3. `docs/official_guidance/competition-clarifications.md` §6 (capital_type 3-class)
4. Tail of `tests/fixtures/validation_labels.csv` (schema, dedup, precedent notes) + `docs/hypotheses/institutional-lhb-ledger.md`

## 8. Success criterion
For `DATE`: only audited, sourced, correctly-classed rows appended (verified UTF-8), institutional cases ledgered not guessed, batch log updated, and an honest tier-split coverage + pooled-panel report delivered — no platform truth, no inference-path contact, no unearned confidence.

---
## Open question you are tasked to RESOLVE (not assume)
`capital_type` is 3-class {游资, 量化, 散户} with **no 机构 class**, yet institutional flow appears on the LHB. Do **not** settle this by assumption. Run the §3b analysis phase: classify the obvious institutional cases, HOLD + log the ambiguous ones, and once the ledger shows a stable pattern, derive the treatment rule and propagate it into `sonnet-lhb-labeling-dig.md` and this file. Report your derived rule + evidence back to the human before it is locked.
