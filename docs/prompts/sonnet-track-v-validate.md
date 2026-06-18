# Sonnet execution prompt — Track V V.1–V.2 (offline weighted-F1 scorer)

> **Status:** Ready to run. **LIS v1.4.1** §6 **Track V**, tasks **V.1–V.2 only**. Needs **no human labels** and
> **no other track** — fully safe to run in parallel with Track L / Phase 1.
>
> **Parallel tracks (context only — out of scope here):** Track L (local adapter), Phase 1 (normalize),
> Track D (human procurement). See `docs/LIS.md` §6.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Track V tasks V.1–V.2 only** — the **offline**
`weighted_f1` proxy scorer.

**Read (minimal):**
- `docs/LIS.md` §6 **"Track V — Offline validation & label-truth proxy"** (and §2–§3 if not seen this session)
- This prompt

Do **not** re-read the whole doc tree.

**Out of scope this session:** **V.3** (seed `validation_labels.csv` — a *human* action; see
`docs/human_guides/track_v_validation_labels.md`), **V.4** (offline harness `scripts/validate_offline.py`), anything in
**`main.py` / the inference path**, Phase 1+, Track L. No `docs/LIS.md` edit unless you hit a factual contradiction
(flag it; don't silently change).

---

# LIS v1.4.1 context (trust these; do not re-derive)

| Item | Note for Track V |
|---|---|
| **OQ-1 / R2** | ✅ Resolved — eval is **3-class** `{游资, 量化, 散户}`; `散户` scores in weighted F1. The scorer is 3-class. |
| **What this is** | An **offline** proxy-F1 of Task-2 output vs a hand-labeled truth set — a *smoke detector*, not the leaderboard. |
| **Compliance** | Labels are **public post-market info, never the board's answers** (§3.3). The scorer is **pure & offline** — no network, no read of `outputs/` or leaderboard answers. |
| **Fixture state** | `tests/fixtures/validation_labels.csv` currently has **EXAMPLE rows only** (`EXAMPLE.SZ`, confidence 0.0). **Do NOT load it in tests** — use inline tiny DataFrames. |
| **Dependency** | `sklearn` is already in the env (`src/cluster.py` imports it), so the **test** may use it as an oracle. |

---

# Hard rules (auto-DQ if broken)

From LIS §2–§3:

1. **Intraday-only** — the scorer is offline post-hoc; it must **never** be wired into a feature or `main.py`'s inference
   path. Validation labels never enter the model.
2. **No hard-coding** — no per-stock logic; generic over the label set `config.CAPITAL_TYPES`.
3. **No answer-feedback** — the scorer compares our output to **our** hand labels, never the platform's backtest answers;
   it must not read `outputs/` or any leaderboard file.
4. **Reproducible** — pure function, deterministic, relative paths only; no LLM.
5. **Locked labels** — operate over `{游资, 量化, 散户}` exactly; do not invent or translate class strings.

---

# What to build

## Goal (LIS §6 Track V, V.1–V.2)

A **pure, offline** `weighted_f1` that scores predicted `capital_type` against a hand-labeled truth set, so later phases
(Phase 1b/2/3) can report a **proxy-F1 before/after** delta. This session builds **only the scorer + its test** — not the
labels, not the harness.

## Files

| Action | Path |
|--------|------|
| Create | `src/validate.py` |
| Create | `tests/test_validate.py` |
| Do NOT touch | `tests/fixtures/validation_labels.csv` (human V.3), `main.py` (inference path) |

## API contract (`docs/LIS.md` §6 Track V)

```python
weighted_f1(pred_df: pd.DataFrame, truth_df: pd.DataFrame) -> dict
```

- **Inner-join** `pred_df` and `truth_df` on `(stock_code, transaction_date)` — only co-present (stock, day) rows are scored.
- Compute **weighted F1** over `capital_type` plus **per-class** precision / recall / F1 and **support**.
- Return a dict, e.g. `{"weighted_f1": float, "n": int, "per_class": {label: {"precision":.., "recall":.., "f1":.., "support":..}}}`.
- **Pure & offline:** no network, no file reads of board answers, deterministic.
- **Prefer a dependency-light implementation** in `src/validate.py` (so the scorer is independently auditable). Using
  `sklearn` is acceptable since it is already a project dependency — but the **V.1 test** pins correctness to
  `sklearn.metrics.f1_score(average="weighted")` regardless.
- Sensible edge behavior: **empty join → `weighted_f1 = 0.0`, `n = 0`** (document it; don't raise).

---

# TDD workflow (one failing test → fail → minimal impl → pass → commit)

1. **V.1** Write `tests/test_validate.py::test_weighted_f1_matches_sklearn` (**fail first**): build a **tiny inline**
   `pred_df` / `truth_df` (a handful of rows over all 3 classes, sharing `(stock_code, transaction_date)` keys) and assert
   `weighted_f1(pred, truth)["weighted_f1"] == pytest.approx(sklearn.metrics.f1_score(y_true, y_pred, average="weighted"))`.
   Run → **FAIL** (`ModuleNotFoundError: src.validate`).
2. **V.2** Implement `src/validate.py::weighted_f1` per the contract (inner-join, weighted + per-class P/R/F1 + support).
   Run → **PASS**.
3. Add `test_inner_join_only_scores_common_keys` (non-overlapping keys are dropped; `n` reflects the join) and
   `test_empty_join_is_zero` (no common keys → `weighted_f1 == 0.0`, `n == 0`). Run → pass.
4. Full suite: `pytest tests/ -q` → stays green (was 37; count increases).

**Final checks before done:**
```bash
pytest tests/test_validate.py -q
pytest tests/ -q
```

**Commit message (if committing):** `feat: offline weighted-F1 proxy scorer (Track V V.1–V.2)`

---

# Acceptance criteria (Track V V.1–V.2 only — from LIS §6)

- [ ] `tests/test_validate.py::test_weighted_f1_matches_sklearn` green (matches sklearn weighted F1)
- [ ] `weighted_f1` inner-joins on `(stock_code, transaction_date)`; returns weighted + per-class P/R/F1 + support
- [ ] Pure & offline — no network, no read of `outputs/` or board answers; not wired into `main.py`
- [ ] Tests use **inline DataFrames**, not `tests/fixtures/validation_labels.csv` (EXAMPLE-only)
- [ ] Full suite green (`pytest tests/ -q`); no new dependencies

**Not required this session** (later): V.3 human label seeding, V.4 offline harness, wiring proxy-F1 into phase PRs.

---

# Style

- Match existing `src/` conventions (`from __future__ import annotations`, type hints, module docstring stating
  *offline / post-hoc / never in inference path*).
- Test-first; small commits. Delete throwaway debug scripts.

---

# When done, report

1. Commands run + pass/fail output (paste counts)
2. Files created/changed (list)
3. Acceptance checklist (checked)
4. Did you implement `weighted_f1` by hand or via sklearn? (either is fine — state which)
5. Anything that contradicted LIS (if none, say so)
6. **Next hint:** scorer ready; V.3 (human labels) + V.4 (offline harness) remain before phases can report proxy-F1 deltas

Begin with the first failing test (V.1).
