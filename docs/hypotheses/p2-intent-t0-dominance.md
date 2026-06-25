# P2-intent — why `capital_intention` collapses to T0交易 (92/99)

> **Phase A2 hypothesis doc — Opus-only, read-only. No code changed, no labels touched.**
> Spec of record: `docs/LIS.md` v1.6.7 §5 (hypotheses) + §3 (compliance).
> Empirical basis: read-only audit `scratchpad/audit_intent_0623.py` on the **exact 99 production
> stocks** of `outputs/20260623/predict_result.csv`, matrix rebuilt from `parquet:data/202606`.
> Status: **awaiting human approval before any Phase B Sonnet probe.**

---

## 0. TL;DR

- The intent gate (`src/rules.py:get_intention`) outputs **买入 4 / 卖出 3 / T0交易 92** on the 99
  production stocks — audit reproduces production **exactly**.
- Root cause is **not** a P5.1-style raw/normalized leak (the raw feed is intentional, `label.py:54-67`).
  It is two compounding mis-calibrations of **absolute** thresholds against the real cross-sectional
  distribution:
  1. **An AND-conjunction with a structurally biased signal.** 买入 needs
     `buy_pct > 0.6` **AND** `blended_imbalance > +0.08`. The imbalance term has a **median of −0.18**
     (mean −0.18) across the panel — it is systematically negative — so the `> +0.08` conjunct kills
     **8 of the 12** buy-side candidates. The conjunction, not the pct gate, is the proximate cause.
  2. **A pct threshold parked at the p90 tail.** `ap_active_buy_pct` has median **0.511**; the `0.6`
     cut sits at **p90**, so only ~10% of stocks can ever clear it.
- **Critical measurement gap:** the offline proxy gate (`scripts/validate_offline.py` → `validate.weighted_f1`)
  scores **`capital_type` only**. It is **blind to intention** — a `get_intention` change leaves
  `0.6971/n=65` and `0.6599/n=24` *exactly unchanged*. The orchestrator's stated acceptance metric
  therefore cannot measure this slice. **A new intention-F1 gate is required** (see §5), and the labels
  to build it already exist.

---

## 1. Distribution audit (20260623, n=99)

Branch reachability of `get_intention` (thresholds `INTENT_BUY_PCT=0.6`, `INTENT_SELL_PCT=0.6`,
`INTENT_IMBALANCE=0.08`; blend `0.4·book_imbalance + 0.6·obp_imbalance_mean`):

| Condition | Count |
|-----------|------:|
| `buy_pct > 0.6` | 12 |
| `sell_pct > 0.6` | 4 |
| `imbalance > +0.08` | 12 |
| `imbalance < −0.08` | **72** |
| **BUY branch** (`buy_pct>0.6` **AND** `imb>+0.08`) | **4** |
| **SELL branch** (`sell_pct>0.6` **AND** `imb<−0.08`) | **3** |
| **T0 fallback** | **92** |

Matches production (买入 4 / 卖出 3 / T0 92) to the row.

**Feature distributions (n=99):**

| Feature | min | p10 | p25 | med | p75 | p90 | max | mean |
|---------|----:|----:|----:|----:|----:|----:|----:|-----:|
| `ap_active_buy_pct` | 0.359 | 0.434 | 0.464 | **0.511** | 0.548 | 0.615 | 0.732 | 0.515 |
| `ap_active_sell_pct` | 0.268 | 0.385 | 0.452 | 0.489 | 0.536 | 0.566 | 0.641 | 0.485 |
| `blended_imbalance` | −0.675 | −0.518 | −0.353 | **−0.184** | −0.072 | 0.128 | 0.990 | −0.180 |
| `book_imbalance` (1st snap) | −0.964 | −0.557 | −0.375 | −0.032 | 0.315 | 0.622 | 1.000 | −0.011 |
| `obp_imbalance_mean` (full day) | −0.677 | −0.562 | −0.485 | **−0.375** | −0.272 | 0.026 | 0.984 | −0.292 |

Two facts drive everything:
- `ap_active_buy_pct` / `ap_active_sell_pct` are **clean and symmetric** (medians 0.511 / 0.489, centered on
  0.5 — they partition price-moving amount, so `buy_pct + sell_pct ≡ 1`). The only problem is the **0.6
  threshold sits at p90**.
- `blended_imbalance` is **badly off-center (median −0.18)**, dragged there by `obp_imbalance_mean`
  (60% weight, median **−0.375**). The symmetric `±0.08` gate applied to an asymmetric signal is the
  asymmetry engine: 72 stocks clear `< −0.08` (helps SELL) but only 12 clear `> +0.08` (blocks BUY).

---

## 2. Is it a raw-vs-normalized mismatch (the P5.1 lesson)?

**No — not the same bug.** `label.weak_label_matrix` (`src/label.py:54-67`) deliberately passes
`feat_raw` to `get_intention` because the gate thresholds are *absolute by design*; only
`score_capital_type` gets the rank-normalized row. This is intentional and documented, unlike P5.1 where
raw `n_ticks` leaked into KMeans.

**But the *spirit* of the P5.1 lesson applies:** an absolute threshold is only valid where the
cross-sectional density actually lives. Here both thresholds are placed where the population *isn't* —
`0.6` at p90 of a 0.51-median signal, and `±0.08` symmetric around a −0.18-median signal. The fix family
is the same one that resolved P5.1: **judge a stock relative to the day's panel**, not against a constant
parked in the tail.

---

## 3. Feature sensitivity — what blocks 买入/卖出?

| Feature | Role | Verdict |
|---------|------|---------|
| `ap_active_buy_pct` / `ap_active_sell_pct` | direction (aggressor share) | **Healthy, symmetric.** Only the 0.6 cut is too high (p90). |
| `book_imbalance` (first snapshot) | corroboration | Roughly centered (med −0.03); minor. |
| `obp_imbalance_mean` (full-day) | corroboration, **60% of blend** | **Structurally negative (med −0.375).** This is the dominant cause of the BUY/SELL asymmetry. |
| `blended_imbalance` (the AND-conjunct) | hard gate | **The proximate killer** — removes 8/12 buy candidates. |

⚠️ **Side-flag (out of scope, do not fix in this slice):** a full-day `obp_imbalance_mean` median of
**−0.375** across a broad universe is suspicious. It is consistent with either (a) a genuine ask-heavy
A-share book, or (b) a sign/column-semantics issue in `totalbidvolume`/`totalaskvolume`
(`features.py:155-161`). A median-recentering fix (§4) is **robust to a constant offset** but **not** to a
per-stock sign swap. Worth a separate read-only probe later; **not** part of P2-intent.

---

## 4. Proposed fix (ONE) + predicted distribution

**Replace the imbalance AND-conjunct with a symmetric net-direction band; demote imbalance to a
confidence-only role.**

```
net = ap_active_net_direction        # = buy_pct − sell_pct = 2·buy_pct − 1, centered at 0, symmetric
买入   if net > +τ
卖出   if net < −τ
T0交易 otherwise
# imbalance no longer hard-gates direction (it was the asymmetry engine);
# may remain as an intent_confidence weight only (label.py:_intent_confidence) — decide in probe.
```

Rationale, point-by-point against the audit:
- Removes the **biased imbalance hard-gate** (median −0.18) that asymmetrically blocked BUY.
- Uses the already-**symmetric, clean** net-direction signal centered at 0.
- Replaces the **p90-parked** 0.6 cut with a band τ placed where the density is.
- `τ` calibrated from the net-direction distribution to land near the **LHB truth prior** (§5), validated
  against our own hand labels — *not* the platform score (compliance §3 #3; same methodology already used
  for the `capital_type` gate).

**Predicted distribution (illustrative — probe will calibrate τ):**

| Gate | 买入 | 卖出 | T0交易 | directional share |
|------|----:|----:|------:|------------------:|
| **Current** (AND, audit) | 4 | 3 | 92 | 7% |
| Counterfactual: pct-only `>0.6` (drop AND) | 12 | 4 | 83 | 16% |
| Counterfactual: pure sign `buy_pct vs 0.5` | 54 | 45 | 0 | 100% (**overshoots**) |
| **Proposed band**, τ≈0.10 (buy_pct outside [0.45, 0.55]) | ~25 | ~25 | ~49 | ~50% |
| **LHB truth prior** (n=64, §5) | 27 | 9 | 28 | **56%** |

The band is the only candidate that lands near the truth prior. Pure sign-gate (T0→0) confirms the danger
of removing the neutral zone entirely; pct-only barely moves the needle.

---

## 5. The real gate (the doc's key contribution): an intention-F1 the harness doesn't compute

The existing proxy scores `capital_type` only, so it is the **wrong instrument** for this slice. But
`tests/fixtures/validation_labels.csv` already carries `capital_intention` ground truth (LHB-derived):

| capital_intention (truth) | count |
|---------------------------|------:|
| T0交易 | 28 |
| 买入 | 27 |
| 卖出 | 9 |
| (blank) | 1 |
| **usable n** | **64** |

Against this, the current 93%-T0 rule is structurally capped: it predicts T0 on rows that are 56%
directional. **Phase B must add an intention weighted-F1 over these labels and report before→after** —
that is the actual acceptance signal.

### 5.1 Measured baseline (read-only, `scratchpad/baseline_intent_f1.py`)

Production `get_intention()` run on raw matrix rows for every joinable labeled (stock, date), scored with
the exact `validate.weighted_f1` formula over `INTENTION_CLASSES`:

> **Current intention weighted-F1 = 0.4242 (n = 64)**

| class (truth) | precision | recall | F1 | support |
|---------------|----------:|-------:|---:|--------:|
| 买入 | 0.714 | **0.185** | 0.294 | 27 |
| 卖出 | 0.333 | 0.333 | 0.333 | 9 |
| T0交易 | 0.458 | 0.786 | 0.579 | 28 |

Predicted dist on the 64 joined rows: **T0交易 48 / 卖出 9 / 买入 7** vs truth **T0交易 28 / 买入 27 / 卖出 9**.

**Diagnosis confirmed quantitatively:**
- **买入 recall = 0.185** is the single dominant drag — the gate catches **5 of 27** true buys (BUY
  precision is high at 0.714, so it is *too conservative*, not wrong-headed: loosening trades a little
  precision for large recall).
- **T0交易 is a dumping ground** — recall 0.786 but precision only 0.458; 48 predicted vs 28 true.
  Moving over-assigned T0 rows to directional will lift T0 precision *and* BUY recall together.
- The band fix (§4) directly targets both: it raises directional share toward the 56% truth prior.

**0624 not yet joinable:** all 12 `20260624` labels are unscored — the `parquet:data/202606` corpus has
**no 0624 snapshot data** (`[WARN] no matrix for 20260624`). Baseline therefore covers the five prior
dates {0616, 0617, 0618, 0622, 0623}, n=64. Re-score once 0624 parquet lands (Track D / human ops).

**Phase B acceptance anchor:** beat **0.4242 / n=64** on intention weighted-F1 (reuse
`scratchpad/baseline_intent_f1.py` as the harness), with 买入 recall as the primary lever, while keeping
the capital_type proxy byte-identical (§6).

---

## 6. Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Capital_type proxy regression** | — | Impossible by construction: `get_intention` does not touch `score_capital_type`. Verify `0.6971/n=65` & `0.6599/n=24` are **byte-identical** after the change (confirms scope discipline). |
| **No offline signal** (proxy is intention-blind) | **High** | Add the §5 intention-F1 gate; do **not** rely on the capital_type proxy to validate this slice. |
| **Over-prediction of directional intent** (sign-gate → T0 0%) | High | Symmetric band τ with a real neutral zone; calibrate τ to the truth prior (~44% T0), not to extremes. |
| **τ calibrated on labels = overfit / compliance** | Medium | Calibrate on **our LHB validation labels** (allowed, same as capital_type gate), never on the platform/Tianchi score. Keep τ a single interpretable constant from the net-direction distribution. |
| **`intent_confidence` still imbalance-based** (`label.py:_intent_confidence`) | Low | Confidence feeds `model.py` weighting, not the submitted label. Keep change minimal; decide whether to re-base confidence in the probe. |
| **`obp_imbalance_mean` negative bias is a real data bug** | Medium (separate) | Out of scope here; the band fix sidesteps imbalance entirely so it is unaffected. File a separate read-only probe. |

---

## 7. Proposed Phase B scope (for approval — not yet dispatched)

- **Files:** `src/rules.py` (`get_intention`) + `tests/test_rules.py` (intent cases) **only**. Possibly
  `scripts/validate_offline.py` to *report* (not gate on) an intention-F1, or a separate read-only script.
- **Forbidden:** `cluster.py`, `validation_labels.csv` (human-only), `score_capital_type`, any tuning to
  Tianchi/0.3600.
- **Acceptance:**
  1. capital_type proxy **unchanged** — `0.6971/n=65` and `0.6599/n=24` byte-identical.
  2. **intention weighted-F1 (n=64) beats the measured baseline 0.4242** materially (primary lever:
     买入 recall, currently 0.185).
  3. intention distribution on 20260623 moves from 7% → ~40–55% directional **without** collapsing the
     neutral zone (T0 stays a meaningful plurality, near the ~44% truth prior).
  4. Suite green (163+ passed, 2 xfailed); new intent tests are discriminating.
- Regenerate `outputs/20260623/{predict_result.csv,submit.zip}`; report offline metrics only — **human
  holds the upload; do not claim any board score.**

---

## 8. Open question for the human (gate)

The proposed fix **drops the imbalance hard-gate**. Two equally-compliant directions if you'd rather keep
imbalance involved:
- **(A) Band-only on net-direction** (recommended) — cleanest, removes the biased signal.
- **(B) Recenter imbalance** to its panel median before the ±gate, keeping it as a second confirming
  axis — preserves a two-signal design but is fragile if the obp bias is a sign bug (§3 flag).

Recommend **(A)**; **(B)** documented as the conservative alternative the probe could A/B.
