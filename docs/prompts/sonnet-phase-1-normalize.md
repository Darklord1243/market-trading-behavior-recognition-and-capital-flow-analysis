# Sonnet execution prompt — Phase 1 (cross-sample normalization)

> **Status:** Ready to run. **LIS v1.4.1** §6 **Phase 1**. Phase 1b (`label.py` wiring) is a **separate** follow-up session.
>
> **Parallel tracks (context only — out of scope here):** Track V (offline validate), Track L (local CSV adapter), Track D (human procurement). See `docs/LIS.md` §6.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Phase 1 only** — the cross-sample normalization seam.

**Read:**
- `docs/LIS.md` §6 **"Phase 1 — Cross-sample normalization seam"**
- This prompt

Do **not** re-read the whole doc tree.

**Out of scope this session:** Phase 1b (`src/label.py` wiring), Phase 2+ (RS fix, features, model, clustering), **Track L / Track V / Track D**, any LIS edits unless you hit a factual contradiction (flag it; don't silently change LIS).

---

# LIS v1.4.1 context (trust these; do not re-derive)

| Item | Note for Phase 1 |
|---|---|
| **OQ-1 / R2** | ✅ Resolved — eval is **3-class** `{游资, 量化, 散户}`. You are not changing labels. |
| **H1 exec rank** | Still **#1** — normalization gates H3, H4, H5 inputs. |
| **Official fixture** | `samples/AFAC2026.xlsx` = **1 stock** → single-row normalize → all **0.5** (degenerate). Phase 1 unit tests use synthetic matrices, not the fixture, for rank proof. |
| **Local `data/`** | ~7.5k stocks × 2 days exist but **not wired** until Track L. Phase 1 does not require them. |
| **Track V** | After Phase 1b, PRs should report proxy-F1 delta when `src/validate.py` exists — **not required in Phase 1**. |

---

# Hard rules (auto-DQ if broken)

From LIS §2–§3:

1. **Intraday-only** — normalization uses only rows in the **same input matrix** (the day's cross-section). No future days, no external data, no validation labels in features.
2. **No hard-coding** — no per-stock tables, no random fill.
3. **No answer-feedback** — never tune against leaderboard outputs.
4. **Reproducible** — fixed seed unchanged; no LLM in inference path.
5. **Locked labels unchanged** — you are not touching scoring logic yet (that's Phase 1b).

**CB note (§3):** On the **xlsx/snapshot path**, cancel features are absent → `cb_available` passes through unchanged. Local embedded cancels are a **Track L** concern, not Phase 1.

---

# What to build

## Goal

Add a pure normalization layer so rule/model inputs are comparable across stocks. Unblocks H1.

## Files

| Action | Path |
|--------|------|
| Create | `src/normalize.py` |
| Create | `tests/test_normalize.py` |
| Do NOT modify yet | `src/label.py` (Phase 1b) |

## API contract (`docs/LIS.md` §6 Phase 1)

```python
normalize_matrix(matrix: pd.DataFrame) -> pd.DataFrame
```

- Rank-normalize **each numeric column** to `[0,1]` across rows: `rank(method="average")` then `(r - 1) / (n - 1)`.
- **Exclude** from normalization (pass through unchanged): `cb_available`, `n_ticks`.
- **n ≤ 1:** every normalizable numeric column → `0.5` (neutral).
- **Constant column** (all equal, n > 1): → `0.5`.
- Same index/columns as input; non-numeric columns unchanged.

Module docstring must state: within-day cross-section only; compliance #1.

---

# TDD workflow (follow in order)

1. **1.1** Write `tests/test_normalize.py::test_ranks_to_unit_interval` per LIS §6 (4 rows, `cb_available` passthrough).
2. **1.2** Run `pytest tests/test_normalize.py::test_ranks_to_unit_interval -q` → expect **FAIL** (`ModuleNotFoundError`).
3. **1.3** Implement `src/normalize.py` per LIS §6 (minimal; match existing `src/` style).
4. **1.4** Run test → **PASS**.
5. **1.5** Add `test_single_row_is_neutral` and `test_constant_column_is_neutral` per LIS §6.
6. **1.6** Run full suite: `pytest tests/ -q` → must stay **37+ green** (count may increase).
7. **1.7** Smoke: `python main.py --input samples/AFAC2026.xlsx -o outputs/` → still emits valid CSVs (labels may still be degenerate on n=1 — that's expected).

**Commit message (if committing):** `feat: cross-sample rank normalization seam (H1 prerequisite)`

---

# Acceptance criteria (Phase 1 only)

- [ ] `pytest tests/test_normalize.py -q` green
- [ ] `pytest tests/ -q` full suite green
- [ ] `normalize_matrix` matches LIS contract (rank, exclude flags, n=1, constant col)
- [ ] No changes to `src/label.py`, `src/rules.py` behavior, or `src/features.py`
- [ ] No new dependencies in `requirements.txt`

**Not required in Phase 1** (later):
- Phase 1b: wire into `weak_label_matrix`; ≥10-row synthetic scorer panel tests
- Track V: proxy-F1 before/after
- Track L: real multi-stock matrix from `data/`

---

# Style

- Match existing project conventions; minimal code — one function + `EXCLUDE` constant.
- Delete any throwaway debug scripts.

---

# When done, report

1. Commands run + output
2. Files created/changed
3. Acceptance checklist
4. Contradictions with LIS (if any)
5. **Explicit:** "Phase 1b not started — `label.py` still scores on raw matrix"
6. **Proxy-F1:** N/A (Phase 1)

Begin with the failing test.
