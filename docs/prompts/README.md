# Execution prompts (Sonnet / Claude Code)

Reusable prompts for **implementation agents** (Sonnet-class). Strategy and LIS maintenance stay with the
high-reasoning lead (Opus); executors read **one prompt file + `docs/LIS.md` §6** for the target phase or track.

**LIS version:** v1.6.5 (2026-06-24). Batch 3 closed. Batch 4: V.3.2 labels ✅ · B.3b Feature B.3 shipped (active gate **0.6449/n=39**) · B.3c limit-down mirror **DEFERRED** · H.2 docs sync ✅ · P3.1 first slice **DEFERRED** (per-dim probe) · P3.2 new-feature slice **DEFERRED** (buyer-concentration, n=39 generalization fail) · **gate banked → Track D next** (no single-feature slice until label/data expansion; Phase 4 GBDT not authorized).

> **New here? Read [`WORKFLOW.md`](WORKFLOW.md) first** — operating model (Opus → Sonnet → verify), batch status, dispatch order.

## Batch status

| Batch | Status | Suite |
|-------|--------|-------|
| **1** (parallel: Track L-a, Phase 1, Track V V.1–V.2) | ✅ DONE | 79 passed |
| **2** (sequential: Phase 1b → L-b → Phase 2) | ✅ DONE | 101 passed |
| **3** (V.4 ‖ V.3 → P.1 → B.0/B.2 → **L-c re-eval**) | ✅ DONE (L-c swap **rejected**, infra kept) | 131 passed |
| **4** (V.3.2 ✅ → B.3b ✅ 0.6449 → B.3c **deferred** → H.2 ✅ → P3.1 **deferred** → P3.2 **deferred** → gate banked, Track D next) | 🔄 in progress | 141 passed, 2 xfailed |

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
| **Batch 3 (V.4/V.3/P.1/B.0/B.2 done; L-c re-eval rejected)** | |
| [`opus-lead-orchestrator-batch-3.md`](opus-lead-orchestrator-batch-3.md) | Opus lead — batch 3 operating model (V.4→V.3→L-c) |
| [`opus-lead-orchestrator-batch-3-continued.md`](opus-lead-orchestrator-batch-3-continued.md) | Opus lead — post–B.2 continuation (gate 0.6599, L-c re-eval) |
| [`sonnet-track-v-v4-offline-harness.md`](sonnet-track-v-v4-offline-harness.md) | Track V V.4 — offline proxy-F1 harness ✅ |
| [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) | Track V V.3 — human label acceptance spec ✅ |
| [`sonnet-feature-b-b2-size-entropy.md`](sonnet-feature-b-b2-size-entropy.md) | Feature B B.2 — `trd_size_entropy` (shipped `94ccb90`) |
| [`sonnet-track-l-c-cb-true-latency.md`](sonnet-track-l-c-cb-true-latency.md) | Track L-c — base prompt (true order→cancel latency) |
| [`sonnet-track-l-c-cb-true-latency-addendum.md`](sonnet-track-l-c-cb-true-latency-addendum.md) | L-c mandatory addendum — gate 0.6599; **swap rejected `51787d0`** |
| **Batch 4 (V.3.2 ✅ · B.3b Feature B.3 ✅ 0.6449 · B.3c/P3.1/P3.2 deferred · gate banked → Track D)** | |
| [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md) | **Opus lead — START HERE** (post–P3.2-deferral handoff: gate banked 0.6449/n=39, Track D next; no Sonnet slice) |
| [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md) | Opus lead — batch 4 entry prompt (V.3.2/B.3b; baseline numbers superseded by LIS v1.6.3) |

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

> Open `docs/prompts/opus-lead-orchestrator-batch-4-continued.md` (current handoff; spec of record `docs/LIS.md` v1.6.5 §6). Batch 4: V.3.2 labels ✅, B.3b Feature B.3 shipped (active gate **0.6449/n=39**, 游资 R 0.40→0.60); B.3c, P3.1, and P3.2 all **deferred** (probe-only, no ship). The gate is **banked** — no Sonnet slice to dispatch: per the binding disposition, no further constant / single-feature slices on the limit-up 游资 FNs until **Track D** (human) expands labels/days. Do not start Phase 4 GBDT.

Or paste only the orchestrator file path — it is self-contained.
