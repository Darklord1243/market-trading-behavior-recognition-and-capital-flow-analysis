# Execution prompts (Sonnet / Claude Code)

Reusable prompts for **implementation agents** (Sonnet-class). Strategy and LIS maintenance stay with the
high-reasoning lead (Opus); executors read **one prompt file + `docs/LIS.md` §6** for the target phase or track.

**LIS version:** v1.6.7 (2026-06-24). Batch 4: V.3.2 ✅ · B.3b ✅ (prior gate 0.6449/n=39) · B.3c/P3.1/P3.2 **DEFERRED** · **V.3.3 ✅ active gate 0.6971/n=65** (20260622+20260623 addenda) · optional Track D (20260624+ labels). Phase 4 GBDT not authorized.

> **New here? Read [`WORKFLOW.md`](WORKFLOW.md) first** — operating model (Opus → Sonnet → verify), batch status, dispatch order.

## Batch status

| Batch | Status | Suite |
|-------|--------|-------|
| **1** (parallel: Track L-a, Phase 1, Track V V.1–V.2) | ✅ DONE | 79 passed |
| **2** (sequential: Phase 1b → L-b → Phase 2) | ✅ DONE | 101 passed |
| **3** (V.4 ‖ V.3 → P.1 → B.0/B.2 → **L-c re-eval**) | ✅ DONE (L-c swap **rejected**, infra kept) | 131 passed |
| **4** (… → V.3.3 ✅ **0.6971/n=65** → Track D optional) | ✅ DONE | 154 passed, 2 xfailed (post-P6.1) |
| **5** (P6.1 ✅ parquet submit → Tianchi 0.2597 → refinement) | 🔄 in progress | 154 passed, 2 xfailed |

## Files

| File | Purpose |
|------|---------|
| [`handoff-b-board-20260713-score-02411.md`](./handoff-b-board-20260713-score-02411.md) | Board B day-1 score 0.2411 triage |
| [`fable5-guide-lhb-labeling.md`](./fable5-guide-lhb-labeling.md) | **NEW** — Fable 5 as *guide*: emits per-day LHB dig-prompt + audits returned `capital_type` labels (Board-B offline validation) |
| [`sonnet-lhb-labeling-dig.md`](./sonnet-lhb-labeling-dig.md) | **NEW** — standalone self-auditing executor (Sonnet/Cursor) for public-LHB `capital_type` labeling; thin path if the guide layer is skipped |
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
| **Batch 4 (V.3.3 ✅ 0.6971/n=65 · B.3c/P3.1/P3.2 deferred · Track D optional)** | |
| [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md) | Opus lead — Batch 4 (Track V / deferred P3; baseline reference) |
| [`opus-lead-orchestrator-batch-5-phase6-submit.md`](opus-lead-orchestrator-batch-5-phase6-submit.md) | Opus lead — Batch 5 P6.1 (**DONE** — parquet main + submit.zip) |
| [`opus-lead-orchestrator-batch-5-continued.md`](opus-lead-orchestrator-batch-5-continued.md) | **Opus lead — START HERE** (post-upload triage; Tianchi 0.2597; refinement) |
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

> Open `docs/prompts/opus-lead-orchestrator-batch-5-continued.md` (current handoff; spec of record `docs/LIS.md` v1.6.7 §6). P6.1 ✅ on `feat/phase6-parquet-submit`; first Tianchi instant **0.2597** (verification only — do not tune against). Phase A triage → human picks P5.1 / P6.1b / P6.2. Active proxy gate **0.6971/n=65**. Do not start Phase 4 GBDT.

Or paste only the orchestrator file path — it is self-contained.
