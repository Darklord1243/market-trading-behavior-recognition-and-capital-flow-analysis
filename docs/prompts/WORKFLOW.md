# Execution workflow — how the pieces fit (for the team lead)

> Plain-language map of the Sonnet prompt pack. **Not** a prompt — read this in 5 minutes, then dispatch.
> Spec of record: `docs/LIS.md` **v1.5.2** §6.

## Operating model (Opus lead ↔ Sonnet executor)

```
YOU (human)     approve dispatch
    ↓
OPUS (lead)     pick prompt, paste to Claude Code Sonnet, review end-of-session report
    ↓
SONNET          TDD-only implementation; one phase/track per session; commit; stop
    ↓
OPUS + YOU      double-verify: git show, pytest, smoke, scope/compliance checklist
    ↓
OPUS            update LIS §4 + changelog (or batch docs commit); dispatch next ONE item
```

**Rules:** one sequential item at a time in batch 2; never trust subagent reports without fresh command output; Sonnet does **not** edit LIS unless you ask the lead to.

---

## Batch 1 — COMPLETE ✅ (2026-06-18)

Parallel dispatch (three Sonnet sessions, disjoint files):

| Track | Commit | Tests | Gate |
|-------|--------|-------|------|
| Track L-a (local GBK ingest) | `65116b6` | 37 → 67 | PASS |
| Phase 1 (normalize seam) | `78bd5a9` | 67 → 74 | PASS |
| Track V V.1–V.2 (offline F1) | `719ebaa` | 74 → 79 | PASS |

**Suite:** 79 passed. **Open from batch 1:** L-a only (CB values stub), Phase 1 unwired, Track V needs V.3/V.4 for proxy-F1 deltas.

---

## Batch 2 — SEQUENTIAL (one at a time)

```
Phase 1b  ──►  wire normalize_matrix into label.weak_label_matrix (intent stays raw)
    ↓
Track L-b ──►  real _cb_features math from reconstructed cancels
    ↓
Phase 2   ──►  RS dtype fix (.diff().dt.total_seconds()*1000) + burst <100ms
    ↓
Phase 3+  ──►  feature expansion, GBDT head, clustering, … (fill template per LIS §6)
```

| Order | Prompt | LIS target |
|-------|--------|------------|
| **1 — NEXT** | [`sonnet-phase-1b-wire-normalize.md`](sonnet-phase-1b-wire-normalize.md) | Phase 1b |
| 2 | [`sonnet-track-l-b-cb-features.md`](sonnet-track-l-b-cb-features.md) | Track L-b |
| 3 | [`sonnet-phase-2-rs-fix.md`](sonnet-phase-2-rs-fix.md) | Phase 2 |
| 4+ | [`sonnet-phase-execution-template.md`](sonnet-phase-execution-template.md) | Phase 3–6 |

**Human, anytime (not Sonnet):**

- Track V **V.3** — seed `tests/fixtures/validation_labels.csv` ([`../human_guides/track_v_validation_labels.md`](../human_guides/track_v_validation_labels.md))
- Track V **V.4** — offline harness `scripts/validate_offline.py`
- Track D — more L2 days ([`../human_guides/track_d_l2_procurement.md`](../human_guides/track_d_l2_procurement.md))

---

## What each batch-1 prompt built

| Prompt | What landed |
|--------|-------------|
| [`sonnet-track-l-ingest-local.md`](sonnet-track-l-ingest-local.md) | `src/ingest_local.py` — GBK CSV → pipeline frame + cancel reconstruction |
| [`sonnet-phase-1-normalize.md`](sonnet-phase-1-normalize.md) | `src/normalize.py` — cross-sample rank normalization (unwired) |
| [`sonnet-track-v-validate.md`](sonnet-track-v-validate.md) | `src/validate.py` — offline `weighted_f1` (not in `main.py`) |

---

## How to run (new session)

**Opus lead (recommended):** paste [`opus-lead-orchestrator-batch-2.md`](opus-lead-orchestrator-batch-2.md) into a new **Claude Code Opus** chat. Opus dispatches Sonnet one track at a time, double-verifies, commits after each GATE PASS, stops for your **"proceed"** between tracks.

**Manual / Sonnet-only:** copy the next Sonnet prompt below → paste into Claude Code **Sonnet** → you verify → commit.

1. Read this file + LIS §4 snapshot.
2. Open the **next** prompt (batch 2 table) → copy whole file (or let Opus orchestrator read it).
3. Sonnet implements (TDD); **Opus lead commits** after GATE PASS unless you said otherwise.
4. **Double-verify** — `pytest tests/ -q`, scope diff, smoke if applicable.
5. Dispatch **one** next prompt after your proceed.

**Start batch 2 with:** `sonnet-phase-1b-wire-normalize.md` (say **"proceed to Phase 1b"**).

---

## Links

- **Opus orchestrator (batch 2):** [`opus-lead-orchestrator-batch-2.md`](opus-lead-orchestrator-batch-2.md)
- Prompt index: [`README.md`](README.md)
- Template: [`sonnet-phase-execution-template.md`](sonnet-phase-execution-template.md)
- LIS: [`../LIS.md`](../LIS.md)
- Local data: [`../data_inventory_report.md`](../data_inventory_report.md)
