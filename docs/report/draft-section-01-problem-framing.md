# §1 — Problem Framing & Task Decomposition

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md`. Task weights and output contracts are from the competition
> spec (§5.3–5.4); the market-phase open question is carried per the Phase-2 handoff (§6.3 → §8).

The competition gives us intraday Level-2 order-flow and asks two coupled questions about the capital
behind it. We frame them explicitly because the framing determines the entire methodology.

## 1.1 Two tasks, two outputs, two graders

| Task | Output file | What it asks | Weight | How it is graded |
|---|---|---|---|---|
| **Task 1** | `pattern_reco.csv` | group each stock-day into a **trading-behavior pattern** | **0.4** | undisclosed separation/cohesion blend ("Wasserstein + DTW") |
| **Task 2** | `predict_result.csv` | predict **capital type** `{游资, 量化, 散户}` + **capital intention** | **0.6** | weighted-F1 vs a hidden **T+5** real-market backtest |

**[CLAIM]** The two tasks are coupled — the same feature matrix feeds both — but scored separately,
and Task 2's 0.6 weight makes capital-type/intention prediction the larger prize.

## 1.2 The defining property: a partially-observable objective

The methodological pivot of this whole project is that **neither grader is visible to us at build
time.** Task 2 is graded against a future (T+5) we never see; Task 1 is graded by a metric the spec
names only obliquely. The one number the platform returns — the instant score — is a blend of both,
after the fact, with no per-task or per-stock breakdown. **[CLAIM]** A team can therefore *watch* a
score move but cannot *learn why* from it, and tuning toward it is both uninformative and explicitly
disqualifying (spec §3.3 / §5.5 code audit).

This single fact forces the posture developed in the rest of the report: build **offline, compliant
instruments** (the Track-V proxy, §5.1) that certify a change before it ships, honor **pre-registered
gates** even when an idea is attractive (§5.3), and treat the board as an object of **controlled
experiment** (§5.4), never a gradient to descend. The differentiation we pursue is methodological
rigor under an adversarial objective, not a headline score.

## 1.3 Scope we concretely model — and one we do not

The spec defines two output CSVs with concrete fields; we model exactly those: the 3-class
`capital_type` and the `capital_intention` net-direction. **[CLAIM]** A third notion — 行情阶段
(market-phase) — appears in the scoring discussion but its scoring object was never disclosed to us,
and a direct organizer clarification we asked went **unanswered**. **[ADMIT]** We therefore do not
claim coverage of a market-phase component whose grading target the organizer never defined; this is
recorded honestly in **§8 Limitations** rather than papered over with a speculative feature. Framing
the boundary of what is scoreable is itself part of the methodology.
