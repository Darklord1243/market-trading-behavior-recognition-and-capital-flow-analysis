# Opus lead orchestrator — Batch 4 continued (post–P3.2 DEFERRED → V.3.3 ✅ → active gate 0.6689/n=53)

> **Paste this entire file** into a **new Claude Code Opus** session.
> **Human team lead:** approve each step with **"proceed to …"** between items.
> **Operating model:** `docs/prompts/opus-lead-orchestrator-batch-3.md`
>   (DISPATCH → MONITOR → INSPECT → VERIFY-1 → VERIFY-2 → GATE).
> **Batch 4 entry prompt:** `docs/prompts/opus-lead-orchestrator-batch-4.md` (V.3.2 / B.3b phases — now DONE; baseline numbers there are stale).
> **Spec of record:** `docs/LIS.md` **v1.6.6** §6.
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
| LIS state | v1.6.6 — V.3.3 verify ✅; active gate **0.6689/n=53**; B.3c/P3.1/P3.2 DEFERRED; Track D optional |
| Recent commits | `f2e8b94` V.3.3 CSV → `2f9ff8d` LIS v1.6.5 → … → `497bbce` feat B.3 |

### Active gate
| Set | n | weighted_f1 | Notes |
|-----|---|-------------|-------|
| **Active gate** | **53** | **0.6689** | post–V.3.3 20260622 addendum (ship criterion for all future slices) |
| **Prior reference** | 39 | 0.6449 | post–B.3 slice 1 (delta baseline) |
| **Continuity reference** | 24 {0617,0618} | **0.6599** | must not regress (held at floor) |
| Test suite | — | **141 passed, 2 xfailed** | L-c discriminating xfails dormant |
| Per-class n=53 | — | 游资 F1≈0.55 (s14) · 量化 F1≈0.70 (s18) · 散户 F1≈0.72 (s21) | 游资 still weakest |
| 20260622-only (diagnostic) | 14 | 0.7190 | informational |

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
| H.2 docs sync → v1.6.3 | ✅ | README + WORKFLOW prompt pack |
| P3.1 / P3.2 | ⛔ DEFERRED | v1.6.4 / v1.6.5 — probe-only, no ship |
| **V.3.3 verify (20260622)** | ✅ | `f2e8b94` — 14 rows; gate 0.6449/n=39 → **0.6689/n=53**; 53/53 joined |

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
Paste summary. If gate ≠ **0.6689/n=53** or suite ≠ 141/2xfail, stop and report delta. Clean up `gate.out`/`gate.err` after.

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

## P3.2 — ⛔ DEFERRED (feature probe + n=39 generalization complete; no ship, no code change; LIS v1.6.5)

**Human decision (binding):** P3.2 deferred; **gate banked at 0.6449/n=39.** Opus ran the mandated feature probe on
the triangle (no Sonnet, no gate run, no `rules.py` change). The strongest **new** axis — **buyer-account
concentration** (`buyer_top5` / `buyer_hhi`: HHI & top-k share of executed buy volume across distinct `BuyID`s in the
`deal` stream) — separated the *triangle* cleanly (002008 0.075 / 605198 0.133 vs 002354 0.011; the quant spreads buy
flow over 232k accounts) but **failed n=39 generalization** and was **rejected before any code**.

**Three independent blockers** (full table + per-class numbers in LIS v1.6.5 changelog and §6 Phase 3 status note):
1. **Conflates 游资 with 散户.** n=39 `buyer_top5` median: 量化 0.017 « {游资 0.046, 散户 0.024} — it is a
   **quant-vs-rest "few-participants / thin-liquidity" proxy**, not a 游资 axis. The single highest value in the set
   is a **散户** (`600193.SH` 0618 = 0.496, 111 buyer accounts). Wiring it into `DIMS_YOUZI` relocates the P3.1
   collateral failure to the 散户 class (F1≈0.67, R 8/15).
2. **Supporting hypotheses flat.** Buyer−seller asymmetry (`bms_top5`) shows no class separation (游资 median 0.000);
   OFI left the borderline name ≈flat and is mechanically dominated by the seal queue on a locked board.
3. **FNs resist it.** `002008` own `buyer_top5`=0.075 isn't decisively above several quants, and `seal_up`=0.389<0.5
   keeps any seal-gated variant dead; `605198` is the conf-0.50 borderline (V.3.3: 3-day-cumulative + QFII-diluted).

**Root cause:** the 游资 class is **heterogeneous** (n=10 spans a 56× `buyer_top5` range) and the FNs are **sealed
limit-up names where genuine cadence/cancel axes collapse to look quant** — no single new feature + global constant
resolves it.

**Known scorer-hard cases (documented, NOT chased):**
| Key | Label | Status |
|-----|-------|--------|
| `002008`(0616) | 游资 | genuine 游资 (V.3.3 conf 0.75; microstructure mismatch) |
| `605198`(0616) | 游资 | BORDERLINE (V.3.3 conf 0.50; 3-day-cumulative + QFII-diluted) |
| `000657`(0622) | 游资 | BORDERLINE scorer-hard (conf 0.55; 机构专用 on buy confounds) |

---

## V.3.3 — ✅ DONE (20260622 addendum; LIS v1.6.6)

**Result:** 14× 20260622 rows (游资=4, 量化=4, 散户=6). Harness: **53/53 joined, 0 dropped.**
**Active gate:** n=39→53, F1 **0.6449→0.6689** (+0.0240). n=24 continuity **0.6599 held**. No code change.
Improvement is **label expansion only** — not justification for a single-feature Sonnet slice.

---

## Next — Track D optional (HUMAN); no Sonnet until full-set probe re-run

**Binding disposition:** **0.6689/n=53** is the ship criterion; hold n=24 ≥ **0.6599**. P3.1/P3.2 deferrals stand.

- **Track D (human, optional)** — append **20260623+** LHB rows; prioritize **游资** (still weakest, F1≈0.55, n=14).
- When labels expand: human **"CSV ready"** → Opus verify → update LIS baseline.
- Before any Sonnet slice: re-run feature probes on the **full n=53+ set** (P3.2 lesson applies).

---

## What you do NOT do
- Do not re-run B.3b, B.3c, V.3.2, P3.1, or P3.2 (all settled).
- Do not re-open P3.1/P3.2 as constant or single-feature tweaks.
- Do not dispatch Sonnet without human-approved prompt AND full-set feature probe PASS.
- **Do not start Phase 4 GBDT** — not authorized.
- Do not edit `validation_labels.csv` (human-only).
- Do not implement tracks yourself.
- Do not grid-search thresholds on labels.

---

## Parallel / anytime
- **Track D** label/day expansion (e.g. 20260623) — Human append CSV → Opus verify on **"CSV ready"**.
- **Push** — git network ops on this box need the sandbox disabled + proxy `127.0.0.1:7890`; no `gh` CLI.
