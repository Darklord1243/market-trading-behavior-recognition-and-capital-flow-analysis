# Feature B (散户 dispersion) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
> **Spec:** `docs/superpowers/specs/2026-06-22-retail-dispersion-feature-design.md` (commit `8ed8124`).

**Goal:** Give 散户 a *positive* L2 signal so its recall climbs off 0/10, by (B.0) rewiring `DIMS_RETAIL` to
diagnostic-confirmed separators + replacing the absolute retail veto with a relative win margin, then (B.2)
adding a deal-stream trade-size-heterogeneity entropy feature.

**Architecture:** Stage-1 scorer (`src/rules.py`) votes per-class over normalized feature dims; `src/label.py`
runs it on the rank-normalized matrix. B.0 is pure scoring-logic (no new feature math). B.2 adds one feature
sourced from the `逐笔成交` parquet stream via `src/ingest_parquet.py`. Every slice is gated on the offline
Track-V proxy-F1 (`scripts/validate_offline.py --input parquet:data/202606`, n=24).

**Tech Stack:** Python, pandas, numpy, pytest; conda env `base`; parquet corpus `data/202606` (0617+0618).

**Commit policy (this engagement):** the **Opus lead commits** after reviewing the gate. Sonnet does **not**
commit — each slice ends by reporting evidence. (Plan steps therefore end in a gate+report step, not `git
commit`.)

**Gate (run before AND after every slice):**
```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
conda run -n base --no-capture-output pytest tests/ -q
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```
Baseline (before B.0): `weighted_f1 = 0.3371` (n=24), 散户 R = 0/10. **Ship a slice iff** after:
`weighted_f1 > prior_committed_f1` **AND** 散户 recall > 0 **AND** `pytest` green.

---

## File structure

| File | Responsibility | Slice |
|---|---|---|
| `src/rules.py` | `DIMS_RETAIL` dims; `RETAIL_WIN_MARGIN`; relative guard | B.0 |
| `tests/test_rules.py` | rewritten guard/retail tests (relative-margin semantics) | B.0 |
| `scripts/validate_offline.py` | `--verbose-scores` per-row score/guard attribution (offline) | B.0 |
| `tests/test_validate_offline.py` | unit test for the `score_rows` formatter (inline matrix) | B.0 |
| `src/ingest_parquet.py` | surface per-print `逐笔成交` sizes into `compute_daily_features` | B.2 |
| `src/features.py` | `trd_size_entropy` feature | B.2 |
| `config.py` | B.2 size-bin edges (global constant, documented not-label-fitted) | B.2 |
| `tests/test_features.py`, `tests/test_ingest_parquet.py` | B.2 red-first tests | B.2 |

---

## Task B.0 — retail routing correctness + relative guard

**Files:**
- Modify: `src/rules.py`
- Modify: `tests/test_rules.py`
- Modify: `scripts/validate_offline.py`
- Test: `tests/test_validate_offline.py`

### Reference: scoring mechanics (so the test values are predictable)

`_class_score(feat, dims, cb_available)` = mean over dims of the dim's vote, where a dim
`(key, high_supports, is_cb)` votes `clip01(feat[key])` if `high_supports` else `1 - clip01(feat[key])`;
an **absent** dim (missing/NaN, or `is_cb=True` while `cb_available` is false) votes **0.5 (NEUTRAL)**.
New `DIMS_RETAIL` = `[("oss_small_count_pct", True, False), ("oss_mega_count_pct", False, False),
("cb_fast_cancel_ratio", False, True)]`. 游资/量化 dim sets are **unchanged**.

- [ ] **Step 1: Write the new discriminating test (red first)**

Add to `tests/test_rules.py` (do **not** change imports yet — this test asserts behavior only):

```python
def test_retail_wins_on_limit_down_diffuse_flow():
    # The B.0 target case: a diffuse limit-down retail name. High small-order COUNT
    # share, few mega prints, low fast-cancel — but HIGH unilateral intensity (one-
    # sided limit-down). Under the OLD absolute gate, score_yz clears NEUTRAL+0.05
    # and VETOES 散户 -> 游资. Under the new relative win-margin guard, 散户 beats both
    # alternatives by > margin and wins. This test FAILS on the current code.
    feat = _base()
    feat.update({
        "cb_available": 1.0,
        "oss_small_count_pct": 0.95, "oss_mega_count_pct": 0.10,
        "cb_fast_cancel_ratio": 0.05,
        # one-sided limit-down character feeds 游资 high / 量化 low:
        "oss_mega_amount_pct": 0.7, "ap_active_buy_pct": 0.7,
        "ap_unilateral_intensity": 0.9, "pd_max_price_impact_pct": 0.7,
        "pi_time_concentration": 0.7, "obp_big_quote_share": 0.7,
        "rs_interval_cv": 0.7, "cb_sell_cancel_ratio": 0.7,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL, f"limit-down retail misclassified: {scores}"
    assert scores[2] == max(scores)
    # The discriminator vs the old guard: 游资 is ABOVE the old absolute gate (0.55),
    # so the old code would have vetoed 散户. Pin that so a revert is caught.
    assert scores[0] > 0.55
```

- [ ] **Step 2: Run it → verify it FAILS**

Run: `conda run -n base --no-capture-output pytest tests/test_rules.py::test_retail_wins_on_limit_down_diffuse_flow -q`
Expected: FAIL — current code emits 游资 (old absolute gate vetoes 散户 because `scores[0] > gate`).

- [ ] **Step 3: Rewire `DIMS_RETAIL` + rename constant + relative guard (`src/rules.py`)**

Replace the `DIMS_RETAIL` block:

```python
# 散户: retail DIFFUSENESS — positive signal (not an inverse residual). Many small
# orders by COUNT, few mega prints, and (CB-gated) a LOW fast-cancel rate (retail is
# not an algo). These are the diagnostic-confirmed separators (see design spec §1.1);
# the old rhythm/inverse dims (rs_*, ap_unilateral LOW, oss_small_amount) were dead or
# anti-signal on the real cross-section and were removed.
DIMS_RETAIL = [
    ("oss_small_count_pct", True, False),     # many small orders by count
    ("oss_mega_count_pct", False, False),     # few mega prints
    ("cb_fast_cancel_ratio", False, True),    # retail rarely fast-cancels [CB]
]
```

Replace the `RETAIL_GATE_MARGIN` constant + its block comment:

```python
NEUTRAL = 0.5  # an absent feature casts no vote: +0.5 to that class score
# 散户 wins only when its OWN evidence beats BOTH 游资 and 量化 by this margin (a
# RELATIVE win margin, not an absolute veto). This preserves the "no accidental
# residual win" hedge while removing the obsolete absolute gate, which mis-fired on
# limit-down names (high ap_unilateral_intensity pushed score_yz above the old gate
# and vetoed a genuine 散户). OQ-1 resolved the 3-class question, so the absolute
# hedge is no longer needed. Global constant; value carried from the old gate margin
# and is NOT fitted to labels.
RETAIL_WIN_MARGIN = 0.05
```

Replace the guard block inside `score_capital_type`:

```python
    # Retail guard (relative): 散户 eligible only when its score beats BOTH 游资 and
    # 量化 by RETAIL_WIN_MARGIN. Otherwise the arg-max is between 游资/量化 only.
    retail_eligible = score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN
    eligible = [0, 1, 2] if retail_eligible else [0, 1]

    best = max(eligible, key=lambda i: scores[i])
    return CAPITAL_TYPES[best], scores
```

Also update the module docstring 散户 bullet (lines ~9-11) to describe diffuseness (many small-count orders,
few mega, low fast-cancel) instead of the rhythm residual, and drop the "量化/散户 split is RHYTHM-based" note.

- [ ] **Step 4: Run the new test → verify it PASSES**

Run: `conda run -n base --no-capture-output pytest tests/test_rules.py::test_retail_wins_on_limit_down_diffuse_flow -q`
Expected: PASS. (Other tests in the file are now broken — fixed in Step 5/6.)

- [ ] **Step 5: Fix the import + `_base()` in `tests/test_rules.py`**

Change the import:

```python
from src.rules import (
    NEUTRAL,
    RETAIL_WIN_MARGIN,
    get_intention,
    score_capital_type,
)
```

Add `oss_small_count_pct` to `_base()` so the new retail dim is present (neutral-ish baseline):

```python
def _base():
    """A neutral-ish feature dict (snapshot-only: no cancel table)."""
    return {
        "oss_mega_amount_pct": 0.2, "oss_mega_count_pct": 0.2,
        "oss_small_amount_pct": 0.2, "oss_small_count_pct": 0.2,
        "ap_active_buy_pct": 0.5,
        "ap_unilateral_intensity": 0.2, "pd_max_price_impact_pct": 0.2,
        "pi_time_concentration": 0.2, "obp_big_quote_share": 0.2,
        "rs_interval_cv": 0.2, "rs_burst_ratio": 0.2, "cb_available": 0.0,
    }
```

- [ ] **Step 6: Rewrite the guard/retail tests for relative-margin semantics**

Replace the five tests below (the old absolute-gate tests `test_gate_boundary_*` and
`test_retail_wins_when_youzi_and_quant_both_weak` / `test_retail_guard_suppresses_residual_for_balanced_quant`)
with these. **Delete** the three old `test_gate_boundary_*` tests and the old
`test_retail_wins_when_youzi_and_quant_both_weak` / `test_retail_guard_suppresses_residual_for_balanced_quant`;
paste these in their place. `test_returns_three_scores`, `test_youzi_wins_on_size_and_aggression`,
`test_quant_wins_on_machine_rhythm`, `test_absent_cb_dims_vote_neutral`,
`test_confidence_is_top1_minus_top2_margin`, `test_intention_gate_unchanged` stay as-is.

```python
def test_retail_wins_when_youzi_and_quant_both_weak():
    # Diffuse retail with both real classes weak: high small-count, few mega, neutral
    # cancel (no cancel table). 散户 beats both by margin -> wins.
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.9, "oss_mega_count_pct": 0.05,
        "ap_unilateral_intensity": 0.2, "pi_time_concentration": 0.2,
        "oss_small_amount_pct": 0.2, "rs_burst_ratio": 0.2, "rs_interval_cv": 0.3,
    })
    label, scores = score_capital_type(feat)
    assert label == RETAIL
    assert scores[2] == max(scores)


def test_balanced_quant_not_stolen_by_retail():
    # Retail-ish count profile, but strong machine evidence (small-amount, burst, low
    # CV, balanced, HIGH fast-cancel). 量化 dominates; 散户 fails the win margin.
    feat = _base()
    feat.update({
        "cb_available": 1.0,
        "oss_small_count_pct": 0.8, "oss_mega_count_pct": 0.1,
        "cb_fast_cancel_ratio": 0.9,            # HIGH -> 量化; LOW-supports -> hurts 散户
        "oss_small_amount_pct": 0.9, "rs_burst_ratio": 0.9,
        "rs_interval_cv": 0.1, "ap_unilateral_intensity": 0.1,
    })
    label, scores = score_capital_type(feat)
    assert label == QUANT, f"balanced quant leaked into retail: {scores}"


def test_strong_youzi_beats_close_retail():
    # 游资 strong; 散户 substantial but does NOT beat 游资 by the win margin -> 游资 wins.
    # (Under the old absolute gate this also resolved to 游资, but here the reason is the
    # RELATIVE margin: score_rt < score_yz, so 散户 is ineligible.)
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.6, "oss_mega_count_pct": 0.2,
        "oss_mega_amount_pct": 0.8, "ap_active_buy_pct": 0.8,
        "ap_unilateral_intensity": 0.8, "pd_max_price_impact_pct": 0.8,
        "pi_time_concentration": 0.8, "obp_big_quote_share": 0.8,
        "rs_interval_cv": 0.8,
    })
    label, scores = score_capital_type(feat)
    assert label == YOUZI
    assert scores[2] < max(scores[0], scores[1]) + RETAIL_WIN_MARGIN


def test_retail_max_but_within_margin_yields_runner_up():
    # 散户 is the RAW arg-max but only by < RETAIL_WIN_MARGIN over 量化 -> ineligible ->
    # 量化 (the runner-up) wins. Pins the relative-margin semantics from the other side.
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.95, "oss_mega_count_pct": 0.10,   # retail ~0.783
        "oss_small_amount_pct": 0.8, "rs_burst_ratio": 0.8,
        "rs_interval_cv": 0.2, "ap_unilateral_intensity": 0.2,     # quant ~0.74
    })
    label, scores = score_capital_type(feat)
    assert scores[2] == max(scores)                                # 散户 is raw max
    margin = scores[2] - max(scores[0], scores[1])
    assert 0.0 < margin < RETAIL_WIN_MARGIN                        # ...but within margin
    assert label == QUANT                                          # runner-up wins


def test_retail_wins_at_exact_win_margin():
    # Boundary: score_rt sits exactly at max(others)+RETAIL_WIN_MARGIN. The guard uses
    # >=, so 散户 stays eligible and wins. (If float representation makes this ambiguous,
    # nudge oss_small_count_pct up by 0.001 — the point is to pin the >= boundary.)
    feat = _base()
    feat.update({
        "oss_small_count_pct": 0.90, "oss_mega_count_pct": 0.15,   # retail = 0.75
        "oss_small_amount_pct": 0.75, "rs_burst_ratio": 0.75,
        "rs_interval_cv": 0.25, "ap_unilateral_intensity": 0.25,   # quant = 0.70
    })
    label, scores = score_capital_type(feat)
    assert scores[2] == max(scores)
    assert label == RETAIL
```

- [ ] **Step 7: Run the full rules test file → verify it PASSES**

Run: `conda run -n base --no-capture-output pytest tests/test_rules.py -q`
Expected: PASS (all rules tests green under the new semantics).

- [ ] **Step 8: Add the `score_rows` formatter + unit test (offline per-row attribution)**

Add to `scripts/validate_offline.py` (module-level helper — pure, offline):

```python
def score_rows(matrix: "pd.DataFrame", truth_df: "pd.DataFrame") -> list[dict[str, Any]]:
    """Per-(stock, day) score triple + retail-guard attribution (offline diagnostic).

    Returns one dict per matrix row: stock_code, transaction_date, truth, pred,
    scores=[游资,量化,散户], retail_margin = score_rt - max(score_yz, score_qt),
    eligible (margin >= RETAIL_WIN_MARGIN). Runs the SAME normalize -> score path the
    label stage uses; offline only, never imported by main.py.
    """
    from src.normalize import normalize_matrix
    from src.rules import RETAIL_WIN_MARGIN, score_capital_type

    norm = normalize_matrix(matrix)
    tmap = {
        (str(r.stock_code), str(r.transaction_date)): r.capital_type
        for r in truth_df.itertuples()
    }
    rows: list[dict[str, Any]] = []
    for idx, r in norm.iterrows():
        code, date = idx if isinstance(idx, tuple) else (idx, "")
        pred, scores = score_capital_type(r.to_dict())
        margin = scores[2] - max(scores[0], scores[1])
        rows.append({
            "stock_code": str(code),
            "transaction_date": str(date),
            "truth": tmap.get((str(code), str(date)), "?"),
            "pred": pred,
            "scores": [round(float(s), 3) for s in scores],
            "retail_margin": round(float(margin), 3),
            "eligible": bool(margin >= RETAIL_WIN_MARGIN),
        })
    return rows
```

Add to `tests/test_validate_offline.py` (inline matrix — no parquet/network):

```python
import pandas as pd
from scripts.validate_offline import score_rows


def test_score_rows_reports_triple_and_margin():
    # Two clearly-separated rows so ranks are deterministic.
    matrix = pd.DataFrame(
        {
            "oss_small_count_pct": [0.9, 0.1],
            "oss_mega_count_pct": [0.1, 0.9],
            "oss_mega_amount_pct": [0.1, 0.9],
            "ap_unilateral_intensity": [0.1, 0.9],
            "cb_available": [0.0, 0.0],
        },
        index=pd.MultiIndex.from_tuples(
            [("000010.SZ", "20260617"), ("000725.SZ", "20260617")],
            names=["stock_code", "transaction_date"],
        ),
    )
    truth = pd.DataFrame({
        "stock_code": ["000010.SZ", "000725.SZ"],
        "transaction_date": ["20260617", "20260617"],
        "capital_type": ["散户", "游资"],
    })
    rows = score_rows(matrix, truth)
    assert len(rows) == 2
    r0 = next(r for r in rows if r["stock_code"] == "000010.SZ")
    assert r0["truth"] == "散户"
    assert len(r0["scores"]) == 3
    assert "retail_margin" in r0 and "eligible" in r0
    assert isinstance(r0["eligible"], bool)
```

- [ ] **Step 9: Wire `--verbose-scores` into the CLI (parquet path)**

In `scripts/validate_offline.py`, add the argument in `run()` (near the other `add_argument` calls):

```python
    parser.add_argument(
        "--verbose-scores",
        action="store_true",
        dest="verbose_scores",
        help="Print per-(stock,day) score triple + retail-guard attribution (parquet input; offline).",
    )
```

After the `_print_result(...)` call in `run()` (only when scores were produced), append:

```python
    if args.verbose_scores and args.input.strip().lower().startswith("parquet"):
        root = args.input.split(":", 1)[1].strip() or "data/202606" if ":" in args.input else "data/202606"
        extra = _resolve_norm_universe_codes(norm_universe_path=args.norm_universe)
        print("  per-row scores [游资,量化,散户] (truth -> pred | margin | eligible):")
        for date in filtered_truth["transaction_date"].astype(str).unique():
            labeled = (
                filtered_truth.loc[filtered_truth["transaction_date"].astype(str) == date, "stock_code"]
                .astype(str).unique().tolist()
            )
            matrix = _build_parquet_matrix(root, date, labeled, extra)
            if matrix.empty:
                continue
            sub = filtered_truth[filtered_truth["transaction_date"].astype(str) == date]
            for row in score_rows(matrix, sub):
                if row["truth"] == "?":
                    continue
                print(f"    {row['stock_code']:<11}{row['transaction_date']:<10}"
                      f"{row['truth']}->{row['pred']:<6} {row['scores']} "
                      f"margin={row['retail_margin']:+.3f} eligible={row['eligible']}")
```

> Note: `--verbose-scores` rebuilds the parquet matrix once more for the dump (the scoring path does not
> surface score triples). That ~doubles runtime when the flag is on — acceptable for a diagnostic.

- [ ] **Step 10: Run the harness/formatter tests → verify they PASS**

Run: `conda run -n base --no-capture-output pytest tests/test_validate_offline.py -q`
Expected: PASS (existing harness tests + the new `score_rows` test).

- [ ] **Step 11: Run the full gate (before/after) and capture evidence**

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
conda run -n base --no-capture-output pytest tests/ -q
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 --verbose-scores
```
Expected: `pytest` green; harness prints `weighted_f1`, per-class table, and the per-row score table.

- [ ] **Step 12: Report to the Opus lead (do NOT commit)**

Report, per spec §5: before/after `weighted_f1` + per-class P/R/F1; the full per-row score table (24 keys);
which 散户 names flipped and whether the flip was driven by the **feature rewire** (score_rt rose) or the
**guard change** (now eligible though score_yz high); confirm `pytest tests/` green; confirm
`validate_offline.py` still not imported by `main.py`/`src/` inference; flag any spec contradiction.
**Ship decision is the lead's:** ship iff `weighted_f1 > 0.3371` AND 散户 R > 0 AND suite green.

---

## Task B.2 — deal-stream trade-size-heterogeneity entropy (PLAN ONLY — do not implement until B.0 ships)

> **Dispatch gate:** start B.2 only after B.0 passes its gate and the lead commits it. The "prior committed
> F1" for B.2's gate is B.0's shipped number, not 0.3371.

**Files:** `src/ingest_parquet.py`, `src/features.py`, `config.py`, `tests/test_ingest_parquet.py`,
`tests/test_features.py`, `src/rules.py` (`DIMS_RETAIL` gains the entropy dim).

**Critical constraint (spec §B.2):** measure **size-VALUE heterogeneity**, NOT volume concentration. 量化 and
散户 both make many small prints; a volume-HHI / inverse-HHI does **not** separate them (uniform algo clips
spread volume evenly too). The discriminator is the spread of the print **size-value** distribution: 量化
repeats a few clip sizes (low size entropy); 散户 has heterogeneous human sizes (high size entropy); 游资 is
mega-skewed.

**Scoped tasks (TDD; expand to bite-sized steps with hand-computed values when B.2 is dispatched):**

1. **`config.py`** — add `TRD_SIZE_BINS` (log-spaced edges over round-lot multiples, e.g. powers of 2 ×100
   shares), a global constant documented as chosen from A-share lot structure, **not** label-fitted.
2. **`src/ingest_parquet.py`** — extend the existing `deal`-stream read (already used by `_bigorder_maps`) to
   surface a per-(stock,day) array/Series of genuine-trade print volumes (exclude cancels/auction by `Side`/
   type flags). Plumb it into `compute_daily_features` the same way `cancel_lookup` is threaded (a
   `deal_lookup` dict `((stock_code, date) -> volumes)`), keeping the xlsx/snapshot path backward-compatible
   (absent -> feature 0.0 + degrade gracefully). Test on a tiny synthetic deal frame.
3. **`src/features.py`** — add `trd_size_entropy`: bin print sizes into `TRD_SIZE_BINS`, compute normalized
   Shannon entropy `H = -Σ p_i ln p_i / ln(B)` over non-empty bins (`p_i` = share of prints in bin i), finite
   in [0,1]; empty/degenerate -> 0.0. Tests (hand-computed): repeated-clip sizes -> low; heterogeneous sizes
   -> high; mega-skewed -> low/skewed.
   - **Ladder-free alternative** to implement if binning proves fragile: `1 - modal_size_share` (share of
     prints at the single most common size). B.2 picks entropy vs modal-share by whichever **both** separates
     散户 from 量化 on the diagnostic AND moves proxy-F1; document the choice.
4. **`src/rules.py`** — add `("trd_size_entropy", True, False)` to `DIMS_RETAIL` (HIGH supports 散户). Re-run
   the rules tests; update `_base()`/affected tests if the new dim shifts a synthetic outcome.
5. **Verify on the diagnostic** (`scripts/_diag_retail_features.py` or `--verbose-scores`) that
   `trd_size_entropy` mean is higher for 散户 than 量化 before trusting the proxy gate.

**Gate:** beat B.0's committed `weighted_f1` on `parquet:data/202606` (n=24), 散户 R > 0, suite green. If it
wins, it stays in `DIMS_RETAIL` (alongside or replacing the B.1 composite). Report before/after + the
散户-vs-量化 entropy means.

---

## Appendix B.1 — `retail_diffuseness_idx` named composite (OPTIONAL — off critical path)

> Pursue only if the lead asks for a reusable named feature (for Phase 4 model / Phase 5 clustering /
> `pattern_explanation`) or a reweighting seam. **Score-equivalent to B.0** under the equal-weight averaging
> scorer, so it is **not** gated on beating B.0 — it ships iff score-neutral (±noise) AND adds reuse value,
> suite green.

**Placement (important):** the composite is **rank-based / cross-sectional** — compute it **after**
`normalize.normalize_matrix` in the scoring path (`src/label.weak_label_matrix`), **NOT** in `features.py`
(which runs per-stock, pre-panel). Formula on normalized inputs:
```
retail_diffuseness_idx = mean( norm[oss_small_count_pct],
                               1 - norm[oss_mega_count_pct],
                               1 - norm[cb_fast_cancel_ratio] )   # CB absent -> neutral 0.5
```
Add a regression test asserting B.1's emitted classes == B.0's on the diagnostic panel (proves
score-equivalence under equal weights). Weights are global constants from microstructure reasoning, never
grid-searched on the 24 labels (compliance #3).

---

## Self-review (writing-plans checklist)

**Spec coverage:** §B.0 dims rewire → Step 3; relative guard → Step 3; per-row diagnostic → Steps 8-9;
gate → Step 11; compliance (no label tuning, 游资/量化 unchanged) → Steps 3/12 + hard rules. §B.2 → Task B.2
(plan-only as required). §B.1 → Appendix (optional). §5 universal gate → header + Step 11. ✅
**Placeholder scan:** B.0 steps contain complete test + impl code; B.2/B.1 are intentionally plan-only/
appendix per the dispatch instruction (B.2 marked "expand to bite-sized when dispatched"). No TBD/TODO in B.0.
**Type/name consistency:** `RETAIL_WIN_MARGIN` (constant), `score_rows(matrix, truth_df)`, `DIMS_RETAIL` keys
(`oss_small_count_pct`, `oss_mega_count_pct`, `cb_fast_cancel_ratio`) used identically across Steps 3/5/6/8 and
the spec. Guard expression `score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN` consistent in Step 3 and
`score_rows`. ✅
