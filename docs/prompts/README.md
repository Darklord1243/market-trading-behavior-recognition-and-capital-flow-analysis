# Execution prompts (Sonnet / Claude Code)

Reusable prompts for **implementation agents** (Sonnet-class). Strategy and LIS maintenance stay with the
high-reasoning lead (Opus); executors read **one prompt file + `docs/LIS.md` §6** for the target phase or track.

**LIS version:** v1.6.0 (2026-06-22). Batch 1–2 done. Batch 3: V.4/V.3/P.1/B.2 ✅ — **L-c re-eval NEXT** (gate 0.6599).

> **New here? Read [`WORKFLOW.md`](WORKFLOW.md) first** — operating model (Opus → Sonnet → verify), batch status, dispatch order.

## Batch status

| Batch | Status | Suite |
|-------|--------|-------|
| **1** (parallel: Track L-a, Phase 1, Track V V.1–V.2) | ✅ DONE | 79 passed |
| **2** (sequential: Phase 1b → L-b → Phase 2) | ✅ DONE | 101 passed |
| **3** (V.4 ‖ V.3 → P.1 → B.2 → **L-c re-eval**) | 🔜 L-c next | 130 passed |

## Files

| File | Purpose |
|------|---------|
| [`WORKFLOW.md`](WORKFLOW.md) | **Team-lead guide** — operating model, batch 1/2, dispatch order |
| [`sonnet-phase-execution-template.md`](sonnet-phase-execution-template.md) | Blank template for Phase 3+ |
| **Batch 1 (done)** | |
| [`sonnet-track-l-ingest-local.md`](sonnet-track-l-ingest-local.md) | Track L-a — local GBK ingest |
| [`sonnet-phase-1-normalize.md`](sonnet-phase-1-normalize.md) | Phase 1 — normalize seam |
| [`sonnet-track-v-validate.md`](sonnet-track-v-validate.md) | Track V V.1–V.2 — offline F1 |
| **Batch 2 (done)** | |
| [`opus-lead-orchestrator-batch-2.md`](opus-lead-orchestrator-batch-2.md) | **Opus lead** — dispatch / verify / gate / commit loop for batch 2 |
| [`sonnet-phase-1b-wire-normalize.md`](sonnet-phase-1b-wire-normalize.md) | Phase 1b — wire normalize into `label.py` |
| [`sonnet-track-l-b-cb-features.md`](sonnet-track-l-b-cb-features.md) | Track L-b — real CB feature math |
| [`sonnet-phase-2-rs-fix.md`](sonnet-phase-2-rs-fix.md) | Phase 2 — RS dtype fix |
| **Batch 3 (V.4/V.3/P.1/B.2 done; L-c next)** | |
| [`opus-lead-orchestrator-batch-3.md`](opus-lead-orchestrator-batch-3.md) | Opus lead — batch 3 operating model (V.4→V.3→L-c) |
| [`opus-lead-orchestrator-batch-3-continued.md`](opus-lead-orchestrator-batch-3-continued.md) | **Opus lead — START HERE** post–B.2 (gate 0.6599, L-c re-eval only) |
| [`sonnet-track-v-v4-offline-harness.md`](sonnet-track-v-v4-offline-harness.md) | Track V V.4 — offline proxy-F1 harness ✅ |
| [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) | Track V V.3 — human label acceptance spec ✅ |
| [`sonnet-feature-b-b2-size-entropy.md`](sonnet-feature-b-b2-size-entropy.md) | Feature B B.2 — `trd_size_entropy` (shipped `94ccb90`) |
| [`sonnet-track-l-c-cb-true-latency.md`](sonnet-track-l-c-cb-true-latency.md) | Track L-c — base prompt (true order→cancel latency) |
| [`sonnet-track-l-c-cb-true-latency-addendum.md`](sonnet-track-l-c-cb-true-latency-addendum.md) | **L-c mandatory addendum** — gate 0.6599, parquet eval history |

## Workflow (one line)

Opus orchestrator dispatches Sonnet (one track) → Sonnet implements (TDD, **no commit**) → Opus double-verifies → Opus commits on GATE PASS → human **proceed** → next track.

## Human-only work

| Guide | Purpose |
|-------|---------|
| [`../human_guides/track_v_validation_labels.md`](../human_guides/track_v_validation_labels.md) | Track V V.3 — seed validation labels |
| [`../human_guides/track_d_l2_procurement.md`](../human_guides/track_d_l2_procurement.md) | Track D — more L2 days |
| [`../data_inventory_report.md`](../data_inventory_report.md) | Local `data/` layout |

## New session kickoff

Paste into a fresh **Opus** chat:

> Open `docs/prompts/opus-lead-orchestrator-batch-3-continued.md` + base batch-3 orchestrator. B.2 shipped (130 tests, gate 0.6599). Wait for proceed, then dispatch L-c re-eval.

Or paste only the orchestrator file path — it is self-contained.
