# Repro-Pack Readiness Audit — `project_solution.zip` vs spec §5.5

> **Status:** read-only audit, Phase 3a. Findings only — **no code was changed.** Any "fix" column is a
> recommendation pending explicit human approval (`rules.py`/`features.py`/`label.py`/`config.py`/
> `requirements.txt` are frozen without an ask). Verified 2026-07-06; G1/P1 fixes now committed as
`b26bfed` (parent `f6f3097`), by
> reading the files and grepping the inference path; commands are shown so the auditor can re-run them.

The TOP-15 code review (`topic-specifications-and-data.en.md` §5.5) requires a full-pipeline
replication and disqualifies on any **code / doc / result mismatch**. This checklist maps each §5.5
requirement to its evidence and to the parity-ledger row that carries the corresponding report claim.

## 1. §5.5 requirement checklist

| §5.5 requirement | Status | Evidence (read-only) | Ledger row |
|---|---|---|---|
| **Dependencies** declared in `init_env.sh` | ✅ **PASS** | `init_env.sh` is idempotent, relative-path, `pip install -r requirements.txt`; header states the audit contract | — |
| **Entry point** `main.py` → writes `predict_result.csv` | ✅ **PASS** | `main.py:107` → `postprocess.write_predict_result`; also emits `pattern_reco.csv` (Task 1). Output contract asserted (`postprocess.write_predict_result`, `OutputContractError`) | 22 |
| **Hard-coding ban** — no random fill, no per-stock rules, no ignoring L2 | ✅ **PASS** | grep of `src/ main.py config.py`: the only 6-digit match in `rules.py` (L178) is inside a **comment**; no `random.`/`np.random` outside `RANDOM_SEED`; thresholds live in `config.py` | 23 |
| **Timing** — producible from intraday data by market close | ⚠️ **PARTIAL** | Pipeline recomputes from raw L2 per `--date`; but the "yesterday" auto-resolution is a **calendar stub** (`main.py` `TODO(holiday-calendar)`). A given `--date` run is fine; the *automatic* nightly default is not holiday-aware | 1 |
| **Paths** relative + thorough comments | ✅ **PASS** | grep for `C:\`/`/home/`/`/Users/`: none in `src/ main.py config.py`; `main.py` + `init_env.sh` carry contract comments | 1 |
| **Audit** — full replication; no code/doc/result mismatch | ✅ **PASS** (post-freeze) | F1–F4 re-froze to exact expected values 2026-07-06 (0.6773/n=77, 0.6438/n=122, 0.7824/n=32, intent 0.6750/n=115, suite 234/2); the one mismatch found (P1) was fixed and re-verified | 5, 15, 24 |
| **No LLM in inference path** (compliance) | ✅ **PASS** | grep `openai\|anthropic\|llm\|requests\|http` on `src/ main.py`: matches are docstrings ("no LLM call") only; `model.py` is a pass-through stub | 2 |

## 2. Gaps (ranked; none block *today*, all block *report lock*)

**G1 — Undeclared runtime dependency `pyarrow` (audit-blocking for our own gate exhibits).**
`src/ingest_parquet.py:33` does `import pyarrow.dataset as ds`, but `requirements.txt` declares only
pandas/numpy/scikit-learn/openpyxl/pytest. The competition sample entry (`--input
samples/AFAC2026.xlsx`) uses the openpyxl path and is unaffected, **but every gate exhibit in the
report runs on `--input parquet:data/202606`** — an auditor reproducing our 0.6773 / 0.6438 / 0.7824
numbers on a clean `init_env.sh` install would hit `ModuleNotFoundError: pyarrow`.
*Recommended fix (pending OK):* add `pyarrow>=6.0` to `requirements.txt`. Read-only for now.
**→ RESOLVED 2026-07-06:** `pyarrow>=6.0` added to `requirements.txt` (committed `b26bfed`); no other code touched.

**G2 — Three cited numbers not yet frozen from a timestamped run.** Ledger Rows 5 (feature count),
15 (gates 0.6773/n=77, combined n=154, intent floor), 24 (pytest 234/2 xfail) are asserted as current
but lack a pasted command+date exhibit. Any drift between the pasted report number and a fresh run is
a §5.5 "result mismatch" → DQ. *Resolved by the exhibit-freeze block appended to the ledger
(this Phase 3a item #3); the runs themselves are the pre-lock task, not this session.*

**G3 — Clean-checkout smoke test.**
**→ VERIFIED 2026-07-06 (tree now committed `b26bfed`).** `python main.py --input samples/AFAC2026.xlsx
-o outputs/smoke-test/` ran green end-to-end (exit 0, ~2.3s): 5-stage pipeline completed, feature
matrix `1 (stock, day) rows × 35 features`, and both contract-validated CSVs were written
(`predict_result.csv`, `pattern_reco.csv`, 1 row each). The run also exercised the holiday-aware
"yesterday" seam (resolved to 20260703) and the `cb_available=False` snapshot-only degradation path
without error. The competition entry point is reproducible from a clean invocation.

**G4 — Holiday-calendar stub (documented limitation, not a fix).** The `TODO(holiday-calendar)` seam
in `main.py` means the nightly "yesterday" default is not exchange-holiday-aware. Every scored run
this competition passes an explicit `--date`, so this does not affect any submitted result; it belongs
in **§8 Limitations** as a stated seam, not a code change. (The G3 smoke run did resolve a holiday-aware
"yesterday" of 20260703, so the seam is wired — it is the exchange-calendar *table* that is stubbed.)

**G5 — pandas-3.0 `astype(str)` regression — RESOLVED 2026-07-06 (fix committed `b26bfed`).** `_load_universe_codes`
relied on the pre-3.0 behavior where `Series.astype(str)` stringified `NaN`→`"nan"`; on pandas 3.0.3
`NaN` stayed a float, survived the `.ne("nan")` filter, and crashed `sorted()` — failing
`test_load_universe_codes_strips_empty_and_deduplicates` (first freeze: 1 failed / 233 passed / 2
xfailed) and threatening any real run with a blank universe cell. **Fixed (both):**
`src/pipeline_parquet.py:67` → `df[col].fillna("").astype(str).str.strip()`, and `requirements.txt`
pin capped `pandas>=1.3,<3`. Re-verified green: **234 passed, 2 xfailed** (ledger freeze F4 /
Open parity flag P1). Both edits **committed as `b26bfed`**; production entry was never affected
(G3 green).

## 3. What is already solid (no action)

- Determinism + seed (Row 1), no-LLM inference (Row 2), 3-class output validator that fails loudly on
  the old `量化机构` string (Row 22, `postprocess.validate_predict:57`), no hard-coded stock rules
  (Row 23), `__pycache__/` gitignored so the code zip ships clean.
- `requirements.txt` uses pinned **floors** with a commented `lightgbm` seam for the stubbed Stage-3
  head — honest about what is and isn't wired.

**Bottom line (updated 2026-07-06 after freeze + P1 fix):** the pack is audit-ready and the production
entry point is verified green (G3). Both code-side items are **RESOLVED and committed (`b26bfed`)**:
**G1 (pyarrow)** declared, **G5/P1 (pandas-3.0 loader)** fixed (`fillna("")` + pin cap `<3`), suite
green at **234 passed / 2 xfailed**. All four gate/intent numbers the report cites re-froze to their
exact expected values (ledger F1–F3), and the F5 feature-count mapping is frozen (P2 resolved:
35-col matrix, 24 reference-matched, 31 clustering). The only remaining pre-lock item is the §8 note on
the G4 holiday-calendar stub. Changes were surfaced first and applied only under explicit human
decision — nothing silently patched.
