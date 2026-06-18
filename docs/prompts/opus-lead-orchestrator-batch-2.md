# Opus lead orchestrator — Batch 2 (Phase 1b → Track L-b → Phase 2)

> **Paste this entire file** into a **new Claude Code Opus** session to run Batch 2.
> **Human team lead:** approve each dispatch with **"proceed to …"** between tracks.
> **Sonnet prompts:** `docs/prompts/sonnet-phase-1b-wire-normalize.md` · `sonnet-track-l-b-cb-features.md` · `sonnet-phase-2-rs-fix.md`
> **Map:** [`WORKFLOW.md`](WORKFLOW.md) · **Spec:** [`docs/LIS.md`](../LIS.md) **v1.5.2** §6

---

You are the **Opus lead orchestrator** for AFAC2026 Track 1 in this repo. I am the human team lead. Your job is **not** to implement all three tracks yourself — you **dispatch, monitor, inspect, and double-verify** one Sonnet execution subagent at a time, then **gate** before the next.

**Model rule:** You (lead) stay on **Opus**. Dispatch **each subagent with model Sonnet** (not Opus). If your environment exposes model selection for subagents, set Sonnet explicitly; if not, state in every dispatch header:

> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates.*

**Spec of record:** `docs/LIS.md` **v1.5.2** · **Workflow map:** `docs/prompts/WORKFLOW.md`

---

## Batch 1 — already DONE (do not re-run)

| Track | Commit | Tests |
|-------|--------|-------|
| Track L-a (local GBK ingest) | `65116b6` | 37 → 67 |
| Phase 1 (normalize seam, unwired) | `78bd5a9` | 67 → 74 |
| Track V V.1–V.2 (offline F1) | `719ebaa` | 74 → **79** |

**Baseline for Batch 2:** `pytest tests/ -q` → **79 passed**. `src/normalize.py` exists but is **not** wired into `label.py`. `_cb_features` true branch still returns **zeros** (L-b pending). `src/validate.py` is **offline-only** (not in `main.py`).

---

## Operating model (strict)

For **each** track, run this loop — **do not skip steps, do not start the next track until gated:**

```
DISPATCH  → Sonnet subagent (model Sonnet) runs the filled prompt (TDD, scoped files only)
MONITOR   → wait for completion; collect end-of-session report
INSPECT   → Opus reviews diff + report vs prompt acceptance criteria
VERIFY-1  → Opus independently runs commands and reads code (never trust report alone)
VERIFY-2  → second pass: scope / compliance / LIS alignment + regression check
GATE      → PASS → commit (unless I said "no commit") + Gate Report + stop for my proceed
            FAIL → fix or re-dispatch Sonnet; no commit; do not proceed
```

**Sequential order (one Sonnet subagent at a time):**

1. **Phase 1b** — `docs/prompts/sonnet-phase-1b-wire-normalize.md`
2. **Track L-b** — `docs/prompts/sonnet-track-l-b-cb-features.md`
3. **Phase 2** — `docs/prompts/sonnet-phase-2-rs-fix.md`

**Rationale:** Phase 1b makes normalization affect scoring (H1 label fix). Track L-b adds real CB values before RS/feature work on real cross-sections. Phase 2 fixes the dtype bug so RS features are correct for normalization and rules. **Not parallel** — file overlap risk (`features.py`, `label.py`, `aggregate.py`) and ordering matters.

---

## Git commits (after each GATE PASS)

When a track **GATE = PASS**:

1. Stage **only** files for that track (no unrelated docs, `data/`, or secrets).
2. Commit with the **suggested message from that track's Sonnet prompt** (table below).
3. Run `git status` after commit; report clean working tree for that track's scope.

**Do not commit** on GATE FAIL, partial work, or before VERIFY-1 + VERIFY-2 pass.

**Do not commit** unless I explicitly authorize that gate (e.g. **"commit"** or default proceed after PASS).

| Track | Suggested commit message |
|-------|--------------------------|
| Phase 1b | `feat: wire normalize_matrix into weak labels (Phase 1b)` |
| Track L-b | `feat: real CB feature math from reconstructed cancels (Track L-b)` |
| Phase 2 | `fix: RS interval computation dtype-portable (Phase 2)` |

Never use `--no-verify`, never amend unless I ask. Never commit `data/` or secrets.

**LIS / docs:** draft §4 + changelog lines after each PASS; apply `docs/LIS.md` edits only if I say **"apply LIS update"**.

---

## How to dispatch each subagent

When dispatching, give the subagent **the full text** of the prompt file (read it from disk and include it in the task) plus this header:

---

**Model:** Sonnet (execution agent — not Opus).

**Role:** Implement **only** what the prompt below specifies.

**Read:** the prompt body + the primary `src/` files it names (+ their test files).

**Out of scope:** everything the prompt lists; no `docs/LIS.md` edits unless factual contradiction (flag only).

**Report back:** commands run (with counts), files changed, acceptance checklist, contradictions, what remains.

**Do not commit** — the Opus lead commits after GATE PASS (unless I said otherwise).

---

Use Claude Code **subagents** for each dispatch. Run **in-repo** after prior track is committed; files may overlap across L-b and Phase 2 (`features.py`) — that is why order is strict and commits are per-track.

**Environment:** Python via **Anaconda** (`conda run -n base …` on Windows if needed).

---

## Inspection checklists (after each subagent)

### Phase 1b (`sonnet-phase-1b-wire-normalize.md`)

**Expected artifacts:** `src/label.py` (modified), `tests/test_label.py` (new or extended)

**Must NOT touch (behavior):** `src/normalize.py` contract, `main.py` inference path, `src/validate.py` wiring

**Acceptance:**

- [ ] `weak_label_matrix` calls `normalize_matrix(matrix)` before capital scoring
- [ ] `score_capital_type` uses **normalized** row; `get_intention` + `_intent_confidence` use **raw** row
- [ ] ≥10-row synthetic panel: planted **游资** row → `游资`, planted **量化** row → `量化`
- [ ] `test_intent_uses_raw_matrix` (or equivalent) — intent follows raw imbalance
- [ ] `pytest tests/ -q` full suite green (baseline **79**; count may increase)
- [ ] `python main.py --input samples/AFAC2026.xlsx -o outputs/` — valid CSVs (class may change on n=1; validator must pass)
- [ ] No `validate` import in `main.py`; no new dependencies
- [ ] §3: no leaderboard tuning, no validation labels in inference

**VERIFY-1 commands (you run):**

```bash
pytest tests/test_label.py -q
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/
```

**VERIFY-2 (you read):**

- Diff limited to `label.py` + tests (flag unexpected `normalize.py` / `rules.py` behavior changes)
- `grep` / read `label.py`: `normalize_matrix` imported; loop uses `feat_norm` vs `feat_raw` correctly
- Panel test does **not** use n=1 xlsx fixture as proof

---

### Track L-b (`sonnet-track-l-b-cb-features.md`)

**Expected artifacts:** `src/features.py` (`_cb_features` true branch), likely `src/aggregate.py`, `tests/test_features.py`, optional `config.py` (`CB_FAST_CANCEL_MS`)

**May touch optionally:** `src/ingest_local.py` only if extending `read_cancel_frame` for order-ref latency (not required)

**Must NOT break:** `ingest.load_raw` / xlsx path; `test_absent_cb_dims_vote_neutral`; `main.py` default input

**Acceptance:**

- [ ] `_cb_features(..., has_cancel_table=True)` returns **non-zero** CB keys on synthetic + `local_l2_tiny` cancel data
- [ ] `has_cancel_table=False` → zeros + `cb_available=0.0` (unchanged)
- [ ] `cb_fast_cancel_ratio` uses **inter-cancel interval proxy** (`< CB_FAST_CANCEL_MS`) unless refs were added — documented in code/report
- [ ] Cancel plumbing reaches `_cb_features` (cancel_lookup or equivalent)
- [ ] `pytest tests/test_features.py -q -k cb` green; full suite green
- [ ] xlsx smoke: `cb_available=False` in log output
- [ ] No `validate` in inference path; no heavy new deps

**VERIFY-1 commands:**

```bash
pytest tests/test_features.py -q -k cb
pytest tests/test_rules.py::test_absent_cb_dims_vote_neutral -q
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/
```

**VERIFY-2 (you read):**

- `read_cancel_frame` still returns `side`, `cancel_time`, `cancel_qty` (refs optional only)
- `CB_KEYS` unchanged unless LIS contradiction flagged
- Honest report: inter-cancel proxy vs true order→cancel latency
- `ingest.py` / `load_raw` not hacked

---

### Phase 2 (`sonnet-phase-2-rs-fix.md`)

**Expected artifacts:** `src/features.py` (`_rs_features`), `tests/test_features.py`, optional `config.py` (`RS_BURST_THRESHOLD_MS`)

**Acceptance:**

- [ ] Intervals via `.diff().dt.total_seconds() * 1000` (dtype-portable) — **not** `astype("int64") // 1_000_000`
- [ ] Synthetic 30s-spaced `datetime64[ms]` group → mean interval ≈ 30000 ms
- [ ] `rs_burst_ratio` = share of intervals **< 100ms** (not `< 0.25 * mean`)
- [ ] Uniform cadence → lower CV than irregular (hand-checked tests)
- [ ] Full suite green; xlsx smoke valid CSVs
- [ ] Report documents fixture `rs_interval_cv` / `rs_burst_ratio` before → after (~1.34 / ~0 target)

**VERIFY-1 commands:**

```bash
pytest tests/test_features.py -q -k rs
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/
```

**VERIFY-2 (you read):**

- `_rs_features` only changed in scope; PI (`hour`/`minute`) untouched
- No normalize / label wiring changes in this track
- Phase 3+ not started

---

## Double-verify rule (mandatory)

For each track, produce a short **Gate Report:**

1. **Subagent claims** — bullet summary from Sonnet report
2. **Lead verification** — what you ran/read; paste pytest summary line; note any mismatch
3. **Commit** — if PASS: hash + message; if FAIL: "no commit"
4. **GATE = PASS** only if both agree and VERIFY-1 + VERIFY-2 are clean → then commit (unless I said "no commit")
5. **GATE = FAIL** → re-dispatch Sonnet with failing test + `file:line`; no commit; do not proceed

---

## After each GATE PASS

1. Run the git commit (see table) unless I said **"no commit"** for that gate
2. Propose one-line LIS §4 status flip + changelog entry (**draft only** — apply only if I say **"apply LIS update"**)
3. Present Gate Report + commit hash to me
4. **Stop and wait** for my **"proceed to …"** before dispatching the next track

---

## What you do NOT do

- Do not implement all three tracks yourself in the lead session (delegate to Sonnet)
- Do not run Batch 2 tracks in parallel
- Do not skip VERIFY-1 because the subagent said green
- Do not re-run Batch 1 (Track L-a / Phase 1 / Track V V.1–V.2)
- Do not start Phase 3+, Track V V.3/V.4, or `main.py --input data/` wiring unless I ask
- Do not dispatch subagents on Opus when Sonnet is available
- Do not commit `docs/` unless I authorized docs commit for that gate

---

## Start now

1. Confirm baseline: `git log -3 --oneline` shows `719ebaa` / `78bd5a9` / `65116b6`; `pytest tests/ -q` → 79 passed.
2. Read `docs/prompts/sonnet-phase-1b-wire-normalize.md` in full.
3. Dispatch the **first** Sonnet subagent (model Sonnet) with that prompt + dispatch header.
4. When it returns: **inspect → VERIFY-1 → VERIFY-2 → Gate Report**.
5. On **PASS:** commit with Phase 1b message → stop and wait for my proceed.
6. On my **"proceed to Track L-b"**, repeat for L-b, then Phase 2.

**Begin with Phase 1b dispatch** (unless I say otherwise).
