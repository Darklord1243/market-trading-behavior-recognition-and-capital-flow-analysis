# Sonnet execution prompt — template (LIS v1.4.1)

> **How to use:** Copy to `docs/prompts/sonnet-phase-{{ID}}-{{slug}}.md`, replace every `{{PLACEHOLDER}}`, delete this block, paste into Claude Code with Sonnet.
>
> **LIS v1.4.1 roadmap (§6):** numbered **Phases 1–6** (sequential engineering spine) plus **parallel tracks**:
> - **Track V** — offline validation / proxy-F1 (`src/validate.py`)
> - **Track D** — data procurement (human; see `docs/human_guides/track_d_l2_procurement.md`)
> - **Track L** — local GBK CSV ingest adapter (`src/ingest_local.py`)
>
> Use `Phase {{N}}` or `Track {{LETTER}}` in the title below to match the LIS subsection you are implementing.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS {{PHASE_OR_TRACK_ID}} only** — {{PHASE_TITLE}}.

**Read (minimal):**
1. `docs/LIS.md` — **§6** subsection for your target only (`Phase N` or `Track X`), plus **§2–§3** if you have not seen them this session.
2. This prompt file.
3. The **one** primary `src/` file your phase names (+ its test file).

Do **not** re-read the whole doc tree. Pointers only: `docs/data_inventory_report.md` (local `data/` layout), `docs/human_guides/` (human-only work).

**Out of scope this session:** {{OUT_OF_SCOPE}}

**Do not edit `docs/LIS.md`** unless you hit a factual contradiction (flag it in your report; propose a changelog line; do not silently change LIS).

---

# LIS v1.4.1 context (do not re-derive; trust these locks)

| Item | Status |
|---|---|
| **Eval class set (OQ-1 / R2)** | ✅ **Resolved** — 3-class `{游资, 量化, 散户}`; `散户` scores in weighted F1. No code change. |
| **Official fixture** | `samples/AFAC2026.xlsx` — **1 stock × 1 day**; n=1 cannot validate scoring or normalization. |
| **Local corpus** | `data/` (gitignored, ~7.5k stocks × 2 days) — **not readable by `load_raw` yet**; needs **Track L** adapter. |
| **Cancels** | Embedded in local CSVs (SZ `逐笔成交.成交代码=='C'`, SH `逐笔委托.委托类型=='D'`); xlsx fixture has **no** cancels — `cb_available=False`. |
| **Track V** | Offline proxy-F1 vs `tests/fixtures/validation_labels.csv` — report before/after for H1–H3 phases when scorer exists. |

---

# Hard rules (auto-DQ if broken)

From LIS §2–§3 (non-negotiable):

1. **Intraday-only** — {{INTRADAY_BINDING_FOR_THIS_PHASE}}
2. **No hard-coding** — no per-stock label tables, no random fill; thresholds are global `config` constants.
3. **No answer-feedback** — never read `outputs/` or leaderboard answers to tune anything.
4. **Reproducible** — `config.RANDOM_SEED=42`; relative paths; **no LLM in the inference path**.
5. **Locked labels** (exact bytes): `capital_type` — `{游资, 量化, 散户}` (bare `量化`, never `量化机构`); `capital_intention` — `{买入, 卖出, T0交易}`; UTF-8-sig, 4 cols, no nulls. Validator: `src/postprocess.py`.

**CB / cancel path (§3 engineering invariant):**
- **xlsx / snapshot-only path** (`load_raw` + official fixture): no cancel table — `cb_available=0.0`; CB dims vote **NEUTRAL**.
- **Local CSV path** (after **Track L**): reconstruct embedded cancels — `cb_available=True`; wire `features._cb_features` true branch.

---

# What to build

## Goal (from LIS §6)

{{PHASE_GOAL_ONE_PARAGRAPH}}

## Files

| Action | Path |
|--------|------|
| {{FILE_ACTION_1}} | `{{FILE_PATH_1}}` |
| {{FILE_ACTION_2}} | `{{FILE_PATH_2}}` |
| {{FILE_ACTION_3}} | `{{FILE_PATH_3}}` |

## API / design contract (from LIS)

{{DESIGN_CONTRACT_CODE_OR_BULLETS}}

---

# TDD workflow (follow in order)

{{NUMBERED_TASKS_FROM_LIS — one failing test → fail → minimal impl → pass → commit}}

**Final checks before done:**
```bash
pytest tests/{{PRIMARY_TEST_FILE}} -q
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/   # if phase touches pipeline (xlsx path)
# After Track L exists, also smoke on a tiny local fixture if LIS says so:
# python main.py --input data/...  # only when adapter is wired — do not invent paths
```

**Commit message (if committing):** `{{SUGGESTED_COMMIT_MESSAGE}}`

---

# Acceptance criteria (this phase/track only)

Copy from LIS §6; check each box in your report:

- [ ] {{ACCEPTANCE_1}}
- [ ] {{ACCEPTANCE_2}}
- [ ] {{ACCEPTANCE_3}}
- [ ] Full suite green (`pytest tests/ -q`)
- [ ] No out-of-scope files changed
- [ ] No new dependencies (unless LIS explicitly allows for this phase/track)

**Track V add-on (Phases 1b, 2, 3 batches only — when `src/validate.py` exists):**
- [ ] Record **proxy-F1 before/after** on `tests/fixtures/validation_labels.csv` (skip if only EXAMPLE rows or scorer not built)

**Not required in this session** (later phases/tracks): {{EXPLICITLY_DEFERRED}}

---

# Style

- Match existing `src/` conventions (`from __future__ import annotations`, type hints, minimal diff).
- Test-first; small commits.
- Delete throwaway debug scripts before finishing.
- On Windows, console Chinese may mojibake — verify CSVs on disk are UTF-8-sig.

---

# When done, report

1. Commands run + pass/fail output (paste counts)
2. Files created/changed (list)
3. Acceptance criteria met (checklist)
4. Anything that contradicted LIS (if none, say so)
5. **Proxy-F1:** N/A / before→after numbers / skipped (reason)
6. **Next hint:** {{WHAT_REMAINS_FOR_FOLLOW_UP}}

Begin with the first failing test.
