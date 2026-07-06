# Report Assembly Checklist

> **Status:** Phase 4b. One row per section: draft path, word count (2026-07-06), the parity-ledger
> rows it leans on, and any open item. The master stitch is `draft-full-report.md` (regenerate from
> the section files; do not hand-edit it). Section word total ≈ **7,893** (master stitch ≈ 7,575 after
> per-file draft-status blocks are dropped).

| § | Draft file | Words | Ledger rows / anchors | Open items |
|---|---|---:|---|---|
| §0 Executive summary | `draft-section-00-executive-summary.md` | 515 | 1, 2, 10, 13, 15A, 17, 19, 20, 21; spec §5.3 | — |
| §1 Problem framing | `draft-section-01-problem-framing.md` | 464 | spec §5.3 (weights); §6.3 handoff (行情阶段→§8) | — |
| §2 System design | `draft-section-02-system-design.md` | 588 | 1, 2, 22 | — |
| §3 Features | `draft-section-03-features.md` | 585 | 3, 4, 5, 6, 7; **F5** | **P2 RESOLVED** — "34 of 89" retired; §3.1 carries the author-confirmed 24/≈30/3/2, 31-cluster mapping |
| §4.1 Task-2 rules | `draft-section-04-1-task2-rules.md` | 402 | 8, 9, 22, 23 | — |
| §4.2 Task-1 clustering | `draft-section-04-2-task1-clustering.md` | 386 | 3, 10, 12 | — |
| §4.3 H1 discovery | `draft-section-04-3-h1-board-space.md` | 697 | 10, 11, 12 (E5.3/E5.4 cross-ref) | — |
| §5 Evaluation | `draft-section-05-evaluation.md` | 2,399 | 3, 13, 14, 15, 16, 17, 18, 19, 20, 21 | F2 combined-n=154 shown as two slices (Option A) — keep, do not average |
| §6 Results & ceiling | `draft-section-06-results.md` | 633 | 5, 10, 15A/B/C, 16, 18, 19, 20, 21, 24 | — |
| §7 Reproducibility | `draft-section-07-reproducibility.md` | 555 | 1, 2, 22, 23, 24; G1/G3 done, P1 fixed, G4→§8 | Code edits (G1/P1) **committed `b26bfed`** ✅ |
| §8 Limitations | `draft-section-08-limitations.md` | 663 | 5, 7, 8, 16, 20, 21 | 行情阶段 accepted-open; G4 holiday stub (P2 resolved) |

## Cross-section invariants (verified during assembly)

- **No single live-gate number.** §0/§5/§6 cite **0.6773 / n=77** only as the frozen through-0624 ship
  gate; corpus-split verifies (0.6438/n=122, 0.7824/n=32) are shown as slices, never a combined live
  figure (ledger Row 15 detail; F2 Option A). ✅
- **H1 stated with its caveats.** §4.3/§5.4 keep the n=2 + partly-tautological caveats (Row 11); the
  load-bearing evidence is the two falsifications, not the positive reproduction. ✅
- **Honesty capstone consistent.** Hard-key (§5.5→§6→§8), falsified slices (§5.3), and the
  found-and-fixed P1 (§7.2) all reflect the same "surface, don't paper over" posture. ✅
- **Feature-count accuracy.** §3.1 and §8.2 carry the author-confirmed reproducible mapping (35-col
  matrix; 24 exact/renamed reference, ≈30 w/ family, 3 novel, 2 flags; 31 clustering after 4 EXCLUDE).
  The unreproducible "34 of 89" is retired. ✅ **P2 RESOLVED**.

## Open items to close before report lock (not this session)

1. ~~**P2** — author confirms §3.1 / Row 5 feature-count wording.~~ **RESOLVED 2026-07-06** — wording
   confirmed and applied to §3.1, §8.2, Row 5, F5.
2. ~~**Code edits** — human reviews/commits the staged G1 + P1 changes.~~ **DONE** — committed as
   `b26bfed` (G1 `pyarrow` + P1 `fillna` + pin cap).
3. **Polish pass (Phase 5)** — **executive sections §0/§6 stripped of inline tags** and a tag legend
   added to §0; technical sections (§1–§5, §7, §8) **retain** **[CLAIM]** / **[ADMIT]** as ledger
   scaffolding, to be resolved to final prose at lock. Remaining polish: resolve the technical-section
   tags; add any §1/§2/§4/§6 figures beyond the specced E5.1–E5.5 (`figure-specs.md`).
4. **Deliverable build** — `project_solution_report.docx` + `project_solution.zip` (spec §5.5) —
   plus optional figure render (E5.1–E5.5). A later phase; **not** in scope now (no .docx, no merged
   zip this session).

## Section-status legend

All 11 sections are **drafted** (report-ready prose). §5 was Phase-1; §0/§6/§4.3 Phase-2;
§4.2/§4.1/§2/§3/§1/§7/§8 Phase-3b; §3.1/§8.2 reconciled to F5 in Phase-4a; §0/§6 tag-stripped +
committed-state sync in Phase-5. **Tags:** stripped in §0/§6 (executive), retained in §1–§5/§7/§8
(technical). Nothing is a stub.
