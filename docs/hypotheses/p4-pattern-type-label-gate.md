# P4 — Task-1 offline observability: clustering-quality gate (+ pattern rationality proxy)

**Status:** read-only hypothesis / spec. **No code, config, label, threshold, or submit change.**
**Date:** 2026-06-28 · **Branch:** feat/phase6-parquet-submit · **Spec:** docs/LIS.md v1.6.8.
**Parent:** `docs/hypotheses/p0626-score-collapse-triage.md` (Update U2). **Compliance:** LIS §3.3.
Related: [[normalize-exclude-leak-clustering]], [[proxy-gate-scores-capital-type-only]].

> **Filename note:** kept as requested (`p4-pattern-type-label-gate.md`), but the proposed
> primary gate is a **clustering-quality gate**, not a label/F1 gate — see §1 for why.

---

## 0. The gap this closes

**Task 1 is 40% of the board score and we have NO offline measurement of it today** beyond
two metrics printed to a log and never gated. That is the live blind spot behind the 0626
triage (capital_type + intention both held/improved on the OOS proxy; only Task 1 went
unmeasured). This doc specifies how to *measure* Task 1 offline, the right way.

## 1. How Task 1 is ACTUALLY scored (corrects the "pattern-F1" premise)

Per **LIS §1**:

| Task | Weight | Scored by |
|---|---|---|
| **Task 1** — pattern clustering (`pattern_reco.csv`) | **0.4** | **silhouette + CH + Wasserstein + DTW** (separation + cohesion) |

And **LIS §2 locked fact:** `pattern_type` is **open vocabulary — scored on
rationality/interpretability, NOT string match.**

**Consequence — two corrections to the parent doc's first draft:**
1. **There is no hidden pattern_type answer key to match against.** Seeding pattern_type
   "ground-truth" labels and computing a **pattern-F1 would measure something the board does
   not score.** A string-match F1 is the wrong objective for Task 1.
2. **Task 1 is therefore NOT a total blind spot.** Its scoring *components*
   (silhouette/CH/Wasserstein/DTW) are **deterministic functions of the data + our own
   clustering** — computable offline, **no labels, zero §3.3 risk.** We simply never gated them.

So the board-aligned offline gate for Task 1 is a **clustering-quality gate**, and label
seeding (the original ask) is demoted to a **secondary rationality/interpretability sanity
check** (§4), not the primary metric.

## 2. What we can compute today vs what is blocked

| Metric | In code? | Offline-computable now? | Blocker |
|---|---|---|---|
| **silhouette** | ✅ `src/cluster.py:187` (sklearn) | **yes** — already logged per run | none |
| **Calinski-Harabasz (CH)** | ✅ `src/cluster.py:188` | **yes** — already logged | none |
| **Wasserstein** | ❌ absent | no | **LIS open-Q #2**: what object does it score? |
| **DTW** | ❌ explicitly deferred (`cluster.py:10`, Task-5 note) | no | **LIS open-Q #2** + needs TimeSeriesKMeans/tslearn |

**LIS § openQ #2 (unresolved):** *"What object does Wasserstein/DTW score in Task 1 — per-day
static feature vectors, or intraday time-series?"* → re-read brief Rev. 7 §Task-1 metric; if
ambiguous, **ask organizer**. This must be resolved before Wasserstein/DTW can be implemented
faithfully — guessing the input object risks building a gate that disagrees with the board
(and tuning to a wrong offline metric is its own trap).

**Already observed this session (0626 re-run log):** best **K=6, silhouette=0.1453, CH=16.4.**
silhouette 0.1453 is **low** (weak separation). The immediate, cheap, label-free test is to
compute the same for **0625** and compare (§5).

## 3. Primary gate spec — `validate_pattern_offline.py` (spec only, NOT implemented)

Mirror the Track-V harness *discipline* (offline, never imports into `main.py`/`src/`, never
reads platform answers), but score **cluster quality**, not label agreement.

**Inputs**
- `pattern_reco.csv` for the day(s) under test (cluster → `pattern_type` assignment per stock).
- The **normalized feature matrix** the clustering ran on, **recomputed from `parquet:data/202606`**
  (same path `main.py` uses; honors the [[normalize-exclude-leak-clustering]] EXCLUDE set so
  `n_ticks`/`cb_available`/`limit_*` never re-enter the metric inputs).

**Outputs (per day)**
- `silhouette` and `CH` on the recomputed matrix + emitted cluster labels (re-derive, don't
  trust the log) — sanity-check they reproduce the run.
- `n_clusters`, per-cluster sizes, degeneracy flags (any cluster <2; any label ≥ X% of universe).
- **Wasserstein / DTW: stubbed `NotImplemented`** until open-Q #2 is resolved — the script must
  *fail loud / skip-with-message*, never silently emit a partial "Task-1 score."

**Metric contract (proposed)**
- Report the **individual** components, not a single blended number, until the board's exact
  blend (weights across the 4 metrics) is known. A fabricated blend invites tuning to a wrong
  target (§3.3-adjacent). Components only; human reads the table.
- Exit codes mirror `validate_offline.py` (0 = ran, including legitimate skip; 1 = malformed).

**Compliance:** identical to `validate_offline.py` header — offline/post-hoc, no board feedback,
no answer files. Quality metrics use only our data + our clustering → inherently §3.3-safe.

## 4. Secondary — pattern *rationality* proxy (the label-seeding ask, scoped correctly)

Because `pattern_type` is open-vocab/rationality-scored, "labels" here are **not** a key to
match. They are a **human sanity check on whether our cluster→label→explanation mapping is
defensible** — i.e. does `游资强势拉升` actually describe a cluster whose feature centroid looks
like hot-money strength?

**Critical: LHB seats do NOT map 1:1 to `pattern_type`.**
- An LHB 游资 seat tells you *who* traded (capital_type evidence), **not** *which microstructure
  pattern* the day exhibited. A stock can hit the 龙虎榜 on institutional/index-rebalance flow
  (→ `机构长线配置`), or a 游资 name can produce a distribution-day shape (`卖压主动出货`).
- So the capital_type labels in `validation_labels.csv` **cannot be reused** as pattern truth.

**How a human would seed a pattern rationality sample (compliant):**
1. Pick N held stock-days (incl. 0625 + 0626 overlap).
2. From **public post-market sources only** (LIS §3.3 / §5.1): 龙虎榜 seat composition, public
   news, AND the **human-readable L2 narrative** we can already render (intraday price/volume,
   open-auction, active-buy/sell ratio, mega-order prints, seal behavior).
   **NEVER** the platform's backtest answers or instant-score (auto-DQ).
3. Human writes a one-line *pattern narrative* per stock-day ("late-session active-buy ramp on
   mega prints → strength" / "steady institutional accumulation, no extremes").
4. Compare narrative vs our emitted `pattern_type` + `pattern_explanation` → score **mapping
   plausibility** (e.g. % agree / 3-point rubric), NOT string F1.

**Is `pattern_explanation` scored?** LIS §1 attributes Task-1 scoring to the four cluster
metrics; §2 says `pattern_type` is judged on *rationality/interpretability*. `pattern_explanation`
is the natural carrier of that interpretability, but **the brief does not explicitly confirm it
is independently scored.** → **Open item: re-read brief Rev. 7 §Task-1; if ambiguous, ask
organizer.** Until confirmed, treat `pattern_explanation` as interpretability support, not a
scored field, and keep every row's explanation defensible (current pipeline already does).

## 5. Acceptance test for H2 (Task-1 regression vs H5 hard-key)

Label-free, runnable as soon as §3's sil/CH path exists (or even now from re-run logs):

1. Recompute **silhouette + CH** for **0625** and **0626** on the recomputed normalized matrix.
2. Compare:
   - **0626 materially worse than 0625** (e.g. silhouette and CH both drop) → **H2 confirmed**:
     Task-1 clustering quality regressed on 0626 → plausibly drove the −0.13 board move.
   - **0625 ≈ 0626 (both low)** → **H5**: Task-1 was not the differentiator; the 0626 *key*
     (or universe-Task2 we can't see) is the driver; no Task-1 bug to fix.
3. **Decision is by the offline metric delta, never by the 0.3265 board point** (§3.3).
   If H2 confirms, the fix slice targets clustering inputs/K-selection (e.g. revisit the
   EXCLUDE set / feature set / K-sweep), gated on silhouette/CH improvement **without**
   regressing the frozen Task-2 gates.

**Caveat:** sil/CH alone are 2 of 4 board components; a clean sil/CH comparison is *suggestive*,
not conclusive, until Wasserstein/DTW (open-Q #2) are resolved. State this in any conclusion.

## 6. Recommended next slice (needs human go — ONE of)
- **6a (cheap, immediate, label-free):** compute silhouette + CH for 0625 vs 0626 (re-run 0625
  clustering to a scratch dir, read metrics) → runs the §5 acceptance test for H2 *today*, no new
  code, no labels. **Recommended first** — highest information per cost.
- **6b (structural):** resolve LIS open-Q #2 (brief/organizer), then spec+build
  `validate_pattern_offline.py` as a standing Task-1 gate.
- **6c (secondary):** seed the §4 rationality sample for interpretability QA.

## 7. Compliance
Read-only spec. No tuning to 0.3265. No P2-intent-b revert. No board-driven thresholds. No submit
regen. All proposed measurements use our data + our clustering or public post-market info only —
never the platform's answers/score (LIS §3.3).
