# Feature B — 散户 dispersion / diffuseness — design spec

> **Status:** approved design, ready for implementation planning.
> **Date:** 2026-06-22 · **Lead:** Opus (design/spec/gate) · **Executor:** Sonnet (TDD build per slice).
> **Spec authority:** this doc is subordinate to `docs/LIS.md` (the living spec) and the §2 locks /
> §3 compliance rules therein. On any conflict, LIS + organizer precedence win.

## 1. Problem

On the combined Track-V label set (`tests/fixtures/validation_labels.csv`, n=24 across 20260617/0618),
the honest offline baseline is:

```
parquet:data/202606 (no --date):  weighted_f1 = 0.3371 (n=24)
  游资  R=0.67 F1=0.50  support=6
  量化  R=0.88 F1=0.64  support=8
  散户  R=0.00 F1=0.00  support=10   ← 0 / 10
```

散户 recall is **0 on all 10 retail names**. This is a **feature/definition gap**, not threshold tuning:
`src/rules.py` defines 散户 as an inverse-of-everything RESIDUAL (`DIMS_RETAIL` = small-amount HIGH +
low-aggression + low-burst + high-CV + low-concentration), and a **guarded** residual that only wins when
both 游资 and 量化 are absolutely weak.

### 1.1 Diagnostic evidence (offline EDA, `scripts/_diag_retail_features.py`)

Per-class RAW means over the 24 labeled keys:

| feature | 游资 | 量化 | 散户 | verdict |
|---|---|---|---|---|
| `oss_small_count_pct` | 0.38 | 0.24 | **0.48** | 散户 highest — **separator** |
| `oss_mega_count_pct` | 0.16 | 0.13 | **0.08** | 散户 lowest — **separator** |
| `cb_fast_cancel_ratio` | 0.68 | **0.79** | **0.53** | 散户 lowest — **separator** (CB-gated) |
| `ap_unilateral_intensity` | 0.17 | 0.10 | **0.22** | 散户 **highest** — **ANTI-signal** in current DIMS_RETAIL |
| `oss_small_amount_pct` | 0.027 | 0.026 | **0.012** | 散户 **lowest** — **ANTI-signal** in current DIMS_RETAIL |
| `rs_interval_cv` | 14.0 | 13.9 | 13.3 | **degenerate** (no separation) |
| `rs_burst_ratio` | 0.0 | 0.0 | 0.0 | **degenerate** (all zero) |

Two root causes the diagnostic exposes:

1. **`DIMS_RETAIL` votes on anti-signals.** It rewards `oss_small_amount_pct` HIGH (散户 is *lowest*) and
   `ap_unilateral_intensity` LOW (散户 is *highest*, because the retail names are limit-down / one-sided
   distribution days). The residual literally votes *against* the real retail names → they score 游资.
2. **The rhythm features are dead on the parquet path.** `rs_interval_cv≈13` for all three classes and
   `rs_burst_ratio=0` everywhere, because the parquet cleaned frame is **snapshot rows** (~3s sampling +
   lunch gap), so `_rs_features` measures snapshot cadence, not order rhythm. The real cadence lives in the
   untouched `逐笔成交`/`逐笔委托` streams. (Fixing this is Option 2 — **out of Feature-B scope**, a separate
   RS-on-逐笔 track that also resurrects 量化's rhythm axis.)

## 2. Compliance framing (binds the whole spec)

- Every feature here is motivated by an **established A-share microstructure prior** — retail flow = many
  small orders, rarely cancels, few mega prints, heterogeneous (non-clipped) sizes. The 24-label diagnostic
  **confirms** these priors; it does **not** derive them. We are not reverse-engineering features from labels.
- **No threshold fitting to labels (LIS §3 #3).** Constants (`RETAIL_WIN_MARGIN`, any entropy bin edges) are
  global, documented as *not* label-fitted, and chosen from microstructure reasoning, not a grid search over
  the 24 points.
- **Proxy-F1 on 24 points is a SMOKE TEST, not a leaderboard simulator.** Trust large moves; discount small
  ones as noise. A slice ships only on a clear, same-scheme improvement (§5).
- Intraday-only (#1); no per-stock constants (#2); reproducible, no LLM in inference path (#4).

## 3. North star & slice plan

**North star:** 散户 = **diffuse, non-clipped trade flow.** The principled measure is **trade-size
dispersion** (B.2). Ship cheapest-first; each slice is independently gated and committed.

| Slice | Deliverable | New math? | Role |
|---|---|---|---|
| **B.0** | Routing correctness + relative retail guard | none | Fastest "is the signal real?" test |
| **B.1** | `retail_diffuseness_idx` named composite | low | **Optional, off critical path** — score-equiv to B.0; only for a reusable named feature / reweighting seam |
| **B.2** | Deal-stream **size-heterogeneity entropy** | yes | The real Feature B; replaces B.1 if it wins |
| ~~Opt 2~~ | RS-on-逐笔 memorylessness | — | **Out of scope** — separate track, do not block B |

## 4. Slice specs

### B.0 — routing correctness + relative retail guard

**File:** `src/rules.py` (+ `tests/test_rules.py`). **No new feature math.**

1. **Rewire `DIMS_RETAIL`** to the diagnostic-confirmed separators, motivated by retail priors:
   - `("oss_small_count_pct", True, False)` — many small orders by **count** (not amount).
   - `("oss_mega_count_pct", False, False)` — few mega orders.
   - `("cb_fast_cancel_ratio", False, True)` — retail rarely fast-cancels (CB-gated → absent votes neutral).
   - **Remove from retail:** `oss_small_amount_pct`, `ap_unilateral_intensity`, `rs_interval_cv`,
     `rs_burst_ratio`, `pi_time_concentration`. (游资/量化 dim sets are **unchanged** in B.0 — 游资 keeps
     `ap_unilateral_intensity` HIGH.)
2. **Replace the absolute retail veto with a relative win margin.** OQ-1 resolved the 3-class question
   (Decision-log 2026-06-16), so the guard's original 2-class hedge is obsolete; the absolute veto also
   mis-fires on limit-down names (high `ap_unilateral_intensity` → `score_yz` above the gate → 散户
   disqualified before its score matters).

   ```python
   # old (absolute veto):
   gate = NEUTRAL + RETAIL_GATE_MARGIN
   retail_eligible = (score_yz <= gate) and (score_qt <= gate)
   # new (relative win margin):
   RETAIL_WIN_MARGIN = 0.05   # NOT fitted to labels; preserves "no accidental residual win"
   retail_eligible = score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN
   ```
   Keep the hedge intent ("散户 wins only when its own evidence beats both alternatives"), drop the obsolete
   absolute veto. `RETAIL_GATE_MARGIN` is renamed/repurposed to `RETAIL_WIN_MARGIN`; value 0.05 carried over
   with a comment that it is not label-fitted.
3. **Per-row diagnostic** (in the offline harness / diagnostic script, not inference): for every labeled key
   print `truth, pred, [score_yz, score_qt, score_rt], retail_margin = score_rt - max(score_yz, score_qt),
   eligible, final`. This is how we attribute a miss to feature vs guard.

**Tests (TDD, red first):**
- A synthetic clearly-retail row (high small-count, low mega-count, low fast-cancel, but *high* unilateral
  like a limit-down name) scores 散户 as arg-max under the new guard — and would have been vetoed under the
  old absolute gate (genuine discriminator: the test fails if the guard change is reverted).
- A balanced quant row (high small-count too, but strong 量化 evidence) still scores 量化 (guard still
  prevents accidental residual wins).
- Absent-CB path: `cb_fast_cancel_ratio` absent → votes neutral, retail still computable (regression of
  `test_absent_cb_dims_vote_neutral` stays green).

**Gate:** same-run `parquet:data/202606`, n=24, **weighted_f1 > 0.3371 AND 散户 recall > 0**. Report the
per-row triples. Ship (commit) only if both hold.

**Fallback experiment (documented, not committed unless needed):** if the relative-margin guard still shows
clear 散户 score-wins being blocked, or `RETAIL_WIN_MARGIN=0.05` is too conservative across the diagnostic
rows, evaluate plain 3-way arg-max (remove guard) as an explicit experiment — but B.0's committed candidate
is the relative margin, never plain arg-max by default.

### B.1 — `retail_diffuseness_idx` named composite — OPTIONAL

> **Honest note (spec self-review):** under the current scorer, `_class_score` already **equal-weight
> averages** a class's dims. So B.0's three retail dims are *mathematically identical* to an equal-weight
> `retail_diffuseness_idx` composite — B.1 with equal weights **cannot move proxy-F1 vs B.0**. B.1 is
> therefore **not on the critical path**; the primary path is **B.0 → B.2**. Pursue B.1 only for one of two
> concrete reasons:

- **(a) Named, reusable, explainable feature.** Expose the composite as a first-class column
  `retail_diffuseness_idx` so Phase 4 (model) / Phase 5 (clustering) and `pattern_explanation` can consume a
  single interpretable "retail diffuseness" axis instead of three correlated dims. Score-equivalent to B.0,
  so it is **not gated on beating B.0** — it ships iff it is score-neutral (±noise) AND adds downstream reuse
  value, with the suite green.
- **(b) Reweighting seam.** If B.0 clears the gate only marginally, B.1 is where non-equal weights could be
  introduced — but weights are **global constants chosen from microstructure reasoning, never grid-searched
  on the 24 labels** (#3). Default stays equal weights unless there is a prior-based reason to differ.

**Placement (fixes the ordering bug):** the composite is rank-based and therefore **cross-sectional** — it
must be computed **after** `normalize.normalize_matrix` (which produces the [0,1] ranks), as a derived column
in the scoring path (`label.weak_label_matrix` / `rules`), **not** in `features.py` (which runs per-stock,
pre-panel, with no cross-section). Formula on normalized inputs:
```
retail_diffuseness_idx = mean( norm[oss_small_count_pct],
                               1 - norm[oss_mega_count_pct],
                               1 - norm[cb_fast_cancel_ratio] )   # CB absent → neutral 0.5
```

**Tests:** hand-computed composite on a small normalized panel; high-diffuseness row > low-diffuseness row;
finite in [0,1]; CB-absent uses neutral for the cancel term; a regression asserting B.1's emitted classes ==
B.0's on the diagnostic panel (proves score-equivalence under equal weights).

### B.2 — deal-stream size-heterogeneity entropy (the real Feature B)

**Files:** `src/ingest_parquet.py` (pass per-stock-day print sizes), `src/features.py` (new feature),
`config.py` (bin definition if used), `tests/test_features.py`, `tests/test_ingest_parquet.py`,
`src/rules.py` (`DIMS_RETAIL` gains the entropy dim).

**Critical design constraint — measure SIZE-VALUE heterogeneity, not volume concentration.** 量化 and 散户
*both* make many small prints, so a plain volume-HHI / inverse-HHI (volume spread across prints) does **not**
separate them — 量化's uniform clips spread volume evenly too. The discriminator is the **distribution of
print SIZE VALUES**: 量化 repeats a few algorithmic clip sizes (low size entropy); 散户 has heterogeneous,
human-chosen sizes (high size entropy); 游资 is mega-skewed.

- **Input:** per-print trade volumes from `逐笔成交` (deal stream), genuine trades only (`Side ∈ {buy,sell}`,
  exclude cancels/auction if flagged). `load_parquet` already reads `deal` for `_bigorder_maps`; extend that
  read to surface per-(stock,day) print volumes into `compute_daily_features`.
- **Feature (primary candidate):** normalized Shannon entropy of the print-size distribution over
  **log-spaced size bins** (bin edges a documented global constant, e.g. powers of 2 over round-lot
  multiples — chosen from lot structure, not label search):
  `H = -Σ p_i ln p_i / ln(B)` where `p_i` = share of prints in bin i, B = non-empty bins. 散户 → high.
- **Ladder-free alternative (implement if binning proves fragile):** `1 − modal_size_share` (share of prints
  at the single most common size) — 量化 high modal share → low heterogeneity; 散户 low modal share → high.
- B.2 picks whichever (entropy vs modal-share) **both** (a) separates 散户 from 量化 on the diagnostic AND
  (b) moves proxy-F1; document the choice.

**Tests:** synthetic deal frame with repeated-clip sizes → low entropy; heterogeneous sizes → high entropy;
mega-skewed → low/skewed; finite in [0,1]; cancels excluded; empty/degenerate guarded.

**Gate:** beat the **best committed prior slice** (B.0 or B.1) on `parquet:data/202606`, n=24, 散户 R > 0.
If it wins, it replaces the B.1 composite as the retail diffuseness signal.

## 5. Universal gate (every slice)

Run **before and after** on the identical scheme:

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```

Ship the slice (commit) **iff**: `weighted_f1 > prior_committed_f1` **AND** `散户 recall > 0` **AND** full
`pytest tests/` green. Record before/after + per-class + per-row triples in the commit message and bump
`docs/LIS.md` (changelog + §4 `rules.py`/`features.py` rows). A slice that moves the synthetic panel but not
the proxy (or moves it the wrong way) is **flagged suspect, not shipped** (LIS §6 Track V rule).

## 6. Execution model (lead / worker)

- **Opus (lead):** owns this spec, the implementation plan, the gate decision, LIS maintenance, and commits.
- **Sonnet (worker):** implements each slice **test-first** against this spec + the one `src/` file the slice
  names — does NOT re-read the whole repo (LIS §11 starter). Reports acceptance evidence (command output) +
  before/after proxy-F1; flags any contradiction with this spec rather than diverging silently.
- One slice at a time. **Critical path: B.0 → B.2.** B.1 is optional (dispatch only for reason (a)/(b) in
  its section). Opus runs the gate and commits between slices; Option 2 is not dispatched as part of Feature B.

## 7. Files touched (summary)

- `src/rules.py` — B.0 dims + guard; B.1/B.2 wire the new dim into `DIMS_RETAIL`.
- `src/features.py` — B.1 composite; B.2 entropy feature.
- `src/ingest_parquet.py` — B.2 surfaces per-print deal sizes into `compute_daily_features`.
- `config.py` — B.1 weights, B.2 bin/threshold constants (global, documented not-label-fitted).
- `tests/test_rules.py`, `tests/test_features.py`, `tests/test_ingest_parquet.py` — red-first per slice.
- `docs/LIS.md` — changelog + §4 rows per landed slice.

## 8. Risks / guardrails

- **Tiny-set overfit.** 24 points; proxy-F1 is a smoke test. Mitigate: features from priors not grids;
  trust only clear moves; keep per-row attribution visible.
- **Guard over-correction.** Relative margin could let noisy residual retail win on genuine quant days.
  Mitigate: `RETAIL_WIN_MARGIN` keeps the "beat both" requirement; the quant-row test guards it.
- **B.2 measuring the wrong thing.** Volume-concentration ≠ size-heterogeneity (§B.2). Mitigate: the spec
  pins size-value heterogeneity and requires 散户-vs-量化 separation on the diagnostic before the proxy gate.
- **Snapshot vs tick streams.** B.0/B.1 use snapshot-derived OSS/CB features (already in the matrix); B.2
  reaches into the deal stream. The dead `rs_*` are explicitly *not* relied on by the new retail definition.
```
