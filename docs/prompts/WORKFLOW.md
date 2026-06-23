# Execution workflow — how the pieces fit (for the team lead)

> Plain-language map of the Sonnet prompt pack. **Not** a prompt — read this in 5 minutes, then dispatch.
> Spec of record: `docs/LIS.md` **v1.6.5** §6.

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

## Batch 4 — V.3.2 ✅ → B.3b Feature B.3 ✅ → B.3c DEFERRED → H.2 ✅ → P3.1 DEFERRED → P3.2 DEFERRED → Track D

```
HUMAN          appended validation labels (15× 20260616 LHB seats) → V.3.2 (n=39)
   ↓
OPUS           V.3.2 verify (read-only) → active baseline 0.5934/n=39 on parquet:data/202606
   ↓
OPUS → SONNET  B.3b Feature B.3 — limit-UP regime de-contamination; gate 0.5934 → 0.6449 (游资 R 0.40→0.60)
   ↓
OPUS → SONNET  B.3c limit-DOWN mirror — prototype regressed 0.6449→0.5876 → DEFERRED (rules.py unchanged)
   ↓
OPUS           H.2 docs sync (this file + README → v1.6.3) ✅
   ↓
OPUS           P3.1 Phase 3 first slice — per-dim probe → ⛔ DEFERRED (no ship; LIS v1.6.4)
   ↓
OPUS           P3.2 new-feature probe (buyer-concentration) → ⛔ DEFERRED (n=39 generalization fail; LIS v1.6.5)
   ↓
HOLD           gate banked at 0.6449/n=39; no single-feature slices on limit-up 游资 FNs until Track D label/data
```

| Order | Owner | Prompt / spec | Status |
|-------|-------|---------------|--------|
| V.3.2 | **Human labels → Opus verify** | [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) §1–§5 | ✅ (n=39; baseline 0.5934) |
| B.3b | Sonnet | Feature B.3 limit-up de-contamination | ✅ `497bbce`+`74b4831` (gate 0.6449) |
| B.3c | Sonnet | Feature B.3 limit-down mirror | ⛔ **DEFERRED** `f68527b` (regressed; 3 blockers in LIS v1.6.3) |
| H.2 | Opus | docs sync (this file + README → v1.6.3) | ✅ |
| P3.1 | Opus | Phase 3 first slice (scorer-moving) — per-dim probe | ⛔ **DEFERRED** (no ship; 3 blockers, LIS v1.6.4) |
| P3.2 | Opus | Phase 3 new-feature probe — buyer-account concentration | ⛔ **DEFERRED** (n=39 generalization fail; conflates 游资/散户, LIS v1.6.5) |
| Track D | **Human** | more L2 days / 游资 labels (stabilize heterogeneous 游资 class) | 🔜 next (no Sonnet slice until then) |
| Orchestrator | Opus | [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md) | **active handoff** |

**Active gate (every future scored slice):** weighted_f1 **0.6449 / n=39** on `parquet:data/202606`; hold
**n=24 {0617,0618} continuity ≥ 0.6599**. Per-class n=39: 游资 R=0.60 · 量化 F1≈0.71 · 散户 F1≈0.67.
The CSV is **human-only** — Opus/Sonnet never label or "fix" rows. **Gate is banked (v1.6.5):** no further
constant / single-feature slices on the limit-up 游资 FNs until Track D label/data expansion. **Known scorer-hard
cases (documented, not chased):** `002008`(0616) genuine 游资 (V.3.3 conf 0.75, microstructure mismatch) ·
`605198`(0616) borderline 游资 (V.3.3 conf 0.50, 3-day-cumulative/QFII-diluted). **Phase 4 GBDT NOT authorized.**

**B.3c deferral (do not re-open seal logic):** the limit-down 散户→游资 FPs have sub-threshold seals
(`limit_seal_down_ratio` < 0.5 on 2/3); the failing lever is 散户-score suppression, not 游资 inflation; and
retail-side CB neutralization regressed the gate on illiquid/\*ST names. Residual routing → stronger 散户
feature/scoring (Phase 3 or Feature B.1), **not** seal de-contamination.

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

**Opus lead (recommended):** paste [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md) into a new **Claude Code Opus** chat (current handoff; spec of record LIS v1.6.5 §6). Batch 4 V.3.2/B.3b are done (active gate **0.6449/n=39**); B.3c, **P3.1, and P3.2 are all deferred** (probe-only, no ship). The gate is **banked** — there is **no Sonnet slice to dispatch**: per the binding disposition, no further constant / single-feature slices on the limit-up 游资 FNs until **Track D** (human) expands labels/days. Do not start Phase 4 GBDT.

**Manual / Sonnet-only:** copy the next Sonnet prompt below → paste into Claude Code **Sonnet** → you verify → commit.

1. Read this file + LIS §4 snapshot.
2. Open the **next** prompt (batch 4 table) → copy whole file (or let Opus orchestrator read it).
3. Sonnet implements (TDD); **Opus lead commits** after GATE PASS unless you said otherwise.
4. **Double-verify** — `pytest tests/ -q`, scope diff, smoke if applicable; for any future scored slice, the **proxy-F1 must beat 0.6449/n=39 and hold n=24 {0617,0618} ≥ 0.6599**.
5. Dispatch **one** next item after your proceed.

**Batch 4 status:** V.3.2 ✅ · B.3b Feature B.3 ✅ (0.6449/n=39) · B.3c **deferred** · P3.1 **deferred** (per-dim probe) · P3.2 **deferred** (buyer-concentration, n=39 generalization fail) · **gate banked → Track D next** — see [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md) and LIS v1.6.5 §6.

---

## Links

- **Opus orchestrator (batch 4 — current):** [`opus-lead-orchestrator-batch-4-continued.md`](opus-lead-orchestrator-batch-4-continued.md)
- Opus orchestrator (batch 4 entry, baseline stale): [`opus-lead-orchestrator-batch-4.md`](opus-lead-orchestrator-batch-4.md)
- Opus orchestrator (batch 3 continued): [`opus-lead-orchestrator-batch-3-continued.md`](opus-lead-orchestrator-batch-3-continued.md)
- Opus orchestrator (batch 3 base): [`opus-lead-orchestrator-batch-3.md`](opus-lead-orchestrator-batch-3.md)
- Opus orchestrator (batch 2, done): [`opus-lead-orchestrator-batch-2.md`](opus-lead-orchestrator-batch-2.md)
- Prompt index: [`README.md`](README.md)
- Template: [`sonnet-phase-execution-template.md`](sonnet-phase-execution-template.md)
- LIS: [`../LIS.md`](../LIS.md)
- Local data: [`../data_inventory_report.md`](../data_inventory_report.md)
