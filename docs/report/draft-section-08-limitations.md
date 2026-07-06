# §8 — Limitations & Future Work

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 5, 7, 8, 16, 20, 21). This section is deliberately
> unflinching — under a partly-unobservable objective, stating the boundaries of the method *is* the
> credibility argument (see §5.5).

We separate limitations we **characterized and accepted** from seams that are **future work**.

## 8.1 Accepted boundaries (studied, not fixable this cycle)

**The hard-key collapse channel is blind.** Two days (0626/0629 ≈ 0.33) collapsed with no scorer
change, and the §5.5 case/control study showed they are market-regime *opposites* yet share no offline
dimension that separates them from good days. **[ADMIT]** The collapse is driven by the hidden answer
key, is **not predictable in advance**, and structurally caps the A-board moving average — roughly two
of five days drag it down regardless of method, so a 0.7 *average* is likely unreachable this week
(Rows 20, 21). We chose to stop rather than fabricate signal across this boundary; the compounding
prize is the B-board (§6.3).

**The offline proxy is a smoke detector, not a leaderboard simulator.** The Track-V truth set is
small and class-imbalanced — 龙虎榜 over-represents 游资, and 量化/散户 are only weakly publicly
attributable — so its class prior is not the hidden T+5 prior (Row 16). **[ADMIT]** We used it
accordingly: trust large regressions, discount sub-0.01 wins. No claim in this report rests on a
third-decimal proxy delta.

**We forgo a possibly-real GBDT lift.** `src/model.py` is a declared stub; we ship rules, not a
trained head, because any GBDT lift is offline-unmeasurable and could be overfitting proxy noise
(Row 8). **[ADMIT]** A trained head might add genuine lift we cannot verify — that is a knowing
trade of unverifiable upside for an auditable, compliant scorer (§4.1).

## 8.2 Known seams (bounded, low-impact, documented)

**Market-phase (行情阶段) is an open organizer question.** A field appears in the scoring discussion,
but its grading object was never disclosed and a direct clarification we asked went **unanswered**. **[ADMIT]**
We therefore model only the two CSV outputs the spec concretely defines (`capital_type`,
`capital_intention`) and do not claim coverage of a market-phase component whose scoring target is
unknown. This is a stated scope boundary, not a defect to patch.

**Feature coverage is a chosen subset of the 89-field reference set.** We build a 35-column matrix —
24 columns match the reference set by exact name or rename (≈30 with family consolidations), 3 are
novel engineered columns, and 2 are internal flags; 31 feed clustering after 4 are EXCLUDE-listed
(§3.1; ledger F5). **[ADMIT]** We built only what earned its place on the gate and reverted families
that did not (§5.3); the many unbuilt reference fields are candidate future work, each gated the same
way — coverage is not a goal in itself. We state coverage as this reproducible mapping rather than a
single "N of 89" headline the column list does not reproduce.

**The cancel-burst family is an inter-cancel-interval proxy.** True order→cancel latency exists as a
dormant `latency_ms` field but regressed the gate when swapped in, so we kept the proxy (Row 7). **[ADMIT]**
Revisiting true latency on a richer corpus is future work, gated the same way.

**The holiday calendar is stubbed.** `main.py` carries a `TODO(holiday-calendar)` seam; the
nightly "yesterday" auto-resolution is not exchange-holiday-aware. **[ADMIT]** Every scored run this
competition passes an explicit `--date`, so **no submitted result is affected** — but a fully
autonomous nightly deploy would need a real SSE/SZSE calendar. (The seam is wired; only the calendar
table is a stub, per §7 / readiness G4.)

## 8.3 Future work

In priority order, gated by the same offline discipline: (1) the **B-board** compounding run under
mandatory daily submission, where a deterministic pipeline and this methodology trail are the
differentiation (§6.3); (2) a real exchange-holiday calendar to close the §8.2 seam; (3) a trained
Task-2 head **only** once a truth set large enough to verify its lift exists — until then, rules stay.
None of these is pursued by tuning to the board. **[CLAIM]**
