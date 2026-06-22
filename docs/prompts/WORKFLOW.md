# Execution workflow — how the pieces fit (for the team lead)

> Plain-language map of the Sonnet prompt pack. **Not** a prompt — read this in 5 minutes, then dispatch.
> Spec of record: `docs/LIS.md` **v1.6.1** §6.

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

**Rules:** one sequential item at a time (within a batch); never trust subagent reports without fresh command output; Sonnet does **not** edit LIS unless you ask the lead to.

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

## Batch 2 — COMPLETE ✅ (2026-06-18)

Sequential dispatch (one Sonnet at a time, file overlap on `features.py`/`label.py`):

| Order | Commit | Tests | Gate |
|-------|--------|-------|------|
| Phase 1b (wire normalize) | `18cca42` | 79 → 86 | PASS |
| Track L-b (real CB math) | `87a60a8` | 86 → 93 | PASS |
| Phase 2 (RS dtype fix) | `f932504` | 93 → 101 | PASS |

**Suite:** 101 passed. **Open from batch 2:** Track L-c (fast-cancel still an inter-cancel proxy); Track V needs
V.3 labels + V.4 harness before any real proxy-F1 number exists.

---

## Batch 3 — COMPLETE ✅ (2026-06-22) — V.4 ‖ V.3 → P.1 → B.0/B.2 → L-c re-eval

```
V.4 harness (Sonnet)   ── ✅  scripts/validate_offline.py
V.3 labels (HUMAN)     ── ✅  validation_labels.csv (24-key combined gate)
P.1 parquet ingest     ── ✅  ingest_parquet.py + parquet: input
B.0 / B.2 retail dims   ── ✅  gate 0.6094 → 0.6599 (n=24 parquet:data/202606)
   ↓
L-c re-eval (Sonnet)   ── ✅ DONE — true-latency swap REJECTED (gate 0.6599→0.6500), infra retained `51787d0`
                                    (parquet swap also tried on n=10: 0.4917→0.4381 — see LIS v1.5.7)
```

| Order | Owner | Prompt / spec | Status |
|-------|-------|---------------|--------|
| V.4 | Sonnet | [`sonnet-track-v-v4-offline-harness.md`](sonnet-track-v-v4-offline-harness.md) | ✅ |
| V.3 | **Human** | [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) | ✅ |
| P.1 | Sonnet | (LIS §6 Track P) | ✅ |
| B.0 / B.2 | Sonnet | [`sonnet-feature-b-b2-size-entropy.md`](sonnet-feature-b-b2-size-entropy.md) | ✅ |
| L-c re-eval | Sonnet | base + [`sonnet-track-l-c-cb-true-latency-addendum.md`](sonnet-track-l-c-cb-true-latency-addendum.md) | ✅ **rejected** |
| Orchestrator | Opus | [`opus-lead-orchestrator-batch-3-continued.md`](opus-lead-orchestrator-batch-3-continued.md) | done |

**Suite:** 131 passed, 2 xfailed. **Frozen reference gate:** n=24 → weighted_f1 **0.6599**, 散户 R **5/10**.

---

## Batch 4 — label addendum ‖ B.3a → **wait CSV** → V.3.2 verify → B.3b (retail-recall focus)

```
HUMAN          append validation labels (20260616 LHB seats — 0622 not yet procured, stepped back to a day in data/202606)
   ‖ parallel
OPUS           H (docs sync → v1.6.1) + B.3a (散户 false-negative diagnostic on n=24)
   ↓
HUMAN          "CSV ready"
OPUS           V.3.2 verify (read-only) → record NEW active baseline on parquet:data/202606
   ↓
HUMAN          "proceed to B.3b"
OPUS → SONNET  Feature B.3 — recover the 5 散户 misses; GATE: beat active baseline (not 0.6599 alone)
```

| Order | Owner | Prompt / spec | Status |
|-------|-------|---------------|--------|
| H | Opus | docs sync (this file + README → v1.6.1) | 🔜 |
| V.3.2 | **Human labels → Opus verify** | [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) §1–§5 | 🔜 (blocks B.3b baseline) |
| B.3a | Sonnet | 散户 FN diagnostic (`--verbose-scores`; **no src/**) | 🔜 |
| B.3b | Sonnet | Feature B.3 implement (after V.3.2 PASS + approved prompt) | ⛔ blocked |
| Orchestrator | Opus | [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md) | **START HERE** |

**Gate rule (B.3b):** beat the **active baseline** recorded after V.3.2 (joinable keys on `parquet:data/202606`),
reporting the n=24 subset for continuity. Falls back to frozen **0.6599 / n=24** only on explicit
**"proceed to B.3b on n=24"**. The CSV is **human-only** — Opus/Sonnet never label or "fix" rows.

**Why this order:** V.4 is the measuring instrument — it can be **built** with no real labels (EXAMPLE-only → skip),
so it runs in parallel with the human V.3 labeling. V.3 is human-only and gates *believing* any win. L-c's proxy→true
swap is only worth shipping **if it moves the real proxy-F1**, so L-c needs both V.3 and V.4 complete first.

**Human vs Sonnet:**

| Item | Human does | Sonnet does |
|------|-----------|-------------|
| V.4 | — | builds `scripts/validate_offline.py` + tests (TDD) |
| V.3 | labels ≥8 cited rows from public sources | **nothing** (never touches the CSV) |
| L-c | — (lead runs the proxy-F1 gate) | extends `read_cancel_frame` + `_cb_features` (TDD, red-first across a minute boundary) |

**Other human work (anytime, not Sonnet):**

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

**Opus lead (recommended):** paste [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md) into a new **Claude Code Opus** chat. Opus runs **H + B.3a** in parallel while you append labels, runs **V.3.2 verify** on your "CSV ready", records the new active baseline, then dispatches **B.3b** against it.

**Manual / Sonnet-only:** copy the next Sonnet prompt below → paste into Claude Code **Sonnet** → you verify → commit.

1. Read this file + LIS §4 snapshot.
2. Open the **next** prompt (batch 4 table) → copy whole file (or let Opus orchestrator read it).
3. Sonnet implements (TDD); **Opus lead commits** after GATE PASS unless you said otherwise.
4. **Double-verify** — `pytest tests/ -q`, scope diff, smoke if applicable; for B.3b, the **proxy-F1 must beat the active baseline**.
5. Dispatch **one** next item after your proceed.

**Batch 4 start:** see [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md) — append labels, say **"CSV ready"**, then **"proceed to B.3b"** after the V.3.2 verify.

---

## Links

- **Opus orchestrator (batch 4 — current):** [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md)
- Opus orchestrator (batch 3 continued): [`opus-lead-orchestrator-batch-3-continued.md`](opus-lead-orchestrator-batch-3-continued.md)
- Opus orchestrator (batch 3 base): [`opus-lead-orchestrator-batch-3.md`](opus-lead-orchestrator-batch-3.md)
- Opus orchestrator (batch 2, done): [`opus-lead-orchestrator-batch-2.md`](opus-lead-orchestrator-batch-2.md)
- Prompt index: [`README.md`](README.md)
- Template: [`sonnet-phase-execution-template.md`](sonnet-phase-execution-template.md)
- LIS: [`../LIS.md`](../LIS.md)
- Local data: [`../data_inventory_report.md`](../data_inventory_report.md)
