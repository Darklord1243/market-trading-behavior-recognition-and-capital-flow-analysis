# B-board Report — Phase 2 session handoff

**Purpose.** Everything a fresh Claude Code session needs to draft **Phase 2** of the solution report
without re-deriving Phase 1. Read this file first, then the two Phase-1 artifacts it points to. Do
**not** re-read the whole doc tree — everything load-bearing is cited here.

**Repo:** `D:/market-trading-behavior-recognition-and-capital-flow-analysis`
**Branch:** `feat/phase6-parquet-submit` · **HEAD:** `f6f3097`
**Today:** 2026-07-06 · A-board through Jul 10 · B-board Jul 13–24 · report ≈ 20% of final
**Role:** competition report architect — **read-only on `src/` / `rules.py` / `features.py` /
`label.py` / `validation_labels.csv`**; writes confined to `docs/report/`.

---

## 1. Where we are (Phase 1 DONE + approved)

The report **outline + section map** is approved and frozen (see §3 for the outline). Phase 1
delivered and the user approved:

| Artifact | Path | State |
|---|---|---|
| Report ↔ code parity ledger | `docs/report/code-parity-ledger.md` | 24 main rows + 6-row §5.3 sub-ledger + **Row 15 detail** (gate split). **Authoritative for all facts/numbers.** |
| §5 draft — Evaluation & validation methodology | `docs/report/draft-section-05-evaluation.md` | Complete, report-ready prose, 5 exhibit tables, CLAIM/ADMIT tags inline |

**Read these two first.** The ledger is the single source of truth for every number; the §5 draft is
the tone/format template every other section should match (inline **[CLAIM]** / **[ADMIT]** tags,
markdown exhibit tables, honest-limits paragraphs).

---

## 2. Phase 2 task (this session)

Draft the following sections, **outline order, §5 tone**, into `docs/report/`. One file per section
(`draft-section-0X-<name>.md`) unless the user says otherwise. Keep every load-bearing statement
traceable to a parity-ledger row; if you assert a fact not yet in the ledger, **add a ledger row for
it** (narrative must not drift from code).

1. **§0 — Executive summary** (short; derive from §5 + §6). Problem, two coupled tasks (0.4/0.6),
   methodology-first posture, headline: deterministic pipeline + offline gates + honest ceiling.
2. **§6 — Results & honest ceiling** (short; derive from §5). Board band, gate history pointer,
   collapse-day structural cap, B-board as the compounding prize.
3. **§4.3 — Modeling: the H1 board-space discovery** (lead with H1). Lean on §5.4 cross-refs; do not
   duplicate the full A/B tables — reference them.

**Do NOT** draft §1, §2, §3, §7, §8 this session unless the user extends scope. §7 in particular is
deferred (see §5 below for the one number it will need).

---

## 3. The approved outline (frozen — do not restructure)

- **§0** Executive summary
- **§1** Problem framing & task decomposition *(Methodology)*
- **§2** System design & pipeline *(System design)* — 2.1 architecture · 2.2 reproducibility contract · 2.3 dual ingest adapters
- **§3** Feature engineering *(Features)* — 3.1 coverage vs 89 · 3.2 discriminating families · 3.3 rank normalization (H1 seam) · 3.4 compliance-by-construction
- **§4** Modeling *(Modeling)* — 4.1 rules over GBDT · 4.2 Euclidean clustering + naming · **4.3 H1 board-space discovery**
- **§5** Evaluation & validation methodology *(Evaluation)* — **DRAFTED** (5.1 Track V · 5.2 gates + limits · 5.3 falsification · 5.4 paired A/B + H1 · 5.5 hard-key case/control)
- **§6** Results & honest ceiling
- **§7** Reproducibility & compliance *(gates code review)*
- **§8** Limitations & future work

Mapping to organizer's five required content areas (spec §5.4): Methodology→§1, System design→§2,
Features→§3, Modeling→§4, Evaluation→§5. §7 gates the code audit (§5.5 of spec).

---

## 4. Differentiation story (the through-line every section serves)

Thesis: **methodological rigor and honesty under an adversarial, partly-unobservable objective** — not
a headline score. Four pillars (all evidenced in §5 / ledger):

1. **H1 board-space discovery** — reverse-engineered that board Task-1 ≈ Euclidean-feature-space
   silhouette, not DTW naming; two deterministic paired days. (§4.3, §5.4)
2. **Deterministic paired A/B under best-not-latest** — determinism confirmed; explore at 0 average
   cost. (§5.4)
3. **Falsified-slices discipline** — six pre-registered gates honored; nothing tuned to the board.
   (§5.3)
4. **Hard-key case/control honesty** — formally characterized where our instruments go blind, and
   stopped. (§5.5)

Binding cross-current: **compliance-first** (offline proxy truth never the board's answers; no LLM in
inference; seed-fixed reproducibility) — exactly what the TOP-15 code audit checks.

---

## 5. CLOSED — do not re-litigate or re-engineer

- **H1 SUPPORTED (n=2)**; Task-1 clustering **method** is a ±0.02 lever, spent; DTW-complete is
  explore-only, shipped default-OFF; euclidean is the scored-day floor.
- **Hard-key channel closed** — no offline signature; no Task-2 rule / trained-head work for A-board
  score boost this week.
- **No tuning to board scores** (LIS §3.3 auto-DQ). No edits to `rules.py`, `features.py`, `label.py`,
  `validation_labels.csv` without an explicit human ask.
- **Do not re-run** the six falsified slices or reopen 0626/0629 tuning.

---

## 6. Updates since Phase 1 (fold these in)

### 6.1 Parity-ledger Row 15 was split (Cursor, 2026-07-06) — USE THE NEW FORM
The "active gate 0.6773" one-liner was **overstated**. The ledger now separates:
- **Frozen ship gate (cite this):** **0.6773 / n=77**, through-0624, `parquet:data/202606`, labels
  commit `23a4498`, LIS v1.6.8. 游资 F1 ≈ 0.59 at ship time.
- **Current corpus-split verify:** full CSV (154 rows/11 days) needs **one parquet root per run** —
  June-corpus **0.6438/n=122**, July-corpus **0.7824/n=32**; combined n=154 is **not** one harness
  output yet. Intent floor **0.6750/n=115** is a separate harness.

The §5 draft has been reconciled to this (frozen-ship-gate wording, no single live-number claim).
**§0/§6 must inherit this framing** — cite 0.6773 only as the frozen through-0624 snapshot; never
imply a single current live gate. See ledger **Row 15 detail A/B/C**.

### 6.2 20260703 submission slot is OPEN (ops — human uploads)
Pre-staged `outputs/20260703/submit.zip` (euclidean floor, pre-flight-clean) should be uploaded now
that the platform advanced to the 20260703 slot. **Human handles upload**; this session does not
generate/submit. Relevant only to §6/§7 as evidence of ongoing daily attendance — do not assert 0703
is banked until the human confirms the instant score.

### 6.3 行情阶段 (market-phase F1) DingTalk question — NO REPLY (organizers skipped)
The clarification we asked (how 行情阶段识别分 is computed from our two CSVs) got **0 reply** — treat
as **intentionally unanswered**. Report handling (decision, do not reopen): in **§8 limitations**,
footnote 行情阶段 as an **open organizer question, asked and unanswered**, and state we therefore
model only the two CSV outputs the spec concretely defines (capital_type, capital_intention) and do
not claim coverage of a market-phase component whose scoring object the organizer never disclosed.
This is honesty, not a gap to fix. (Do not draft §8 this session — just carry the decision forward.)

---

## 7. Numbers you will need (all from the ledger — do not re-derive)

| Fact | Value | Ledger anchor |
|---|---|---|
| Task weights | Task-1 0.4 / Task-2 0.6 | spec §5.3 |
| Frozen ship gate | 0.6773 / n=77 (through-0624) | Row 15 detail A |
| Current June-corpus verify | 0.6438 / n=122 | Row 15 detail B |
| Current July-corpus verify | 0.7824 / n=32 | Row 15 detail B |
| Intent gate floor | 0.6750 / n=115 | Row 15 detail C |
| Board paired A/B 0701 | eucl 0.5245 > dtw 0.5053 | Row 10 / §5.4 |
| Board paired A/B 0702 | eucl 0.5566 > dtw 0.5290 | Row 10 / §5.4 |
| Determinism | identical zip → 0.5245 twice | Row 18 |
| Collapse days | 0626 0.3265 / 0629 0.3333 | Row 20 |
| Good-day band | ~0.45–0.56 | §5.5 table |
| Test suite | 234 passed, 2 xfailed | Row 24 |
| Features built | 35-col matrix; 24 reference-matched, 31 clustering (P2/F5 — "34 of 89" retired) | Row 5 |

**Do not run the gate / pytest to "confirm" these while drafting** — they are read-only prose inputs.
Rows 5/15/24 are the three that still need a one-time frozen command output before *report lock*
(not before drafting); that is a separate pre-lock task, not Phase 2.

---

## 8. Working rules for the session

- Read-only on code; writes only under `docs/report/`.
- Match the §5 draft's format: inline **[CLAIM]** / **[ADMIT]**, markdown exhibit tables, an
  honest-limits paragraph per section where relevant.
- Every new load-bearing fact → a parity-ledger row (edit `code-parity-ledger.md`).
- Economical shell; do not spawn subagents (this box is shell-heavy sensitive).
- Return per section: path created, word count, and any new ledger rows added.
- Wait for the user's review between Phase 2 sections if they ask; otherwise draft §0, §6, §4.3 in
  that order and report back.

---

## 9. Source docs (only if you need to go deeper than the ledger)

- `docs/hypotheses/score-boost-direction-20260704.md` — H1 result + score anatomy (§4.3 backbone)
- `docs/hypotheses/p5.7-board-paired-ab-0701.md` — paired A/B + determinism (§5.4)
- `docs/hypotheses/hard-key-case-control-20260706.md` — collapse study (§5.5)
- `docs/hypotheses/competitive-gap-audit-20260703-fable5.md` — ceiling arithmetic (§6)
- `docs/LIS.md` — §3 compliance, §4 module map, §5 hypotheses, §6 Track V (§1/§2/§3/§7 of report)
- `docs/competition-spec/topic-specifications-and-data.en.md` — §5.4 report reqs, §5.5 code audit
