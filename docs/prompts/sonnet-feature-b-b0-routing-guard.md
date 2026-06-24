# Sonnet execution prompt — Feature B slice B.0 (retail routing + relative guard)

> **Status:** Ready to run.
> **Spec:** `docs/superpowers/specs/2026-06-22-retail-dispersion-feature-design.md` §B.0, §2, §5
> **Plan:** `docs/superpowers/plans/2026-06-22-retail-dispersion-feature.md` — **Task B.0 only**
> **Out of scope:** B.1 composite, B.2 entropy, RS-on-逐笔, label edits, threshold fitting, committing.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **Feature B slice B.0 only** — rewire
`DIMS_RETAIL` to the three diagnostic-confirmed retail separators and replace the absolute 散户 veto with a
**relative win margin**, so 散户 recall climbs off 0/10 without breaking 游资/量化.

**Read (minimal — do NOT re-read the whole repo or LIS end-to-end):**
- `docs/superpowers/plans/2026-06-22-retail-dispersion-feature.md` — **Task B.0 steps 1-12** (your script;
  complete test + impl code is there)
- `docs/superpowers/specs/2026-06-22-retail-dispersion-feature-design.md` — §B.0, §2 (compliance framing), §5 (gate)
- `src/rules.py`, `tests/test_rules.py`
- `src/label.py` — how `normalize_matrix` → `score_capital_type` is wired (you do not change it)
- `scripts/validate_offline.py` — where `score_rows` + `--verbose-scores` land (plan Steps 8-9)

---

# LIS context (trust these locks; do not re-derive)

| Item | Status |
|---|---|
| **Eval class set (OQ-1)** | ✅ 3-class `{游资, 量化, 散户}`; 散户 scores in weighted F1. The old absolute retail veto was a 2-class hedge — now obsolete. |
| **Baseline (gate to beat)** | `parquet:data/202606`, n=24: `weighted_f1 = 0.3371`, 散户 R = **0/10**. |
| **Diagnostic separators** | 散户 vs others: **high** `oss_small_count_pct`, **low** `oss_mega_count_pct`, **low** `cb_fast_cancel_ratio`. The current `DIMS_RETAIL` instead votes on anti-signals (`oss_small_amount_pct`, `ap_unilateral_intensity`) + dead `rs_*` (cv≈13/burst=0 for all classes on the snapshot path). |
| **Scorer mechanics** | `_class_score` = mean of dim votes; `high_supports=False` → vote `1-v`; absent dim (or CB dim with `cb_available=0`) → NEUTRAL 0.5. 游资/量化 dim sets are **unchanged** in B.0. |
| **Guard change** | `retail_eligible = score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN` (was an absolute `<= NEUTRAL+margin` veto on both). `RETAIL_GATE_MARGIN` → `RETAIL_WIN_MARGIN = 0.05`. |

---

# Hard rules (auto-DQ if broken)

1. **Intraday-only, no label feedback** — do **not** read or edit `tests/fixtures/validation_labels.csv`; the
   harness/diagnostic is offline post-hoc, never in `main.py`'s inference path.
2. **No threshold fitting to labels** — `RETAIL_WIN_MARGIN = 0.05` is carried from the old gate margin and is
   documented as **NOT** fitted to the 24 labels. Do not sweep it against proxy-F1.
3. **游资/量化 dim sets unchanged** in B.0 (only `DIMS_RETAIL` + the guard change).
4. **TDD** — write the failing test first (Step 1), watch it fail (Step 2), then implement (Step 3+).
5. **Do not** implement B.1/B.2; do not touch `src/features.py` or the deal-stream ingest; **do not commit**
   (the Opus lead commits after gate review).

---

# What to build (follow the plan's Task B.0 verbatim — summary here)

1. **New red test** `tests/test_rules.py::test_retail_wins_on_limit_down_diffuse_flow` (plan Step 1) — a diffuse
   limit-down retail dict (high small-count, low mega-count, low fast-cancel, but high unilateral). Must FAIL on
   current code (emits 游资 because score_yz clears the old absolute gate). Asserts `label == RETAIL` and
   `scores[0] > 0.55` (proves the old veto would have blocked it).
2. **Rewire `DIMS_RETAIL`** (plan Step 3):
   - `("oss_small_count_pct", True, False)`
   - `("oss_mega_count_pct", False, False)`
   - `("cb_fast_cancel_ratio", False, True)` — CB-gated; absent → neutral
   Remove from retail: `oss_small_amount_pct`, `ap_unilateral_intensity`, `rs_interval_cv`, `rs_burst_ratio`,
   `pi_time_concentration`. Update the module docstring 散户 bullet to diffuseness priors (not rhythm residual).
3. **Relative guard + constant rename** (plan Step 3): rename `RETAIL_GATE_MARGIN` → `RETAIL_WIN_MARGIN`;
   `retail_eligible = score_rt >= max(score_yz, score_qt) + RETAIL_WIN_MARGIN`.
4. **Fix the test file** (plan Steps 5-6): update the import to `RETAIL_WIN_MARGIN`; add `oss_small_count_pct`
   to `_base()`; **delete** the three old `test_gate_boundary_*` tests + the old
   `test_retail_wins_when_youzi_and_quant_both_weak` / `test_retail_guard_suppresses_residual_for_balanced_quant`,
   and paste the five rewritten relative-margin tests from the plan (limit-down win, both-weak win, balanced-quant
   protected, strong-youzi-beats-close-retail, retail-max-within-margin→runner-up, exact-margin win).
5. **Per-row diagnostic** (plan Steps 8-9): add `score_rows(matrix, truth_df)` to `scripts/validate_offline.py`
   (offline helper returning truth/pred/`[游资,量化,散户]`/`retail_margin`/`eligible`) + a `--verbose-scores`
   CLI flag (parquet path) + an inline-matrix unit test in `tests/test_validate_offline.py`. Offline only; not
   wired into `main.py`.

---

# Gate (run BEFORE and AFTER)

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
conda run -n base --no-capture-output pytest tests/ -q
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 --verbose-scores
```

- **Before (baseline):** `weighted_f1 = 0.3371`, n=24, 散户 R = 0/10.
- **Ship decision is the lead's.** Report whether after: `weighted_f1 > 0.3371` **AND** 散户 recall > 0 **AND**
  `pytest tests/` green. (On this Windows/GBK box always use `--no-capture-output`; console Chinese may mojibake
  — trust on-disk UTF-8 / `config.CAPITAL_TYPES` membership, not the console glyphs.)

---

# Files

| Action | Path |
|---|---|
| Modify | `src/rules.py` (`DIMS_RETAIL`, `RETAIL_WIN_MARGIN`, guard, docstring) |
| Modify | `tests/test_rules.py` (import, `_base()`, rewritten guard tests) |
| Modify | `scripts/validate_offline.py` (`score_rows`, `--verbose-scores`) |
| Modify | `tests/test_validate_offline.py` (inline-matrix `score_rows` test) |
| **Do NOT touch** | `tests/fixtures/validation_labels.csv`, `src/features.py`, `src/ingest_parquet.py`, `src/label.py`, `main.py`, anything B.1/B.2 |

---

# When done, report (for the Opus gate review — do NOT commit)

1. Commands run + pass/fail counts (`pytest tests/ -q` before & after).
2. **Before/after** `weighted_f1` + per-class P/R/F1 (paste the harness output).
3. The full **per-row score table** (all 24 keys) from `--verbose-scores`.
4. Which 散户 names flipped to 散户, and the **attribution** for each: did `score_rt` rise above the others
   (feature rewire) or was it already highest but newly **eligible** under the relative margin (guard change)?
5. Confirm `pytest tests/` green; confirm `scripts/validate_offline.py` still not imported by `main.py` / `src/`
   inference (grep).
6. Anything that contradicted the spec/plan (if none, say so) — propose a one-line fix, do not diverge silently.

Begin with the first failing test (plan Step 1).
