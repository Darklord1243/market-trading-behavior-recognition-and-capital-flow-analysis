# Sonnet execution prompt — Phase 1b (wire normalize into label.py)

> **Status:** Ready to run. **LIS v1.5.2** §6 **Phase 1b** (follow-up to Phase 1, commit `78bd5a9`).
> **Prerequisite:** `src/normalize.py::normalize_matrix` exists and is tested (7 tests green).
>
> **Sequential context:** Parallel batch 1 is **DONE** (Track L-a `65116b6`, Phase 1 `78bd5a9`, Track V V.1–V.2 `719ebaa`, suite **79**). This is the **first** item in batch 2.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Phase 1b only** — wire `normalize_matrix` into weak-label scoring.

**Read (minimal):**
- `docs/LIS.md` §6 **Phase 1** (Phase 1b paragraph after task 1.6) + §4 module rows for `normalize.py` / `label.py`
- `src/normalize.py`, `src/label.py`, `src/rules.py`, `tests/test_rules.py`
- This prompt

**Out of scope this session:** Phase 2 (RS fix), Track L-b (CB math), Track V V.3/V.4, `main.py` changes, `docs/LIS.md` edits (flag contradictions only).

---

# LIS v1.5.2 context (trust these; do not re-derive)

| Item | Note for Phase 1b |
|---|---|
| **Phase 1 seam** | `normalize_matrix` rank-normalizes numeric cols to [0,1]; excludes `cb_available`, `n_ticks`; n≤1 / constant→0.5. **Built, unwired.** |
| **Intent gate** | `get_intention` / `_intent_confidence` use **absolute** thresholds on `book_imbalance` / `obp_imbalance_mean` — keep intent on **raw** matrix rows. |
| **Capital scoring** | `score_capital_type` on **normalized** rows. `_class_score` still applies `clip01` — after rank-norm inputs are already in [0,1]. |
| **Official fixture** | `samples/AFAC2026.xlsx` = **n=1** → normalize → all **0.5** tie → smoke stays valid but **cannot prove** scorer responsiveness. |
| **Real proof** | Multi-row **synthetic panel** (≥10 rows) in tests — planted top-rank features → expected class arg-max. |
| **Track V** | `src/validate.py` exists (offline only). Proxy-F1 delta reporting needs V.3 labels — **not required** this session. |

---

# Hard rules (auto-DQ if broken)

1. **Intraday-only** — `normalize_matrix` uses only rows in the same day's matrix; no external data.
2. **No hard-coding** — no per-stock label tables.
3. **No answer-feedback** — do not read `outputs/` or leaderboard answers.
4. **Reproducible** — no LLM in inference path.
5. **Locked labels** — `{游资, 量化, 散户}` unchanged; validator stays `src/postprocess.py`.

---

# What to build

## Goal (LIS §6 Phase 1b)

Call `normalize_matrix(matrix)` inside `weak_label_matrix` **before** capital-type scoring. Score capital on normalized values; compute intent from raw values.

## Files

| Action | Path |
|--------|------|
| Modify | `src/label.py` — import + wire `normalize_matrix` |
| Modify | `tests/test_label.py` (create if missing) or extend `tests/test_rules.py` with panel tests |
| Do NOT modify | `src/normalize.py` (unless a one-line bugfix — prefer not) |
| Do NOT wire | `src/validate.py` into `main.py` |

## Wiring contract (from LIS §6)

```python
from src.normalize import normalize_matrix

def weak_label_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    norm = normalize_matrix(matrix)
    for idx, row in norm.iterrows():
        feat_norm = row.to_dict()
        feat_raw = matrix.loc[idx].to_dict()
        capital_type, scores = score_capital_type(feat_norm)
        intention = get_intention(feat_raw)  # raw — absolute thresholds
        records.append({
            "capital_type": capital_type,
            "capital_intention": intention,
            "capital_confidence": _capital_confidence(scores),
            "intent_confidence": _intent_confidence(feat_raw),  # raw — absolute imbalance
        })
```

Pass `cb_available` from the normalized row (flag is excluded from rank-norm and passes through unchanged).

---

# TDD workflow

1. **1b.1** Write `tests/test_label.py::test_weak_label_uses_normalized_capital_scoring` (**fail first**): build a **≥10-row** synthetic matrix where:
   - Row A: clearly **游资** (top ranks on mega/aggression dims, bottom on small/burst)
   - Row B: clearly **量化** (top ranks on small/burst/low-CV dims, bottom on mega)
   - Use only feature keys that exist in `rules.DIMS_*` and the matrix columns `score_capital_type` reads.
   - Assert `weak_label_matrix(m).loc[A, "capital_type"] == "游资"` and `...loc[B, "capital_type"] == "量化"`.
   - **Do not** use the n=1 xlsx fixture for this proof.
2. **1b.2** Run → **FAIL** (labels still use raw matrix).
3. **1b.3** Wire `label.py` per contract above.
4. **1b.4** Run panel test → **PASS**.
5. **1b.5** Add `test_intent_uses_raw_matrix` — plant a row where normalized capital would differ from raw intent signal; assert `capital_intention` and `intent_confidence` follow **raw** imbalance (not normalized).
6. **1b.6** Full suite + smoke:
   ```bash
   pytest tests/test_label.py -q
   pytest tests/ -q
   python main.py --input samples/AFAC2026.xlsx -o outputs/
   ```
   Smoke asserts **valid CSVs** (label class may change on n=1 — that's OK if validator passes).

**Commit message:** `feat: wire normalize_matrix into weak labels (Phase 1b)`

---

# Acceptance criteria (Phase 1b only)

- [ ] `weak_label_matrix` scores capital on `normalize_matrix(matrix)` rows
- [ ] Intent gate (`get_intention`, `_intent_confidence`) uses **raw** matrix rows
- [ ] ≥10-row synthetic panel: planted 游资 row → `游资`, planted 量化 row → `量化`
- [ ] `pytest tests/ -q` full suite green (was 79)
- [ ] `main.py` xlsx smoke still emits valid CSVs
- [ ] No `validate` import in `main.py`; no new dependencies

**Not required:** proxy-F1 delta (needs Track V V.3 labels), Phase 2 RS fix, Track L-b CB values.

---

# Style

- Minimal diff in `label.py`; match existing conventions.
- Panel test uses hand-built `pd.DataFrame` — no `data/` dependency required.

---

# When done, report

1. Commands run + pass/fail counts
2. Files changed
3. Acceptance checklist (checked)
4. Panel test row counts + which dims you planted
5. xlsx smoke: emitted `capital_type` (note if changed from 散户)
6. **Explicit:** Phase 2 / Track L-b not started
7. Contradictions with LIS (if none, say so)

Begin with the first failing test (1b.1).
