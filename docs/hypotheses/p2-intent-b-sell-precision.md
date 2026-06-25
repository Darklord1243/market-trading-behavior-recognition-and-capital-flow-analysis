# P2-intent-b — why `卖出` precision is 0.27 (the symmetric band over-fires sells)

> **Hypothesis doc — Opus-only, read-only. No code changed, no labels touched.**
> Spec of record: `docs/LIS.md` v1.6.8 §5 (hypotheses) + §3 (compliance).
> Empirical basis: read-only audit `scratchpad/audit_intent_sell.py` over the
> committed intention harness panel (`scripts/validate_intent_offline.py`,
> `build_feature_matrix_for_panel` on `parquet:data/202606`, raw rows).
> Gate of record: the committed intention-F1 harness (`563adc4`) —
> **0.5539 / n=64** {0616–0623}, **0.5772 / n=76** incl 0624.
> Status: **awaiting human approval before any Phase B probe.**

---

## 0. TL;DR

- P2-intent (`7233d6b`) replaced the imbalance AND-gate with a **symmetric**
  net-direction band `τ = INTENT_NET_BAND = 0.08`. It fixed 买入 (precision **0.83**,
  recall 0.52→). But `卖出` precision is only **0.27** (n=76): of **26** predicted
  sells, **7** are real; **19** are false.
- The 19 false sells decompose as **14 true `T0交易` + 5 true `买入`** — i.e. the
  sell branch is eating the neutral class, not confusing buy↔sell.
- **Root cause: the −0.08 sell threshold sits inside the dense left shoulder of the
  `T0交易` net distribution.** `T0交易`'s net (`buy_pct − sell_pct`) is **left-skewed**
  (median −0.04, p25 −0.14) — the same structural sell-lean the P2-intent doc traced
  to `obp_imbalance_mean` (median −0.375). True sells sit much deeper (median **−0.185**,
  p25 **−0.380**). A *symmetric* ±0.08 band is well-placed for buys (clean separation,
  P=0.83) but **mis-placed for sells**: it cuts into the negative-leaning T0 mass.
- **Fix (ONE): make the band asymmetric** — keep `τ_buy = 0.08`, widen the sell side to
  `τ_sell ≈ 0.18`. Calibrated identically on **both** label sets (joint sweep peak):
  - n=64: **0.5539 → 0.6271** (+0.073)
  - n=76: **0.5772 → 0.6480** (+0.071)
  Gain source: `卖出` precision 0.27→**0.42** *and* `T0交易` recall 0.48→**0.76** (the 14
  mis-swept T0 rows return to T0). Buy branch byte-identical.

---

## 1. Confusion audit (symmetric τ=0.08)

Truth (row) × predicted (col), n=76 (n=64 identical pattern):

| truth \ pred | 买入 | 卖出 | T0交易 | total |
|---|---:|---:|---:|---:|
| **买入** | 19 | 5 | 10 | 34 |
| **卖出** | 1 | **7** | 1 | 9 |
| **T0交易** | 3 | **14** | 16 | 33 |

- Predicted `卖出` column = 1 + 7 + 14 = **26**; only **7** correct → precision **0.269**.
- The leak is **column-vertical**: **14 of 33 true `T0交易`** fall into `卖出`. A further
  **5 of 34 true `买入`** do too. Sells are not confused with buys (only 1 true sell →
  buy); the sell branch is **over-claiming the neutral class**.

---

## 2. Why — `net` distribution per truth class (n=76)

`net = ap_active_buy_pct − ap_active_sell_pct` (centered at 0; the clean, symmetric
signal P2-intent adopted).

| truth class | n | min | p25 | med | p75 | max | mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| 买入 | 34 | −0.252 | 0.000 | **+0.144** | 0.193 | 0.501 | +0.111 |
| 卖出 | 9 | −0.494 | **−0.380** | **−0.185** | −0.084 | 0.425 | −0.155 |
| T0交易 | 33 | −0.358 | **−0.138** | **−0.034** | 0.023 | 0.355 | −0.056 |

Two facts drive the whole error:

1. **`T0交易` is not centered at 0 — it leans negative** (median −0.034, p25 −0.138).
   ~⅓ of neutral stocks dip below −0.08 purely from the structural sell-lean of the
   aggressor/book signals (P2-intent §3 flag: `obp_imbalance_mean` median −0.375). The
   −0.08 sell cut lands **inside this shoulder**, so it harvests neutral stocks as sells.
2. **True `卖出` sits far deeper than the threshold** (median −0.185, p25 −0.380). Real
   sells don't need a threshold as shallow as −0.08 to be caught — most clear −0.18 with
   room to spare.

So the threshold is in the wrong place *only on the sell side*. The **buy** side is
healthy: 买入 median +0.144, the +0.08 cut separates cleanly (precision 0.83). The
asymmetry of the *data* (buys clean & centered positive, neutrals leaning negative)
demands an asymmetry of the *gate* — a symmetric band cannot fit both shoulders.

---

## 3. The 26 predicted sells, ranked by net (n=76)

`OK` = true sell, `XX` = false. Sorted most-negative first:

```
OK 000911 -0.494   OK 000010 -0.396   OK 600193 -0.380          ← deep, all real
XX 002431 -0.358   XX 002512 -0.340   XX 002717 -0.288  (T0)
XX 000632 -0.252(买)  XX 603778 -0.249(T0)  XX 600370 -0.239(买)
XX 002542 -0.225(T0)
OK 603778 -0.222   OK 603271 -0.185                              ← last deep reals
XX 002323 -0.151   XX 301669 -0.139   XX 603335 -0.139
XX 603065 -0.138   OK 000777 -0.131   XX 301139 -0.127 …
… (mild shoulder: 14 XX between −0.16 and −0.08, mostly T0) …
OK 001203 -0.084   XX 002137 -0.084(买)                          ← at the boundary
```

The pattern: **3 of the deepest-4 are real**; the **mild shoulder (−0.16…−0.08) is almost
all false** (T0/买入). Moving `τ_sell` deeper trims the false shoulder fastest. The cost is
**3 mild true sells** (`000777` −0.131, `603271` −0.185≈, `001203` −0.084) that fall back to
T0 — an acceptable recall trade given how many false sells leave with them.

---

## 4. Proposed fix (ONE) + calibration

**Asymmetric net-direction band. Keep the buy side; widen the sell deadband.**

```
net = ap_active_buy_pct − ap_active_sell_pct
买入   if net > +τ_buy      # τ_buy = INTENT_NET_BAND = 0.08  (UNCHANGED — buy is healthy)
卖出   if net < −τ_sell     # τ_sell ≈ 0.18  (NEW constant, e.g. INTENT_SELL_BAND)
T0交易 otherwise
```

Rationale: `T0交易`'s negative lean means the neutral deadband must extend **further on the
sell side** than the buy side. `τ_sell` is placed below the T0 left-shoulder (p25 −0.138)
but above the true-sell median (−0.185), so it keeps the deep real sells while shedding the
mild T0 mass. Single interpretable constant; calibrated on our LHB labels (allowed, same
methodology as the capital_type gate and P2-intent), **never** on the platform score.

### 4.1 `τ_sell` sweep (τ_buy = 0.08 fixed) — joint peak on both sets

n=76 (full, incl 0624):

| τ_sell | weighted-F1 | 卖出 P/R/F1 | T0 recall | pred 买/卖/T0 |
|---:|---:|---|---:|---|
| **0.08** (current) | 0.5772 | 0.27 / 0.78 / 0.40 | 0.48 | 23 / 26 / 27 |
| 0.12 | 0.5953 | 0.32 / 0.67 / 0.43 | 0.58 | 23 / 19 / 34 |
| 0.15 | 0.6376 | 0.38 / 0.56 / 0.45 | 0.73 | 23 / 13 / 40 |
| **0.18** (recommended) | **0.6480** | 0.42 / 0.56 / 0.48 | 0.76 | 23 / 12 / 41 |
| 0.20 | 0.6351 | 0.36 / 0.44 / 0.40 | 0.76 | 23 / 11 / 42 |
| 0.25 | 0.6395 | 0.43 / 0.33 / 0.38 | 0.82 | 23 / 7 / 46 |

n=64 ({0616–0623}, matches the locked baseline) — **same peak at 0.18**:

| τ_sell | weighted-F1 | 卖出 P/R | note |
|---:|---:|---|---|
| 0.08 | 0.5539 | 0.28 / 0.78 | locked baseline |
| 0.15 | 0.6146 | 0.38 / 0.56 | |
| **0.18** | **0.6271** | 0.42 / 0.56 | peak |
| 0.20 | 0.6118 | 0.36 / 0.44 | past peak |

`τ_sell = 0.18` is the joint optimum on **both** independently — not a single-date artifact.
`0.15` is the conservative neighbour (higher sell recall, ~0.013 less wF1); `0.20+` overshoots
(sell recall collapses). Phase B should confirm the peak on the live n=76 (now incl 0624) and
fix one value.

---

## 5. Acceptance signal & scope (for approval — not yet dispatched)

- **Files:** `config.py` (add `INTENT_SELL_BAND`), `src/rules.py` (`get_intention` sell
  branch), `tests/test_rules.py` (asymmetric cases) **only**. Report before→after via the
  committed `scripts/validate_intent_offline.py`.
- **Forbidden:** `cluster.py`, `validation_labels.csv` (human-only), `score_capital_type`,
  `src/validate.py`, any tuning to the Tianchi/board score.
- **Acceptance:**
  1. capital_type proxy **byte-identical** — `0.6773/n=77`, continuity `0.6599/n=24`
     (impossible to move by construction; verify as scope discipline).
  2. intention weighted-F1 **n=64 ≥ ~0.62** and **n=76 ≥ ~0.64**, materially beating the
     locked 0.5539 / 0.5772; the integration test's 0.5539 pin updates to the new value.
  3. 买入 branch unchanged (precision 0.83, same predicted-买入 count 23).
  4. 卖出 precision ↑ to ~0.42 and T0交易 recall ↑ to ~0.76 (the two move together).
  5. Suite green; new asymmetric-band tests are discriminating.
- Report offline metrics only — **human holds the upload; no board-score claim.** The 0624
  submit.zip regenerate (for re-upload) is a **separate, subsequent** slice, only after the
  gate change is approved and verified.

---

## 6. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| **`卖出` support is tiny (n=9)** | **High** | τ_sell rests on 9 true sells + the T0 mass. The buy/T0 effects (n=34/33) are sturdier and carry most of the wF1 gain (T0 recall 0.48→0.76). Robustness across **two** independent sets (n=64 & n=76 both peak at 0.18) mitigates; re-confirm when 0625 labels add sells (V.3.5). |
| **Overfit τ_sell to labels** | Medium | Single interpretable constant from the net distribution, calibrated on **our** labels (allowed, same as capital_type gate), never the board. Peak is a plateau (0.15–0.18 all ≥0.61), not a spike — low sensitivity. |
| **Capital_type proxy regression** | — | `get_intention` does not touch `score_capital_type`; verify byte-identical. |
| **Buy-side collateral** | Low | τ_buy untouched → predicted-买入 count (23) and precision (0.83) fixed by construction. |
| **`obp` sell-lean is a real data bug, not market structure** | Medium (separate) | The asymmetric τ_sell *absorbs* a constant lean but not a per-stock sign flip. Out of scope here (same flag as P2-intent §3); file a separate read-only `obp` probe. |

---

## 7. Open question for the human (gate)

The fix introduces a second constant. Two equally-compliant framings:

- **(A) Asymmetric constant `τ_sell ≈ 0.18`** (recommended) — simplest, directly calibrated,
  one new interpretable number; plateau-robust.
- **(B) Recenter `net` by the panel/T0 median first, then a symmetric band** — keeps one τ but
  is fragile if the T0 lean is a per-day artifact rather than a stable offset (the §6 `obp`
  flag). Documented as the conservative cousin a probe could A/B.

Recommend **(A)**. Phase B not dispatched until you approve the slice and the τ_sell value.
