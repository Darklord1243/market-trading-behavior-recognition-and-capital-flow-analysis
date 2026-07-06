# §6 — Results & Honest Ceiling

> **Draft status:** report-ready prose, Phase 2 (polished Phase 5). Executive-facing prose: the inline
> **[CLAIM]** / **[ADMIT]** verification tags used in the technical sections are **omitted here for
> readability** (see the §0 tag legend). Every figure is a frozen exhibit from §5, not a re-run, and
> maps to `docs/report/code-parity-ledger.md`.

This section states what we can defend, at what magnitude, and where the objective structurally caps
what any method can reach this week. Consistent with §5, we report a **frozen historical snapshot**
for the offline gate rather than a single live number, because the harness scores one parquet corpus
per invocation and the validation label set now spans two corpora.

## 6.1 Offline gate results (the instrument, not the board)

The capital-type proxy's **frozen ship gate is 0.6773 at n=77** (through-0624, `parquet:data/202606`,
labels commit `23a4498`, LIS v1.6.8), with 游资 the weakest class at ship time (F1 ≈ 0.59) — reported,
not papered over. The full validation set has since grown to 154 scorable rows across 11 days; on the
current CSV a corpus-split verify gives **June-corpus 0.6438 / n=122** and **July-corpus 0.7824 /
n=32**, with a combined n=154 gate not yet a single harness output. The intent gate floor is **0.6750
/ n=115** on a separate harness. These are proxy measurements — per §5.2 the proxy is a **smoke
detector, not a leaderboard simulator**, so we trust large regressions and discount sub-0.01 wins; no
result in this report rests on a third-decimal delta.

The engineering trail behind these numbers is auditable end to end: **234 passed, 2 xfailed** on the
test suite, a **35-column feature matrix** (24 matching the 89-field reference set by name/rename, 3
novel engineered, 31 feeding clustering — §3.1) chosen for discriminating power, and the full gate
progression (0.3371 → 0.6094 → 0.6599 → … → 0.6773) recorded in §5.2.

## 6.2 Board results and the collapse-day cap

On the live board the pipeline lands in a **good-day band of roughly 0.45–0.56** (0625 0.4558, 0701
0.5245, 0702 0.5566). The controlled paired experiment (§5.4) gives our sharpest board measurement —
the H1 discovery — at zero cost to the moving average, and confirmed the board is deterministic
(0.5245 reproduced exactly on re-upload).

Against that band sit two **collapse days**: 0626 at **0.3265** and 0629 at **0.3333**, with no scorer
change between them and the good days. The §5.5 case/control study establishes the decisive fact: the
two collapse days are **market-regime opposites** (0626 broad-down, 0629 broad-up) yet both collapse,
and on every other offline axis they sit in the middle of — or at opposite ends from — the good days.
**There is no offline dimension on which both collapse days align and separate from the good days**,
so the collapse is driven by the hidden answer key, not a pipeline defect, and it is **not predictable
in advance**.

The consequence is a **structural ceiling**: because the A-board is a moving weighted average and
roughly two of every five days collapse regardless of method, a **0.7 average is likely unreachable
this week** absent a strongly recency-weighted scoring rule. We state this rather than tune toward the
days we happened to win — an audited limit is more credible than a silently favorable average.

## 6.3 The compounding prize is the B-board

The honest reading of §5.5 reframes the target. The A-board average is capped by unobservable collapse
days we chose not to chase; the **B-board restarts the moving average under mandatory daily
submission**, resetting the collapse drag and rewarding consistency. There, the assets are exactly
what this report documents: a deterministic, LLM-free, reproducible pipeline; an offline gate trail
with a falsification record; and one clean experiment (H1) that corrected the field's natural
assumption about the Task-1 metric. The differentiation is the methodology and its honesty, not any
single-day peak — which is the argument the remaining sections make in detail.
