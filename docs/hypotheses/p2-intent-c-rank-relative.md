# P2-intent-c — rank-relative intention gate (panel quantile cutoffs)

> **Slice 3 — Opus-only, TDD. Intention path only; capital path stays byte-identical.**
> **STATUS: FALSIFIED (2026-07-01). Reverted — not committed. Negative result recorded below.**
> Spec of record: `docs/LIS.md` v1.6.8 · `competitive-gap-audit-20260701.md` (D6 Slice 3).
> Parents: `p2-intent-t0-dominance.md`, `p2-intent-b-sell-precision.md`
> (P2-intent-b shipped: `τ_buy = INTENT_NET_BAND = 0.08`, `τ_sell = INTENT_SELL_BAND = 0.18`).
> Gate of record (baseline to beat): committed intention-F1 harness
> `scripts/validate_intent_offline.py` on `parquet:data/202606`.

---

## FALSIFICATION SUMMARY

The full 4×4 quantile grid was swept on the full-universe panel path (production
parity: each date's `labeled ∪ samples/stock-samples.xlsx` panel built once,
`assign_intentions` re-run per grid point). **No cutoff pair survives.** Two of the
three independent revert conditions fire across the *entire* grid:

- **P2-intent-b subset {0616–0623} `< 0.6271`:** every pair regresses it — the best
  subset wF1 is **0.6077** (bq=0.20/0.25, sq=0.10), −0.019 below the floor.
- **卖出 F1 does not improve over 0.48:** the best 卖出 F1 anywhere in the grid is
  **0.46** — the rank tails *lower* 卖出 precision (0.35–0.43 vs the absolute 0.46).
- (Full wF1 *can* be held: bq=0.25/sq=0.10 reaches 0.6780 vs baseline 0.6750, a
  trivial +0.003 — but only by sacrificing the two axes above and blowing the
  0623 T0-share sanity band, 0.651 ≫ [0.35,0.55].)

**Why it fails.** Ranking forces a *fixed fraction* of every day's panel into
buy/sell regardless of net magnitude. On the LHB cross-section the absolute
P2-intent-b bands already sit at the sweet spot; the quantile tails over-claim
sells (harvesting mild-negative T0 mass the asymmetric band was specifically tuned
to shed) and the predicted panels stay too directional (T0 share 47–70% on 0623).
The hypothesised panel-offset benefit doesn't materialise — these days are not
offset enough for a rank to beat a well-placed absolute band. Same negative shape
as Slice 1 (metric-align) and Slice 2 (feature batch): a plausible generalisation
that regresses the frozen offline gate.

**Action:** `assign_intentions` + config quantiles reverted; `label.py` /
`validate_intent_offline.py` restored to per-row `get_intention`;
`tests/test_rules.py` assign_intentions cases removed. Suite back to 203 passed / 2
xfailed. This doc is retained as the negative-result record; nothing committed
(human gate).

---

## 0. TL;DR

`get_intention` classifies buy/sell/T0 from an **absolute** band on the raw aggressor
net `net = ap_active_buy_pct − ap_active_sell_pct` (`net > +0.08` → 买入,
`net < −0.18` → 卖出, else T0交易). P2-intent-b fixed the T0-vs-sell over-fire, but the
weakest intention class is still **卖出** (F1 ≈ 0.48). Absolute cuts don't generalise
across the **100-stock daily cross-section**: the day-level net distribution shifts
(up-days lean the whole panel positive, down-days negative), so a fixed 0.08/0.18 pair
mislabels the tails on days whose panel is offset — the *same* lesson that forced
rank/quantile normalisation for capital_type (P5.1 / `normalize.py`).

**Slice 3:** classify intent **relative to the day's panel**. A stock is 买入 / 卖出
only if its net direction sits in the **top / bottom tail of that day's cross-section**,
not because it cleared a fixed threshold. This is the general form of the P2-intent-b
open-question framing (B): *recenter net by the panel, then band* — here the recentring
is a full within-day rank.

---

## 1. Mechanism

For each `transaction_date` panel (all stocks scored that day):

```
net_i = ap_active_buy_pct_i − ap_active_sell_pct_i           # per stock, RAW row
rank  = average-rank of net within the date panel            # ties → average rank
r_i   = (rank_i − 1) / (n − 1)                                # min-max to [0, 1]
买入   if r_i > 1 − τ_buy_q          (τ_buy_q  = INTENT_BUY_QUANTILE)
卖出   if r_i < τ_sell_q             (τ_sell_q = INTENT_SELL_QUANTILE)
T0交易 otherwise
```

- `r` is the within-day cross-sectional position of the stock's net (0 = most-negative
  net that day, 1 = most-positive). The gate keeps the **top `τ_buy_q` fraction** as
  buys and the **bottom `τ_sell_q` fraction** as sells; everything between is T0交易.
- Strict inequalities on both tails; the panel-extreme stocks (`r=1`, `r=0`) are always
  directional for any `τ>0`, the panel-median (`r=0.5`) is always T0交易 for any
  `τ<0.5`. No overlap since `τ_buy_q + τ_sell_q < 1` across the calibration grid.
- `net.rank(method="average")` handles ties symmetrically and deterministically.

**Why min-max rank (not percentile `pct=True`).** "Rank to [0,1]" is read literally:
min→0, max→1. On the ~100-stock production panel this is numerically identical to a
percentile cut; the difference matters only for tiny panels, where min-max keeps the
tails reachable and the gate well-defined.

### Fallback (single-stock / date-less path)

- **Panel `n ≤ 1`** (only one stock that date): rank is undefined → use the absolute
  `get_intention` (single-stock path) unchanged.
- **No identifiable `transaction_date`** (matrix has a single-level index and no
  `transaction_date` column): a day-panel cannot be formed → per-row absolute
  `get_intention`, with a WARNING. Production always carries the
  `(stock_code, transaction_date)` MultiIndex (`aggregate.build_feature_matrix`), so
  this branch only guards date-less unit callers; it never fires on the real pipeline.

`get_intention` itself is **unchanged** — it stays the single-row API for tests and the
fallback path. Slice 3 adds `assign_intentions(matrix)` and routes `label.py` /
`validate_intent_offline.py` through it.

---

## 2. Compliance (§3.3)

Quantile cutoffs are calibrated on **`tests/fixtures/validation_labels.csv` (LHB) only**
— never the Tianchi board. The rank is computed over the **full daily universe**
(`labeled ∪ samples/stock-samples.xlsx`, the same panel `validate_offline` /
`normalize_matrix` already use for capital), so offline ranks match production ranks.
No post-close data enters features; no answer-feedback tuning.

---

## 3. Falsification

Revert the whole slice (restore per-row `get_intention` in `label.py`, drop
`assign_intentions` + the two config quantiles) if **any** of:

- full intention weighted-F1 `< 0.6750`, OR
- P2-intent-b subset {0616–0623} intention `< 0.6271`, OR
- 卖出 F1 does not improve over the 0.48 baseline, OR
- capital_type gate not byte-identical (0.6438 full / 0.6773 through-0624 / 0.6500
  through-0625).

---

## 4. Calibration (LHB labels only)

Grid: `τ_buy_q ∈ {0.20, 0.25, 0.30, 0.35}` × `τ_sell_q ∈ {0.10, 0.12, 0.15, 0.18}`,
swept via `validate_intent_offline.py` (panel path = production).

**Selection rule (binding):**
1. Hold all intention floors (0.6750 full, 0.6271 P2-intent-b subset).
2. Maximise full intention weighted-F1.
3. Tie-break: maximise 卖出 F1, then 卖出 precision.
4. Distribution sanity: full-panel T0 share on the 20260623 production universe stays
   in ~[35%, 55%] (same discipline as P2-intent-b).

### 4.1 Results — full sweep table

Panel path = production (labeled ∪ 100-code universe; 9 dates, 109–114 stocks/panel).
`full` = all 115 intention labels {0616–0629}; `sub` = 64 labels {0616–0623}.
Floors: full ≥ 0.6750, sub ≥ 0.6271, 卖出 F1 > 0.48, T0@0623 ∈ [0.35,0.55].

| τ_buy_q | τ_sell_q | full wF1 | sub wF1 | 卖出 P/R/F1 | T0@0623 | verdict |
|---:|---:|---:|---:|---|---:|---|
| 0.20 | 0.10 | 0.6692 | 0.6077 | 0.43/0.50/0.46 | 0.697 | sub↓ 卖↓ T0↑ |
| 0.20 | 0.12 | 0.6631 | 0.5974 | 0.38/0.50/0.43 | 0.679 | sub↓ 卖↓ T0↑ |
| 0.20 | 0.15 | 0.6651 | 0.6001 | 0.37/0.58/0.45 | 0.642 | sub↓ 卖↓ T0↑ |
| 0.20 | 0.18 | 0.6515 | 0.5758 | 0.35/0.67/0.46 | 0.615 | sub↓ 卖↓ T0↑ |
| 0.25 | 0.10 | **0.6780** | 0.6077 | 0.43/0.50/0.46 | 0.651 | full↑ but sub↓ 卖↓ T0↑ |
| 0.25 | 0.12 | 0.6719 | 0.5974 | 0.38/0.50/0.43 | 0.633 | sub↓ 卖↓ T0↑ |
| 0.25 | 0.15 | 0.6739 | 0.6001 | 0.37/0.58/0.45 | 0.596 | sub↓ 卖↓ T0↑ |
| 0.25 | 0.18 | 0.6604 | 0.5758 | 0.35/0.67/0.46 | 0.569 | sub↓ 卖↓ T0↑ |
| 0.30 | 0.10 | 0.6408 | 0.5938 | 0.43/0.50/0.46 | 0.596 | all↓ |
| 0.30 | 0.12 | 0.6340 | 0.5829 | 0.38/0.50/0.43 | 0.578 | all↓ |
| 0.30 | 0.15 | 0.6353 | 0.5849 | 0.37/0.58/0.45 | 0.541 | full↓ sub↓ 卖↓ |
| 0.30 | 0.18 | 0.6195 | 0.5579 | 0.35/0.67/0.46 | 0.514 | all↓ |
| 0.35 | 0.10 | 0.6473 | 0.5962 | 0.43/0.50/0.46 | 0.550 | full↓ sub↓ 卖↓ |
| 0.35 | 0.12 | 0.6401 | 0.5845 | 0.38/0.50/0.43 | 0.532 | full↓ sub↓ 卖↓ |
| 0.35 | 0.15 | 0.6412 | 0.5857 | 0.37/0.58/0.45 | 0.495 | full↓ sub↓ 卖↓ |
| 0.35 | 0.18 | 0.6241 | 0.5555 | 0.35/0.67/0.46 | 0.468 | all↓ |

Candidates passing **all** floors: **0**. `sub` never clears 0.6271 (max 0.6077);
卖出 F1 never clears 0.48 (max 0.46).

### 4.2 Chosen cutoffs

**None** — falsified. `INTENT_BUY_QUANTILE` / `INTENT_SELL_QUANTILE` reverted (removed).

---

## 5. Results — per-class before/after

Baseline = absolute band (P2-intent-b, `INTENT_NET_BAND=0.08`, `INTENT_SELL_BAND=0.18`),
measured on the same production panels. "after" = the least-bad rank-relative pair
that holds the full floor (bq=0.25, sq=0.10) — shown to document the regression, not
adopted.

| set | metric | before (absolute) | after (bq.25/sq.10) |
|---|---|---:|---:|
| full | weighted-F1 | 0.6750 | 0.6780 |
| full | 买入 P/R/F1 | 0.83 / 0.66 / 0.74 | 0.88 / 0.64 / 0.75 |
| full | 卖出 P/R/F1 | 0.46 / 0.50 / **0.48** | 0.43 / 0.50 / **0.46** |
| full | T0交易 P/R/F1 | 0.58 / 0.73 / 0.65 | 0.57 / 0.75 / 0.65 |
| {0616–0623} | weighted-F1 | **0.6271** | **0.6077** |
| 0623 full-panel T0 share | — | (n/a) | 0.651 |

The +0.003 full-wF1 gain is entirely a 买入-precision artifact (0.83→0.88); it is
paid for by a −0.019 subset regression and a −0.02 卖出-F1 regression — exactly the
class Slice 3 set out to *improve*. Net negative.

Capital gate (byte-identical, unaffected by construction — intention path only):
full 0.6438 / through-0624 0.6773 / through-0625 0.6500.

---

## 6. Scope

- **Touch:** this doc; `src/rules.py` (`assign_intentions` — new), `src/label.py`
  (`weak_label_matrix` routes through it), `config.py` (two quantile constants only),
  `scripts/validate_intent_offline.py` (panel-path parity), `tests/test_rules.py`
  (assign_intentions cases). Re-freeze `tests/test_validate_intent_offline.py`'s
  committed-number pin iff the slice is promoted.
- **Do NOT touch:** `score_capital_type`, `features.py`, `cluster.py`,
  `validation_labels.csv`, `RS_CADENCE_SOURCE`, `model.py`. `get_intention` keeps its
  absolute semantics (single-stock / fallback).

---

## 7. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| 卖出 support tiny (n≈9–12) | High | Quantile cut rests on the same few sells + the T0 mass; require 卖出 F1 to *improve*, not just full-F1. Falsify if it doesn't. |
| Overfit quantiles to labels | Medium | Coarse grid, single pair, LHB-only; distribution-sanity band on 0623 guards a degenerate directional split. Prefer a plateau over a spike. |
| Panel offset day (all-up / all-down) mislabels | Low (this is the fix) | Rank is invariant to a whole-panel net offset — the exact failure mode of the absolute band. |
| Capital regression | — | `assign_intentions` never touches `score_capital_type`; capital scored from `feat_norm` as before. Verify byte-identical. |
| Date-less caller silently ranks wrong | Low | Fallback to absolute + WARNING when no `transaction_date`; production always has the MultiIndex. |
