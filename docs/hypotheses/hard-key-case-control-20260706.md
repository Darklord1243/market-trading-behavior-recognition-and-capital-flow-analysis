# Hard-key collapse — offline-signature case/control study (2026-07-06)

**Status:** COMPLETE · **ACCEPTED** (human-confirmed 2026-07-06) — no offline signature exists.
**Type:** read-only analysis, no submit, no production-code change.
**Branch:** feat/phase6-parquet-submit · **HEAD:** f6f3097
**Script:** `scratchpad/hardkey_signature_study.py` (session 7ea3e4a9)
**Compliance:** LIS §3.3 — board numbers used for verification only; no threshold tuning.
**Related:** [[p0626-triage-closed-h5]], [[p0629-board-h5-hard-key]], `score-boost-direction-20260704.md` (§score anatomy), `competitive-gap-audit-20260703-fable5.md` (row 1: hard-key channel).

---

## Question

Board-collapse days (0626 → **0.3265**, 0629 → **0.3333**) score ~0.33 while good-key days
reach ~0.52–0.56, with reportedly *identical* offline Task-2 numbers. Does the collapse have
**any offline-measurable signature** — something we could see BEFORE submitting — so that the
hard-key channel could be given a pre-submit offline gate (per the final-week posture: aggressive
goal, disciplined execution)? If a signature exists it becomes a candidate gate; if none exists the
channel is genuinely blind and stays closed.

## Design

Case/control over 5 days with known board scores. Parquet: `data/202606` (June), `data/202607`
(July). For each day, rebuilt the **production** feature matrix
(`src.pipeline_parquet.build_feature_matrix_for_panel` → `src.cluster.build_clustering_matrix`,
31-col Euclidean space) and measured ~12 offline dimensions across three candidate layers:

- **(A) Market regime [INPUT]** — index daily return + breadth (from `指数/` parquet).
- **(B) Label-distribution shift [OUTPUT]** — capital_type / capital_intention / pattern_type
  distributions + entropies (from the committed `outputs/<day>/*.csv`).
- **(C) Cluster geometry** — Euclidean silhouette of the `pattern_type` partition (the board-aligned
  Task-1 proxy per H1); feature-space dispersion.

## Result — per-day table (sorted by board score)

| day | board | sil_pat | n_pat | pat_top_share | 游资 | 量化 | 散户 | cap_entropy | 卖出 | 买入 | T0 | idx_ret | **idx breadth-up** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0626 | **0.3265** ⬇ | 0.098 | 4 | 0.43 | 0.42 | 0.30 | 0.28 | 1.561 | 0.21 | 0.16 | 0.63 | −2.7% | **0.02 (broad DOWN)** |
| 0629 | **0.3333** ⬇ | 0.038 | 4 | 0.64 | 0.42 | 0.28 | 0.30 | 1.561 | 0.03 | 0.31 | 0.66 | +1.2% | **0.83 (broad UP)** |
| 0625 | 0.4558 | 0.129 | 4 | 0.61 | 0.41 | 0.31 | 0.28 | 1.565 | 0.10 | 0.26 | 0.64 | +0.7% | 0.69 |
| 0701 | 0.5245 | 0.082 | 3 | 0.47 | 0.48 | 0.22 | 0.30 | 1.510 | 0.03 | 0.38 | 0.59 | +0.6% | 0.63 |
| 0702 | 0.5566 | 0.135 | 4 | 0.52 | 0.41 | 0.30 | 0.29 | 1.564 | 0.10 | 0.20 | 0.70 | −2.2% | 0.18 (broad down) |
| 0703 | **0.4160** ⬇ | — | 6 | — | 0.39 | 0.28 | 0.33 | 1.572 | 0.10 | 0.29 | 0.61 | — | — |

> **Row 6 addendum (added 2026-07-07).** 0703 board = **0.4160**, scored 2026-07-06 17:00 on the
> `20260703` slot. Distribution columns are measured directly from the shipped pack
> `outputs/20260703/submit.zip` (100 stocks); `sil_pat`/`pat_top_share`/`idx_*` were **not** re-run
> through `hardkey_signature_study.py` (that script's n=5 table was frozen before 0703 scored). 0703
> is a **new confirming data point**: it lands *between* the 0.33 collapse band and the ~0.52–0.56
> good band — a mediocre-key day — while its capital distribution (散户0.33/游资0.39/量化0.28,
> entropy 1.572) sits dead-center among the good days, exactly the "no offline signature" pattern.
> The pack used the **euclidean floor** (`TASK1_METHOD=euclidean`), the same method as the 0.5566
> winner (identical `ap active buy pct` / `oss small amount pct` / `oss mega count pct` cluster
> lexicon, 6 non-degenerate clusters) — **not** a method flip or degeneracy.

## Verdict — no offline signature separates the collapse days

**Decisive fact: the two collapse days are market-regime OPPOSITES.** 0626 was a broad *down* day
(index breadth-up 0.02, ret −2.7%); 0629 was a broad *up* day (breadth 0.83, ret +1.2%). Both
collapsed. Meanwhile the best good day (0702, 0.5566) shares 0626's broad-down regime, and 0629's
broad-up regime matches the good days 0625/0701. **Market regime cannot flag both collapse days.**

On every other axis the collapse days sit in the *middle* of the good days, or are opposite each
other:
- **游资 share** both 0.42, vs good {0.41, 0.48, 0.41} — dead center.
- **capital entropy** both 1.561, vs good {1.565, 1.510, 1.564} — indistinguishable.
- **卖出 share** 0.21 (0626) vs 0.03 (0629) — opposite ends; good days span 0.03–0.10 between them.
- **silhouette** 0.098 (0626) *exceeds* good-day 0701 (0.082); 0629 is lowest (0.038) but 0626 is not —
  no both-low pattern. Confirms the [[p0626-triage-closed-h5]] finding that offline Task-1 quality is
  stable across good/bad days.

**There is no offline dimension on which both collapse days align and separate from the good days.**

### Discarded artifacts (transparency)
Two spurious high correlations were removed: (i) `uni_ret_*` breadth — the column auto-picker matched
`oss_mega_amount_pct` (contains "pct"), NOT a return; the 35-feature matrix has no raw daily-return
column. (ii) feature-space dispersion — varied only at the 4th decimal (~2.13), high |r| over
negligible spread at n=5.

### Open caveat
True per-stock universe-return breadth was *approximated* by index breadth (no raw-return column in
the matrix), not measured directly. Index breadth is regime-opposite across the two collapse days,
making it very unlikely a per-stock version would separate them. Human accepted the verdict without
closing this axis (2026-07-06). n=5 days.

### 0703 provenance — Fable-5 audit exonerated (added 2026-07-07)

A concern was raised that the 0703 → 0.4160 drop was *caused by the Fable-5 audit*. Three
independent facts exonerate the audit; the drop is a hard-key day, not a regression:

1. **Chronology.** The 0.4160 pack (`outputs/20260703/submit.zip`) was built `2026-07-06 00:01` and
   scored `2026-07-06 17:00`. The audit's only code commits — `b26bfed` (pyarrow decl + universe
   `fillna`) at `21:43` and `6f9fbfa` at `22:16` — landed **~21 h after** the pack was built and
   ~4 h after it was scored. A later commit cannot alter an already-scored artifact.
2. **Scope.** `b26bfed` touches only the parquet *gate-reproducibility* loader
   (`src/pipeline_parquet.load_universe_codes`) and `requirements.txt`; the submission generation
   path and Task-2 rules are untouched. Clean-checkout smoke (G3) was green.
3. **Pack health.** 0703 is the euclidean floor, 6 non-degenerate clusters, 100-stock non-degenerate
   3-class split — byte-consistent method with the 0.5566 winner. No DTW flip, no universe
   corruption.

Cross-slot note: 0.5566 / 0.5290 are the **0702** slot (euclidean vs dtw paired-A/B); 0.4160 is the
**0703** slot. Different data dates = different hidden keys — not a same-artifact regression.

## Implication

The hard-key collapse is driven by the **hidden answer key**, not by any property observable in our
inputs or outputs. Therefore:
1. **No offline gate can exist for this channel** → under the final-week posture it stays CLOSED;
   there is no disciplined bet here, and chasing it is the 0626/0629 burn.
2. The collapse is **not even predictable** — we cannot know in advance which days will collapse.
3. Collapse days **structurally cap the moving average**; ~2 of every ~5 days drag it down regardless
   of method. A 0.7 *average* on the A-board is likely unreachable this week unless the organizer's
   weighting is strongly recency-biased.

**Forward:** A-board remainder = attendance only (daily euclidean floor). The compounding prize is the
**B-board** (fresh average, mandatory daily, report ≈20%), where the deterministic pipeline + this
honest methodology trail are the differentiation story.
