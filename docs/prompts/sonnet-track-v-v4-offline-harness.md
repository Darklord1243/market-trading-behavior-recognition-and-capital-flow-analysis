# Sonnet execution prompt — Track V V.4 (offline validation harness)

> **Status:** Ready to run **once `src/validate.py` exists** (it does — Track V V.1–V.2, commit `719ebaa`).
> Useful immediately against EXAMPLE rows + the documented contract; produces a *real* proxy-F1 only after
> **V.3** seeds real labels. **LIS v1.5.5** §6 **Track V**, task **V.4 only**.
>
> **Sequencing (Batch 3):** **V.4 (this) ‖ V.3 (human labels)** run in parallel → Track L-c (gated on the proxy-F1
> this harness reports). V.4 can be **built and tested now** (against EXAMPLE rows + the contract) with no real
> labels; it only *reports a real number* after V.3 lands. **Do not wait on V.3 to start.** See `WORKFLOW.md` Batch 3.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Track V task V.4 only** — an **offline-only**
validation harness `scripts/validate_offline.py` that runs the pipeline on labeled `(stock, day)` keys, joins the
output to the truth CSV, and prints proxy-F1 via the existing `src/validate.weighted_f1` scorer.

**Read (minimal):**
- `docs/LIS.md` §6 **"Track V — Offline validation & label-truth proxy"** (V.4 task) + §3 compliance (#1, #3, #4)
- `src/validate.py` (`weighted_f1` — you **call** it, do not modify it)
- `src/ingest_local.py` (`load_local`, `read_cancel_frame`, `discover_stocks`) and `src/aggregate.py`
  (`build_feature_matrix(..., cancel_lookup=)`) — how to produce predictions on the **local** path
- `main.py` (read only — to mirror the stage order; **do not import it into the harness inference**)
- `tests/fixtures/validation_labels.csv` (EXAMPLE rows), `docs/prompts/track-v-v3-acceptance-spec.md` (CSV contract)
- This prompt

Do **not** re-read the whole doc tree.

**Out of scope this session:** modifying `src/validate.py`; Track V **V.3** (human labels — see
`track-v-v3-acceptance-spec.md`); Track **L-c**; wiring anything into `main.py`'s inference path; new heavy deps; any
`docs/LIS.md` edit (flag a contradiction in your report, do not change it).

---

# LIS v1.5.5 context (trust these locks; do not re-derive)

| Item | Status |
|---|---|
| **Eval class set (OQ-1 / R2)** | ✅ Resolved — 3-class `{游资, 量化, 散户}`; `散户` scores in weighted F1. |
| **Scorer (V.1–V.2 done, `719ebaa`)** | `src/validate.weighted_f1(pred_df, truth_df) -> dict` — inner-joins on `(stock_code, transaction_date)`, returns `{"weighted_f1": float, "n": int, "per_class": {label: {"precision","recall","f1","support"}}}`. Empty join → `{"weighted_f1": 0.0, "n": 0, ...}`. **Pure & offline.** You **call** it; you do **not** reimplement F1. |
| **Local path (Track L-a/L-b)** | `ingest_local.load_local(root, date, max_stocks=None)` → cleaned multi-stock tick frame; `read_cancel_frame(stock_dir, stock_code)` → cancel frame; `aggregate.build_feature_matrix(df, has_cancel_table=True, cancel_lookup={(code,date): cancel_df})`. This is how to get a real feature matrix for labeled stock-days. |
| **`main.py` inference path** | Reads **xlsx** (`load_raw`); the local-corpus path is **not wired into `main.py`** today. The harness must build predictions itself (local ingest → matrix → label → postprocess), **not** by importing the `main.py` inference entrypoint into a feature path. |
| **Validation labels** | `tests/fixtures/validation_labels.csv` columns: `stock_code, transaction_date, capital_type, capital_intention, source, confidence, notes`. **EXAMPLE rows** use `confidence == 0.0` and a `source` starting with `EXAMPLE` — **exclude them from scoring** (see V.3 acceptance spec). |
| **Compliance** | Offline only. The harness lives in `scripts/`, is **never imported** by `src/` inference modules or `main.py`. It reads **our** labels + **our** pipeline output, **never** the board's backtest answers / `outputs/` leaderboard files. |

---

# Hard rules (auto-DQ if broken)

From LIS §2–§3:

1. **Intraday-only** — the harness is offline post-hoc validation; labels must **never** enter a feature or
   `main.py`. No import of `scripts/validate_offline.py` from any `src/` inference module.
2. **No hard-coding** — generic over `config.CAPITAL_TYPES`; no per-stock label tables; the labeled-key filter is
   data-driven from the CSV, not a hand-listed stock set.
3. **No answer-feedback** — compares pipeline output to **our** hand labels only; never reads the platform instant
   score / backtest answers; never tunes anything (it only *prints* a number).
4. **Reproducible** — `config.RANDOM_SEED`; relative paths; no LLM; deterministic given the same inputs.
5. **Locked labels** — operate over `{游资, 量化, 散户}` exactly; do not invent/translate class strings.

---

# What to build

## Goal (LIS §6 Track V, V.4)

A CLI script `scripts/validate_offline.py` that: (1) loads the truth CSV, (2) drops EXAMPLE/zero-confidence rows,
(3) obtains pipeline `capital_type` predictions for the labeled `(stock, day)` keys, (4) calls
`validate.weighted_f1(pred_df, truth_df)`, (5) prints `weighted_f1`, `n`, and a per-class P/R/F1/support table.
It is the instrument every later phase (L-c, Phase 3 batches) uses to report a **proxy-F1 before/after** delta.

## Files

| Action | Path |
|--------|------|
| Create | `scripts/validate_offline.py` (CLI harness — offline only) |
| Create | `tests/test_validate_offline.py` (unit-test the join/filter layer without real labels) |
| Create (if missing) | `scripts/__init__.py` **only if** import of the harness module in the test needs it (prefer importing by path / function; avoid making `scripts` a package if `main.py` doesn't) |
| Do NOT touch | `src/validate.py`, `main.py`, `tests/fixtures/validation_labels.csv`, any `src/` inference module |

> Check whether `scripts/` is already a package (an `__init__.py` exists) before adding one — match the repo.

## CLI contract

```
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input <SOURCE>
```

- `--labels PATH` — truth CSV (default `tests/fixtures/validation_labels.csv`).
- `--input SOURCE` — one of:
  - `local:<root>` — run the **local** ingest pipeline (`ingest_local.load_local`) over the dates present in the
    labels, build the matrix **with `cancel_lookup`** (so CB is real), label, and use the resulting `capital_type`
    as predictions. `<root>` defaults to `data` (e.g. `local:data` or just `local`).
  - `<path/to/pred_result.csv>` — a precomputed prediction CSV (columns incl. `stock_code, transaction_date,
    capital_type`); the harness joins it to truth directly (no ingest run). Useful in CI and when predictions
    already exist in `outputs/`.
- Optional: `--min-confidence FLOAT` (default `0.0` → keep all non-EXAMPLE rows; raise to weight only stronger labels),
  `--date YYYYMMDD` (restrict to one day).
- Exit code: `0` on success (including the "only EXAMPLE rows → skip" case, which is **not** an error); non-zero only
  on a real failure (missing files, malformed CSV). Document the choice in the module docstring.

## Prediction sourcing (the local path)

For `--input local:<root>`:
1. Read distinct `(transaction_date)` values from the **filtered** labels.
2. For each date: `df = ingest_local.load_local(root, date)`; build `cancel_lookup` by calling
   `read_cancel_frame(stock_dir, code)` per discovered stock (mirror how tests in `tests/test_features.py` build it),
   then `matrix = aggregate.build_feature_matrix(df, has_cancel_table=True, cancel_lookup=cancel_lookup)`.
3. Produce `capital_type` via the **same** Stage-2 path the pipeline uses (`label.weak_label_matrix` →
   `postprocess.assemble_predict` or the minimal subset that yields `capital_type` per `(stock, day)`). Reuse
   existing functions; **do not** re-implement scoring.
4. Restrict predictions to the labeled keys and hand `(pred_df, truth_df)` to `weighted_f1`.

> If reproducing the full Stage-2 wiring is heavy, it is acceptable to import and call the existing
> `label`/`postprocess` functions directly (they are not the *inference entrypoint* `main.py`; reusing library
> functions is fine and is **not** a compliance violation). The only forbidden thing is putting labels **into**
> features or tuning to board answers.

## Output format (print to stdout)

```
Track V offline proxy-F1 — labels=<path>, input=<source>
  scored n = <N> (stock, day) pairs   [dropped <E> EXAMPLE/low-confidence rows]
  weighted_f1 = 0.xxxx
  per class:
    游资   P=0.xx R=0.xx F1=0.xx  support=<k>
    量化   P=0.xx R=0.xx F1=0.xx  support=<k>
    散户   P=0.xx R=0.xx F1=0.xx  support=<k>
```

When **no scorable rows remain** (only EXAMPLE rows, or join empty):

```
Track V offline proxy-F1 — no scorable labels (only EXAMPLE / zero-confidence rows, or no key overlap).
Seed real rows via docs/human_guides/track_v_validation_labels.md (V.3). Skipping — not an error.
```

(exit 0)

---

# TDD workflow (one failing test → fail → minimal impl → pass → commit)

The discriminating tests must run **without real labels in CI** — exercise the join/filter/format layer with
**inline** DataFrames / a tiny temp CSV, not the live `validation_labels.csv`.

1. **V4.1** Write `tests/test_validate_offline.py::test_example_rows_are_dropped` (**fail first**): a tiny in-memory
   labels frame with 2 EXAMPLE rows (`confidence==0.0`, `source` startswith `EXAMPLE`) + 2 real rows → the harness's
   label-loader (e.g. `load_truth_labels(path_or_df)`) returns **only** the 2 real rows. Run → **FAIL** (module/func
   absent).
2. **V4.2** Implement the label loader + EXAMPLE/zero-confidence filter in `scripts/validate_offline.py`. Run → pass.
3. **V4.3** `test_pred_csv_path_scores_via_weighted_f1`: given a tiny truth frame and a tiny **pred CSV** that share
   keys, the harness's join layer returns the same `weighted_f1`/`n` as calling `validate.weighted_f1` directly on
   the filtered frames (assert equality — proves the harness *uses* the real scorer, doesn't re-derive). Run → pass.
4. **V4.4** `test_only_example_rows_prints_skip_and_exits_zero`: labels = EXAMPLE-only → harness reports the skip
   message and the runnable entrypoint returns exit code 0 (capture via a `main(argv)->int` function called directly;
   do **not** require a real local corpus). Run → pass.
5. **V4.5** (optional, guarded) `test_local_source_smoke`: if `tests/fixtures/local_l2_tiny` is present, point a tiny
   inline label row at `000001.SZ`/`20260611`, run `--input local:tests/fixtures/local_l2_tiny`, and assert a dict
   with `weighted_f1` and `n>=1` comes back. Skip (`pytest.mark.skipif`) if the fixture is absent so CI never breaks.
6. **V4.6** Full suite + a manual harness run:
   ```bash
   pytest tests/test_validate_offline.py -q
   pytest tests/ -q
   python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:tests/fixtures/local_l2_tiny
   # ^ with EXAMPLE-only labels this prints the skip message and exits 0
   ```

**Structure tip:** put logic in importable functions (`load_truth_labels`, `predict_for_keys`, `run(argv)->int`) so
tests call them directly; keep `if __name__ == "__main__": sys.exit(run(sys.argv[1:]))` thin.

**Commit message (if committing):** `feat: offline Track V proxy-F1 harness (Track V V.4)`

---

# Acceptance criteria (Track V V.4 only — copy into your report)

- [ ] `scripts/validate_offline.py` exists with the documented CLI (`--labels`, `--input local:<root>` and
      `--input <pred_csv>`, optional `--min-confidence`/`--date`)
- [ ] EXAMPLE rows (`confidence==0.0` / `source` startswith `EXAMPLE`) are **excluded** from scoring
- [ ] Harness **calls** `src/validate.weighted_f1` (does not re-implement F1); per-class table printed
- [ ] EXAMPLE-only / empty-join case prints the skip message and exits **0** (not an error)
- [ ] Tests use **inline frames / temp CSV**, not the live `validation_labels.csv`; local-source test is `skipif`-guarded
- [ ] `scripts/validate_offline.py` is **not imported** by `main.py` or any `src/` inference module (grep-clean)
- [ ] Full suite green (baseline **101**; count may increase)
- [ ] No new heavy dependencies (`sklearn`/`pandas` already present)

**Not required this session:** V.3 human labels; Track L-c; wiring the local path into `main.py`; reporting a *real*
proxy-F1 number (that needs V.3 — until then EXAMPLE-only → skip is the expected behavior).

---

# Style

- Match existing `src/`/`scripts/` conventions (`from __future__ import annotations`, type hints, module docstring
  stating **offline / post-hoc / never in inference path**).
- Test-first; small commits. Delete throwaway debug scripts.
- On Windows, console Chinese may mojibake — verify on-disk content is UTF-8; assert via `config.CAPITAL_TYPES`
  membership, not by eyeballing the console.

---

# When done, report

1. Commands run + pass/fail output (paste counts)
2. Files created/changed (list)
3. Acceptance checklist (checked)
4. How predictions are sourced on `--input local:` (which existing `label`/`postprocess` functions you reused)
5. Confirm the grep: `scripts/validate_offline.py` not imported by `main.py` / `src/` inference
6. Did the EXAMPLE-only run print the skip message + exit 0? (paste it)
7. Anything that contradicted LIS (if none, say so)
8. **Next hint:** once V.3 seeds ≥8 real rows, re-run the harness to capture the baseline proxy-F1 that Track L-c
   (proxy→true fast-cancel) must move to PASS its gate.

Begin with the first failing test (V4.1).
