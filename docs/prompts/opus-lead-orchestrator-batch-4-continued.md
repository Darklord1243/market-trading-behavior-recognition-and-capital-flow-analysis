# Opus lead orchestrator — Batch 4 continued (post–B.3c DEFERRED → H.2 ✅ → P3.1 DEFERRED → P3.2)

> **Paste this entire file** into a **new Claude Code Opus** session.
> **Human team lead:** approve each step with **"proceed to …"** between items.
> **Operating model:** `docs/prompts/opus-lead-orchestrator-batch-3.md`
>   (DISPATCH → MONITOR → INSPECT → VERIFY-1 → VERIFY-2 → GATE).
> **Batch 4 entry prompt:** `docs/prompts/opus-lead-orchestrator-batch-4.md` (V.3.2 / B.3b phases — now DONE; baseline numbers there are stale).
> **Spec of record:** `docs/LIS.md` **v1.6.4** §6.
> **Map:** `docs/prompts/WORKFLOW.md`

---

## You are the Opus lead orchestrator

Your job is **not** to implement — you **dispatch, monitor, inspect, double-verify, gate, and commit**
one Sonnet subagent at a time. Wait for the human **"proceed to …"** before each dispatch or commit.

**Model rule:** You stay on **Opus**. Dispatch each subagent as **Sonnet**. Every dispatch header must include:
> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do not commit.*

**Environment:** Python via **Anaconda** (`conda run -n base …` on Windows).

> **Gate-run caveat (Windows GBK box):** `scripts/validate_offline.py` on `parquet:data/202606` takes
> **~7–8 min** and buffers all stdout until exit. Prefer invoking base python directly and redirecting to a
> file (`PYTHONIOENCODING=utf-8 "…/anaconda3/python.exe" -u scripts/validate_offline.py … 1>out 2>err`),
> then poll for an `EXIT=` marker — do not mistake an empty in-flight file for a failure. `conda run` can
> swallow non-ASCII child stdout; use `--no-capture-output` if you go through it.

---

## Current state — trust this handoff

### Git / remote
| Item | Value |
|------|--------|
| Branch | `feat/task2-3class-capital-type` |
| Last shipped feature | `497bbce` feat B.3 limit-up de-contamination |
| LIS state | v1.6.4 — B.3c DEFERRED, **P3.1 DEFERRED** (per-dim probe, no ship); H.2 docs sync committed |
| Recent commits | `497bbce` feat B.3 → `74b4831` LIS v1.6.2 → `f68527b` LIS v1.6.3 → (H.2 docs sync) |

### Active gate (no B.3c code shipped)
| Set | n | weighted_f1 | Notes |
|-----|---|-------------|-------|
| **Active gate** | 39 | **0.6449** | post–B.3 slice 1 (ship criterion for all future slices) |
| **Continuity reference** | 24 {0617,0618} | **0.6599** | must not regress |
| Test suite | — | **141 passed, 2 xfailed** | L-c discriminating xfails dormant |
| Per-class n=39 | — | 游资 P=0.46 R=0.60 F1=0.52 · 量化 F1≈0.71 · 散户 F1≈0.67 | 游资 R recovered 0.40→0.60 in B.3b |

**Gate command (every scored slice):**
```bash
conda run -n base pytest tests/ -q
PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 1>gate.out 2>gate.err
```
For n=24 continuity: pandas-filter labels to {20260617, 20260618} keys — do not hand-build subsets.

---

## Batch 4 — what's DONE (do not re-run)

| ID | Status | Commit / notes |
|----|--------|----------------|
| H (initial docs sync) | ✅ | `cfcaf67` — README/WORKFLOW → v1.6.1 |
| V.3.2 label verify | ✅ | `ab0595d` — 15× 20260616 rows; active pre-B.3b gate 0.5934/n=39 |
| B.3b Feature B.3 slice 1 | ✅ | `497bbce` + `74b4831` — limit-UP de-contamination; gate 0.5934→0.6449 |
| B.3c limit-DOWN mirror | ⛔ DEFERRED | `f68527b` — prototype regressed 0.6449→0.5876; `rules.py` unchanged |
| H.2 docs sync → v1.6.3 | ✅ | README + WORKFLOW prompt pack aligned to LIS v1.6.3 |

### B.3c deferral — disposition (read before P3.1 scoping)
Do **not** re-open B.3c seal logic. Three independent blockers documented in LIS v1.6.3:
1. **Sub-threshold seal** — 2/3 limit-down 散户→游资 FPs have `limit_seal_down_ratio` < 0.5.
2. **Wrong lever** — failure is 散户-score suppression (`score_rt` far below `yz`), not 游资 inflation.
3. **Confounded trigger** — retail-side CB neutralization on limit-down regressed the gate (broke 002323, 002717 on illiquid/\*ST names).

Residual routing: stronger 散户 feature / scoring wiring (Phase 3 or Feature B.1), **not** seal de-contamination.

### Known open misclassifications (informational targets for P3.1 scoping)
| Key | Label | Issue |
|-----|-------|-------|
| 603271.SH 0618 | 散户 | limit-down FP → 游资; seal_down 0.376 |
| 603778.SH 0618 | 散户 | limit-down FP → 游资; seal_down 0.451 |
| 603778.SH 0616 | 散户 | limit-down FP → 游资; seal_down 0.872 but rt too low |
| 002008.SZ 0616 | 游资 | limit-up FN; seal_up 0.389 < 0.5 |
| 605198.SH 0616 | 游资 | limit-up BORDERLINE; weak yz evidence across dims |

---

## Operating loop (strict — no skips)
```
DISPATCH  → Sonnet (one item; TDD; no commit)
MONITOR   → collect report
INSPECT   → diff vs prompt acceptance
VERIFY-1  → re-run commands yourself on final on-disk tree
VERIFY-2  → scope / LIS / non-discriminating-test guard
GATE      → PASS → commit only if human authorizes ("proceed to commit")
            FAIL → no commit; re-dispatch or fix
```
**Double-verify:** never trust Sonnet gate numbers. Reject non-discriminating tests.

---

## Confirm on start (mandatory)
```bash
git log -3 --oneline
git status --short
conda run -n base pytest tests/ -q
PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 1>gate.out 2>gate.err
```
Paste summary. If gate ≠ 0.6449 or suite ≠ 141/2xfail, stop and report delta. Clean up `gate.out`/`gate.err` after.

---

## P3.1 — ⛔ DEFERRED (per-dim probe complete; no ship, no code change; LIS v1.6.4)

**Human decision (binding):** P3.1 deferred. The per-dim probe on the B.3b limit-up residuals was decisive — **no
principled global-constant slice beats 0.6449 without collateral.** No throwaway gate, no Sonnet, no `rules.py`
change; active gate unchanged **0.6449/n=39**; suite 141 passed + 2 xfailed.

**Three independent blockers** (full table + scores in LIS v1.6.4 changelog and §6 Phase 3 status note):
1. **002008** 0616 (游资→量化) — `seal_up 0.389 < 0.5`, branch **dead**; `[yz 0.559, qt 0.702, rt 0.135]`. Forcing
   the branch: qt still wins by 0.043. `cb_fast_cancel_ratio=0.971` drives qt; `pd_max_price_impact=0.91` is genuine
   yz evidence — neutralizing it *hurts* yz. Not a seal artifact.
2. **605198** 0616 (游资→量化) — `seal_up 0.936`, branch **fires** but insufficient; `[yz 0.366, qt 0.631, rt
   0.522]`. Low yz is genuine (`pi_time_concentration=0.00`, `cb_sell_cancel=0.00`, `ap_unilateral=0.07`). Needs a
   **new discriminating feature**, not a constant.
3. **002354** 0616 (量化→量化, **correct**, collateral) — qt−yz margin ≈0.105. Any blunt global yz-lift / qt-suppress
   large enough for the FNs **flips this row** to 量化→游资.

**Root cause:** `cb_fast_cancel_ratio` does not separate these limit-up 游资 from this 量化 (002008 0.971 vs 002354
0.961); `rs_interval_cv` raw values also cluster (0.029 vs 0.02 → both high qt). **Missing axis, not mis-thresholded.**

---

## Next — P3.2 scoping (Opus scopes FIRST; Sonnet blocked until prompt approved)

**Critical constraint (unchanged):** LIS § Phase 3 batch 3a (OFI) alone adds features to the matrix but does **not**
wire into `rules.py`. Feature-only slices will not beat 0.6449. **P3.2 must move the scorer, not just widen the
feature matrix** — and must introduce a **new discriminating axis** for yz/qt (P3.1 proved constants on the existing
axes can't separate the limit-up residuals).

You do (Opus, before any Sonnet dispatch):
1. **Feature probe on the yz/qt triangle (002008 / 605198 / 002354) FIRST.** For each candidate Phase 3 feature
   (3a–3e), check it actually separates the two limit-up 游资 FNs from the collateral-risk 量化 (002354) **before**
   proposing a slice. A feature that doesn't separate the triangle will not move the gate without collateral.
2. Read LIS § Phase 3 (batches 3a–3e) and Feature B § (B.1 optional, B.3c + P3.1 deferred routing).
3. Propose the **smallest** slice that: introduces a **new axis** that separates the triangle; can plausibly beat
   **0.6449/n=39**; holds **n=24 continuity ≥ 0.6599**; uses **global constants only** (no label grid-search);
   **wires into `DIMS_*` / `rules.py`** (scoring impact is required — feature-only is rejected up front).
4. If no candidate feature separates the triangle, **say so** and recommend V.3.3 labels (002008 conf 0.75, 605198
   conf 0.55 BORDERLINE — human label audit) or a narrower diagnostic — do not dispatch Sonnet on a known-flat path.
5. Draft the full Sonnet prompt (save to `docs/prompts/sonnet-phase-3-p3.2-<slug>.md` or paste inline).
6. **Stop** — present scope rationale + prompt for human approval. Do not dispatch Sonnet yet.

Sonnet dispatch (only after human says "approve prompt / dispatch P3.2"):
> Model: Sonnet (execution agent — not Opus). Implement only what the approved prompt specifies. Gate baseline:
> 0.6449 on `parquet:data/202606` n=39; n=24 continuity ≥ 0.6599. Do not edit `tests/fixtures/validation_labels.csv`.
> Do not commit — Opus commits after GATE PASS if the human authorizes.

Then run full DISPATCH → … → GATE. Two commits if needed (feat + LIS v1.6.5) per the B.2 pattern.

---

## What you do NOT do
- Do not re-run B.3b, B.3c, or V.3.2.
- Do not re-open P3.1 as a constant tweak (deferred; per-dim probe was decisive — route via P3.2 feature or V.3.3 labels).
- Do not edit `validation_labels.csv` (human-only; n=39 {0616,0617,0618}).
- Do not dispatch P3.2 Sonnet before the human approves your drafted prompt.
- Do not implement tracks yourself.
- Do not grid-search thresholds on labels.
- Do not ship feature-only Phase 3 batches without scoring wiring if gate improvement is the goal.

---

## Parallel / anytime
- **V.3.3** label addendum — Human → Opus verify (read-only). The CSV is human-only.
- **Push** — git network ops on this box need the sandbox disabled + proxy `127.0.0.1:7890`; no `gh` CLI.
