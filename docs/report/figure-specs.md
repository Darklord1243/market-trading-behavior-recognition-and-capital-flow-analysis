# Figure Specs — report exhibits E5.1–E5.5

> **Status:** Phase 4a sketch. Titles, data-source files, and suggested chart type **only** — no
> rendering, no synthetic data. Every figure's numbers must come from the cited source table (which
> traces to the parity ledger), so a figure can never assert a value the prose/ledger does not.
> Derived from the §5 draft's "Exhibit index" (`draft-section-05-evaluation.md`). Additional exhibits
> for §1/§2/§4/§6 can be added later; §5 is the evidence spine, so its five are specced first.

| ID | Title | Data source (authoritative) | Chart type | Notes for the renderer |
|---|---|---|---|---|
| **E5.1** | Track-V gate progression: proxy-F1 vs label-set size | `draft-section-05-evaluation.md` §5.2 gate table; numbers ← ledger Row 6 + freeze F1/F2 | **Line chart** (x = label-set n: 10→24→39→53→65→77…; y = weighted-F1) | Mark the **0.6773 / n=77 frozen ship gate**; annotate that later dips are OOS label expansion, not regression. Trust-direction, not third decimal. |
| **E5.2** | Six pre-registered slices, falsified | `draft-section-05-evaluation.md` §5.3 table = ledger "§5.3 falsified-slices sub-ledger" | **Keep as table** (do not chart) | The table *is* the argument; columns: slice · idea · pre-registered gate · falsifying result · disposition. |
| **E5.3** | Paired board A/B: euclidean vs dtw-complete, 2 days | `draft-section-05-evaluation.md` §5.4 first table; ← ledger Row 10 / Row 18; `p5.7-board-paired-ab-0701.md` | **Grouped bar chart** (2 groups: 0701, 0702; 2 bars each: euclidean, dtw-complete; y = instant score) | Euclidean bars win both days (0.5245>0.5053, 0.5566>0.5290). Caption the determinism control (0.5245 reproduced on re-upload). |
| **E5.4** | Board rewards Euclidean geometry, not DTW (H1 falsification) | `draft-section-05-evaluation.md` §5.4 second table; ← memory `h1-board-euclidean-space-confirmed`; `score-boost-direction-20260704.md` | **Grouped bar or 3×2 heat-table** (3 feature spaces × {eucl, dtw} silhouette; ✓/✗ "matches board") | Highlight the single row where the board ranking reproduces (Euclidean finance matrix); the two contradicting spaces (DTW, enriched) are the load-bearing falsifications. |
| **E5.5** | Hard-key case/control: collapse days have no offline signature | `draft-section-05-evaluation.md` §5.5 table; ← ledger Row 20/21; `hard-key-case-control-20260706.md` | **Annotated table** (rows = 5 days; cols = board · sil · 游资 share · cap entropy · 卖出 share · breadth) | Highlight the **regime-opposite** fact: 0626 broad-down and 0629 broad-up both collapse; no column separates both collapse days from the good days. |

## Rendering rules (when these are built)

- **Data provenance:** pull every value from the cited source table; never re-derive or round beyond
  what the ledger shows. If a figure would need a number not in a source table, add a ledger row first.
- **Honesty markers:** E5.1 must visually distinguish the frozen ship gate from live corpus-split
  verifies (do not imply one continuous live line through n=154). E5.3/E5.4 are **n=2 days** — caption
  the small-sample caveat (ledger Row 11).
- **Theme/format:** follow the `dataviz` skill for palette/accessibility at render time; these specs
  are format-only and commit to no visual system yet.
