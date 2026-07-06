# Report ↔ Code Parity Ledger

**Purpose.** The TOP-15 B-board audit disqualifies on any *code / doc / result mismatch*
(`topic-specifications-and-data.en.md` §5.5). Every load-bearing claim in the solution report must
trace to an exact module/function and a way to verify it. This ledger is the single source of that
traceability; it is maintained **in parallel with** the report draft so the narrative cannot drift
from the code.

**Status:** Phase 1 — seeded alongside the §5 (Evaluation) draft. Rows for sections not yet drafted
are pre-registered so later drafting fills prose, not facts.
**Branch:** `feat/phase6-parquet-submit` · **HEAD:** `b26bfed` (G1 `pyarrow` + P1 loader fix committed; parent `f6f3097`)
**Convention:** each claim is tagged **CLAIM** (defensible from evidence) or **ADMIT** (a limit we
state openly). Verification is a command, a test, a harness run, or a doc/commit anchor.

**Test-suite anchor (current):** `234 passed, 2 xfailed` — re-frozen 2026-07-06 on **pandas 3.0.3**
after the **P1 fix** (a pandas-3.0 `astype(str)` regression in `_load_universe_codes` had briefly made
it `233/1/2`; fixed via `fillna("")` + pin cap `pandas>=1.3,<3`, committed `b26bfed`). Use `234 passed,
2 xfailed` wherever a suite count appears; the 2 xfails are the dormant L-c true-latency tests. Do not
reuse the stale `222` / `169` figures from older docs.

**Standing gate commands** (offline proxy-F1; see row 15 for which command matches which exhibit):

```bash
# June label dates — current CSV, June corpus (skips July rows with warnings)
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606

# July label dates only — current CSV, July corpus
python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202607
```

The harness accepts **one parquet root per invocation**; it scores only label dates whose parquet
exists under that root. A combined n=154 gate requires both runs (or a merged prediction CSV) — there
is no single command that reproduces all label dates today.

---

## Ledger

| # | Report § | Claim | Tag | Module / function (or doc) | Commit / anchor | How to verify |
|---|---|---|---|---|---|---|
| 1 | §2.2, §7 | Pipeline is byte-deterministic and seed-fixed; `main.py` recomputes everything from raw L2 | CLAIM | `main.py`; `config.RANDOM_SEED=42` | LIS §3 (compliance #4) | Board: identical zip re-upload → identical `0.5245` (`p5.7-board-paired-ab-0701.md` §Determinism, 2026-07-04 23:17). Local: re-run `--pack`, diff the two CSVs → byte-identical |
| 2 | §2.2, §7 | No LLM in the inference path (LLMs used offline only, for features/report) | CLAIM | inference path (`main.py` → `label`/`rules`/`cluster`) | LIS §3 (compliance #4), §3.4 | `grep -ri "openai\|anthropic\|llm\|requests\|http" src/ main.py` on the inference modules → clean |
| 3 | §3.3 | Cross-sample within-day rank normalization is the load-bearing "label fix" that lets scoring generalize 1→100 | CLAIM | `src/normalize.py::normalize_matrix` (L33); wired in `src/label.weak_label_matrix` | Phase 1 `78bd5a9`; Phase 1b `18cca42` | `pytest tests/test_normalize.py tests/test_label.py` (red-first panel test discriminates when wiring reverted) |
| 4 | §3.4 | Normalization uses only the same-day cross-section — no look-ahead (compliance #1) | CLAIM | `src/normalize.py` (`EXCLUDE`, per-column rank over rows) | LIS §3 (compliance #1) | Read the diff: rank is over `matrix` rows (one day's panel), never across dates |
| 5 | §3.1–3.2 | **35-col matrix: 24 match the 89-field reference set by exact name/rename (≈30 w/ 6 family consolidations), 3 novel engineered, 2 internal flags; 31 cluster after 4 EXCLUDE (35−4=31)**; families chosen for discriminating power | CLAIM | `src/features.py`, `src/aggregate.build_feature_matrix` | Freeze F5 (2026-07-06); flag P2 RESOLVED | F5 mapping table: exact 35-col dump vs `reference-feature-set.md` |
| 6 | §3.2 | Feature-B slices moved the offline proxy-F1 measurably (0.3371 → 0.6094 → 0.6599 → 0.6449→ …) | CLAIM | `src/features.py` (`_trd_size_entropy`, `_limit_seal_features`), `src/rules.py` `DIMS_RETAIL` | B.0 `v1.5.9`; B.2 `94ccb90`; B.3 `497bbce` | Run standing gate command; compare to LIS §6 gate table |
| 7 | §3.2, §8 | CB fast-cancel is an **inter-cancel interval proxy**, not true order→cancel latency | ADMIT | `src/features._cb_features`; `ingest_parquet.read_cancel_frame_parquet` (`latency_ms` dormant) | L-c rejected `v1.6.1` | LIS `v1.6.1`: true-latency swap regressed 0.6599 → 0.6500 → kept proxy; `latency_ms` present but not consumed |
| 8 | §4.1 | Transparent 3-class rule scorer, not a GBDT, because GBDT lift is offline-unmeasurable (§3.3 trap) | CLAIM/ADMIT | `src/rules.py::score_capital_type` (L141); `src/model.py` = pass-through STUB | LIS §5 (H4 exec-rank 5); `competitive-gap-audit-20260703-fable5.md` §3–4 | Read `model.py` (`CapitalTypeHead.fit/predict` return weak labels unchanged); CLAIM=compliance, ADMIT=possible unverifiable lift forgone |
| 9 | §4.1 | Intent is a banded net-direction gate on **raw** rows (absolute thresholds) | CLAIM | `src/rules.py::get_intention` (L204); `_intent_confidence` | LIS §4 `label.py` row | Read diff: intent gate reads raw `matrix`, not `normalize_matrix` output |
| 10 | §4.3, §5.4 | **H1: board Task-1 metric ≈ Euclidean-feature-space silhouette, not DTW-space or naming** | CLAIM | `src/cluster.py::cluster_patterns` (L1177), `build_clustering_matrix`; verification via `build_feature_matrix_for_panel` | `score-boost-direction-20260704.md` §"H1 RESULT — SUPPORTED"; memory `h1-board-euclidean-space-confirmed` | Two paired board days: eucl 0.5245>0.5053 (0701), 0.5566>0.5290 (0702) — `p5.7-board-paired-ab-0701.md` changelog. Offline: euclidean-space silhouette reproduces board ranking; DTW/enriched space contradict it |
| 11 | §4.3, §5.4 | H1 is n=2 days and the positive direction is partly tautological; the strength is the two falsifications | ADMIT | — | `score-boost-direction-20260704.md` §"Two honest caveats" | Read the two caveats: eucl labels are argmax-silhouette on that very matrix; board-NOT-DTW and board-NOT-enriched are the load-bearing evidence |
| 12 | §4.2, §4.3 | Task-1 clustering **method** is a ±0.02 lever (near-maxed); no method swap reaches 0.5→0.7 | CLAIM | `src/cluster.py` `_sweep_k` (argmax-silhouette K∈(6,12)) | `score-boost-direction-20260704.md` §"Forward implication"; memory `score-boost-over-method-choice` | Board Δ total 0.0192 with Task-2 byte-identical; euclidean-KMeans already near-maximizes the board-aligned silhouette |
| 13 | §5.1 | Offline weighted-F1 proxy scores our output vs public post-market truth (龙虎榜) — never the board's answers | CLAIM | `src/validate.py::weighted_f1` (L33); `scripts/validate_offline.py`; `tests/fixtures/validation_labels.csv` | V.1–V.2 `719ebaa`; V.4 harness `737ed5a` | `pytest tests/test_validate.py::test_weighted_f1_matches_sklearn`; run standing gate command |
| 14 | §5.1 | Validation labels never enter a feature or the inference path (compliance #1/#3) | CLAIM | `scripts/validate_offline.py` (offline-only; not imported by `main.py`) | LIS §4 `validate.py` row, §6 Track V | `grep -r "validate_offline\|validation_labels" main.py src/` → clean (harness is standalone) |
| 15 | §5.2 | Capital proxy gates (see **Row 15 detail** below): frozen ship gate **0.6773/n=77**; 游资 weakest at ship time | CLAIM | `scripts/validate_offline.py`; `src/validate.py::weighted_f1` | LIS `v1.6.8` §6 gate table | Reproduce frozen gate per Row 15 detail; do **not** expect 0.6773 from the June-only command on the expanded label CSV |
| 16 | §5.2 | Proxy is a **smoke detector, not a leaderboard simulator** (tiny, class-imbalanced, 龙虎榜 over-represents 游资) | ADMIT | — | LIS §6 "Honest limits" | Read Track V honest-limits list; trust large regressions, discount small wins |
| 17 | §5.3 | Six pre-registered hypotheses were falsified and *not* shipped (or shipped default-OFF) | CLAIM | see §5.3 exhibit rows below | six hypothesis docs (`docs/hypotheses/`) | Each doc records a pre-registered gate + the falsifying measurement; git shows reverted/uncommitted state |
| 18 | §5.4 | Scoring determinism confirmed: identical zip → identical instant score | CLAIM | board record | `p5.7-board-paired-ab-0701.md` §"Scoring determinism — CONFIRMED" | Changelog: 2026-07-02 and 2026-07-04 23:17 same zip → 0.5245 both times |
| 19 | §5.4 | Best-not-latest: each A-board day keeps the BEST upload → a paired A/B costs 0 on the average | CLAIM | scoring mechanics | spec §5.1 (moving weighted average); memory `aboard-moving-weighted-average` | `topic-specifications-and-data.en.md` §5.1; daily slot keeps max |
| 20 | §5.5 | Hard-key collapse days (0626/0629 ~0.33) have **no offline signature** → hidden answer key, not a pipeline defect | ADMIT | read-only study | `hard-key-case-control-20260706.md`; memory `hardkey-no-offline-signature` | 5-day case/control table: collapse days are regime-opposites; no dimension separates them from good days |
| 21 | §5.5, §6 | Collapse days structurally cap the A-board moving average; 0.7 *average* likely unreachable this week | ADMIT | — | `hard-key-case-control-20260706.md` §Implication; `competitive-gap-audit` §5 | Read ceiling arithmetic; ~2 of ~5 days drag regardless of method |
| 22 | §7 | 3-class output validator fails loudly on bad labels (`量化机构` rejected; `散户`/bare `量化` required) | CLAIM | `src/postprocess.py::validate_predict` | LIS §2 locks | `pytest tests/test_postprocess.py tests/test_config.py` |
| 23 | §7 | No hard-coding: thresholds are global constants, no per-stock rules, no random fill | CLAIM | `src/config.py`, `src/rules.py` | LIS §3 (compliance #2) | `grep` `rules.py` for stock codes → none; thresholds live in `config.py` |
| 24 | §7 | Test suite: **234 passed, 2 xfailed** (green under pandas 3.0.3 after P1 fix) | CLAIM | `tests/` | Freeze F4 (2026-07-06, post-P1) | `pytest tests/ -q` → `234 passed, 2 xfailed` in 120s (P1 fix committed `b26bfed`; see flag P1 RESOLVED) |

---

## Row 15 detail — capital proxy gates (frozen vs current)

§5.2 cites gate history in prose; this block pins **exact exhibits** so the report cannot drift.

### A. Frozen ship gate (historical exhibit — cite in report)

| Field | Value |
|---|---|
| **weighted_f1** | **0.6773** |
| **n** | **77** (stock, day) pairs |
| **游资 F1** | ≈ **0.59** (weakest class at ship time) |
| **When set** | LIS **v1.6.8** (2026-06-25), labels commit **`23a4498`** (+20260624 addendum) |
| **Corpus** | `parquet:data/202606` only |
| **Code since** | No `rules.py` / scorer change authorized by that gate |

**How to verify (frozen snapshot):** check out labels at commit `23a4498` (or filter
`validation_labels.csv` to `transaction_date ≤ 20260624`, 77 scorable rows) and run:

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```

Expected: **weighted_f1 = 0.6773**, **n = 77**, 游资 F1 ≈ 0.59. This is the number in §5.2 gate
progression table row “+20260624 addenda → **0.6773**”.

### B. Current label CSV — corpus-split verify (2026-07-06, Cursor)

Full `validation_labels.csv` has **154 scorable rows / 11 days** (0616–0702). One root cannot
score all dates. Observed on HEAD **`f6f3097`**, no code change:

| Slice | Command | **n** | **weighted_f1** | Notes |
|---|---|---:|---:|---|
| June label dates | `--input parquet:data/202606` (full CSV) | **122** | **0.6438** | July rows skipped (no 0701/0702 under `data/202606`); matches through-0629 **frozen floor** in gap audits |
| July label dates | `--input parquet:data/202607` (full CSV) | **32** | **0.7824** | June rows skipped (no June parquet under `data/202607`) |
| **Combined 154** | — | — | — | **Not one harness output yet** — merge both slices or add multi-root support before report lock |

**Report wording:** §5.2 gate **progression table** uses historical snapshots (including 0.6773/n=77).
§5.2 “active gate” language must not imply a single live number unless the combined n=154 run is
frozen and pasted here.

### C. Intent gate (separate harness — not row 15, same exhibit family)

Intent floor **0.6750 / n=115** lives in `scripts/validate_intent_offline.py` (capital-only harness
above). Freeze beside row 15 before report lock if §5.2 cites it.

---

## §5.3 falsified-slices exhibit (sub-ledger)

Each row is one falsified hypothesis, its pre-registered gate, the falsifying result, and the code
disposition. This is the evidence spine of the "falsification discipline" differentiator.

| Slice | Hypothesis | Pre-registered gate | Falsifying result | Disposition | Doc |
|---|---|---|---|---|---|
| Slice 2 | OFI + ap_run_max + OBP spread + PI herfindahl/vwap wired into `DIMS_YOUZI` | beat cap 0.6438 | run-max wiring regressed cap 0.6438 → 0.6356 | fully reverted | `p3-feature-batch-ofi-obp-pi.md` |
| Slice 3 | Panel-quantile (rank-relative) intention gate | beat P2-intent subset 0.6271 & 卖出 F1 0.48 | regressed to best 0.6077 / 0.46 across full grid | reverted, not committed | `p2-intent-c-rank-relative.md` |
| Slice 4 | Clustering on precomputed DTW distance (avg linkage) | beat euclidean silhouette non-degenerately | degenerates to giant-cluster + singletons every day | kept default-off `--method dtw-precomputed` harness | `p5-task1-dtw-precomputed.md` |
| Slice 5B | 游资 relative-dominance guard (`YOUZI_WIN_MARGIN`) | hold through-0624 floor 0.6773 | max 0.6747 at any margin (floor blocks it) | no code written (probe-first) | `p4-youzi-guard-tightening.md` |
| Slice 6 | Balance-first constrained Euclidean K-sweep | beat legacy K-selection | constrained ≡ legacy K all 9 days (no-op) | harness `--ksweep constrained` default-off | `p5-task1-constrained-ksweep.md` |
| P5 (metric-align) | DTW/Wasserstein trajectory-enrichment + composite-K | improve silhouette | regressed silhouette | not shipped (commit `5570b07` reverted mechanism) | `p5-task1-metric-alignment.md` |

**Companion (engineering-confirmed, board-falsified):** P5.7 DTW-complete lifts offline DTW-sil to
+0.29..+0.47 across 11 days (first CONFIRMED Task-1 mechanism, commit `f6f3097`) but **lost** both
paired board days → shipped **default-OFF**; euclidean stays the scored-day floor. Engineering
success ≠ board default. (`p5.7-board-paired-ab-0701.md`; memory `p5.7-dtw-complete-confirmed`.)

---

## Open parity flags (audit-blocking if unresolved)

**P1 — pandas-3.0 `astype(str)` regression — RESOLVED 2026-07-06 (fix committed `b26bfed`).** On
pandas 3.0.3, `Series.astype(str)` keeps `NaN` as a float instead of `"nan"`, so the empty-cell filter
in `_load_universe_codes` leaked a float into `sorted()` → `TypeError`; it failed
`test_load_universe_codes_strips_empty_and_deduplicates` and would crash a real run given any universe
file with a blank/NaN code cell. **Fix (both, per human decision):** (a) `src/pipeline_parquet.py:67`
now `df[col].fillna("").astype(str).str.strip()` — robust under pandas 3.x; (b) `requirements.txt` pin
capped `pandas>=1.3,<3`. Verified: `234 passed, 2 xfailed` (freeze F4). Production entry was never
affected (G3 smoke green). **Both edits are committed as `b26bfed`** (G1 `pyarrow` + P1 loader fix).

**P2 — "34 of 89 features" did not reproduce — RESOLVED 2026-07-06 (doc-side; no code change).** The
emitted feature matrix is **35 columns**: **24** match the 89-field reference set by exact name or
rename (≈**30** with six reference-family consolidations), **3** are novel engineered columns
(`trd_size_entropy`, `limit_seal_up_ratio`, `limit_seal_down_ratio`), and **2** are internal flags
(`cb_available`, `n_ticks`); **31** feed clustering after four EXCLUDE-listed columns (35 − 4 = 31,
consistent with H1). No literal count equalled 34, so the "34 of 89" headline was **retired**. The
author-confirmed reproducible wording (above) now appears in **§3.1**, **§8.2**, and **Row 5**; the
width facts are frozen at **F5**. The matrix itself was always correct — this was a report-accuracy fix.

Prior status: the only Phase-1 doc-drift was the stale test count (`222`/`169` in older hypothesis
docs); older hypothesis docs are historical records and are **not** edited (they were correct when
written).

Rows 5, 15, 24 assert numbers reproducible only by running commands (feature count, gate, suite).
Row **15** is split: frozen **0.6773/n=77** (§A) vs corpus-split current verify (§B, frozen
2026-07-06). Before report lock: (1) confirm §A via labels-at-`23a4498` or date filter; (2) run
combined n=154 gate or document merge; (3) paste pytest + intent harness beside row 24 / §C.

---

## Frozen exhibits at report lock

**Purpose.** §5.5 disqualifies on any code/doc/result mismatch, so every number the report *prints*
must be reproducible on demand from a **timestamped command output pasted here**. The blocks below are
the freeze slots. Until a block shows a pasted result + date + HEAD, the report cites that number as a
frozen historical snapshot but the exhibit is **NOT YET RE-FROZEN this cycle**. Fill top-to-bottom
before report lock; each is one foreground command (economical shell, no subagents).

Precondition (all blocks): `export PYTHONUTF8=1 PYTHONIOENCODING=utf-8`. If invoking via `conda run`,
add `--no-capture-output` (GBK box buffers/crashes child stdout on non-ASCII). The parquet path needs
`pyarrow`, which **is now declared in `requirements.txt`** (G1 resolved 2026-07-06) — a clean
`init_env.sh` install is sufficient; no extra `pip install` step.

**HEAD note:** all F-blocks were executed 2026-07-06 on the working tree now committed as **`b26bfed`**
(G1 `pyarrow` + P1 loader fix, parent `f6f3097`). G1/P1 are **result-neutral** for the gate/intent/
feature freezes (F1–F3, F5); F4 was re-run after the P1 fix. Every F-block below cites `b26bfed`.

### F1 — Frozen ship gate (§A): labels ≤ 20260624 → expect 0.6773 / n=77

```bash
# filter validation_labels.csv to transaction_date <= 20260624 (77 scorable rows), OR checkout labels @ 23a4498
python scripts/validate_offline.py --labels <filtered-or-23a4498> --input parquet:data/202606
```

| Field | Expected | Pasted result | Date / HEAD |
|---|---|---|---|
| weighted_f1 | 0.6773 | **0.6773** ✅ | 2026-07-06 · b26bfed |
| n | 77 | **77** ✅ | 2026-07-06 · b26bfed |
| 游资 F1 | ≈ 0.59 | **0.59** (P=0.56 R=0.62, sup=24) ✅ | 2026-07-06 · b26bfed |

**Method used:** filtered current `validation_labels.csv` to `transaction_date ≤ 20260624` (77 rows,
via scratchpad temp file — original not edited) → `--input parquet:data/202606`. Full per-class:
游资 F1=0.59 / 量化 F1=0.73 / 散户 F1=0.71. Reproduces the frozen ship gate exactly.

### F2 — Combined n=154 gate (currently NOT one harness output — pick an option and record it)

The harness scores one parquet root per run, so n=154 has no single command today. Choose and freeze:

- **Option A (two-run merge):** run `--input parquet:data/202606` (June, expect 0.6438/n=122) and
  `--input parquet:data/202607` (July, expect 0.7824/n=32); paste both, and report the two slices
  explicitly (do **not** average them into a fake single number).
- **Option B (precomputed merged CSV):** emit predictions for all 11 days into one CSV and score once;
  paste the single weighted_f1/n. Requires a small merge harness (not yet written).

| Slice | Command | Expected | Pasted | Date / HEAD |
|---|---|---|---|---|
| June | `--input parquet:data/202606` | 0.6438 / n=122 | **0.6438 / n=122** ✅ (游资 0.59 / 量化 0.66 / 散户 0.69) | 2026-07-06 · b26bfed |
| July | `--input parquet:data/202607` | 0.7824 / n=32 | **0.7824 / n=32** ✅ (游资 0.78 / 量化 0.83 / 散户 0.71) | 2026-07-06 · b26bfed |
| Combined | **Option A (two-run merge), no combined F1** | — | Report the two slices explicitly; do NOT average | 2026-07-06 · b26bfed |

### F3 — Intent gate floor: expect 0.6750 / n=115

```bash
python scripts/validate_intent_offline.py --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```

| Field | Expected | Pasted | Date / HEAD |
|---|---|---|---|
| intent weighted_f1 | 0.6750 | **0.6750** ✅ | 2026-07-06 · b26bfed |
| n | 115 | **115** ✅ (买入 F1=0.736 sup=59 / 卖出 F1=0.480 sup=12) | 2026-07-06 · b26bfed |

### F4 — Test suite: expect 234 passed, 2 xfailed

```bash
pytest tests/ -q
```

| Field | Expected | Pasted (after P1 fix) | Date / HEAD |
|---|---|---|---|
| passed | 234 | **234** ✅ | 2026-07-06 · b26bfed |
| failed | 0 | **0** ✅ | 2026-07-06 · b26bfed |
| xfailed | 2 (dormant L-c latency tests) | **2** ✅ | 2026-07-06 · b26bfed |

> **F4 history — found-failing, fixed, re-froze green.** First freeze (pre-fix, 176.9s) was
> **`1 failed, 233 passed, 2 xfailed`**: `test_load_universe_codes_strips_empty_and_deduplicates`
> crashed because env **pandas 3.0.3** stopped stringifying `NaN`→`"nan"`, so a blank universe cell
> leaked a float into `sorted()` in `_load_universe_codes` (`TypeError: float < str`). **P1 fix
> applied** (Open parity flag P1, RESOLVED): `df[col].fillna("").astype(str)` in
> `src/pipeline_parquet.py:67` + pin cap `pandas>=1.3,<3` in `requirements.txt` (both **committed
> `b26bfed`**). Re-run: **`234 passed, 2 xfailed`** in 120.0s. The competition claim is restored and
> now holds under pandas 3.x. Production entry was never affected (G3 smoke green throughout).

### F5 — Feature count (Row 5): column-list vs `reference-feature-set.md` (frozen 2026-07-06)

**Method:** `ingest.load_raw('samples/AFAC2026.xlsx')` → `aggregate.build_feature_matrix` → dump
`matrix.columns`. Emitted width **35** (matches G3 smoke "1 (stock, day) rows x 35 features"). Diffed
each column against the 89-field `reference-feature-set.md`.

**The literal diff does not reproduce a clean "34 of 89" — retired and reconciled (P2 LOCKED, author
decision 2026-07-06).** The 35 emitted columns classify as:

| Class | Count | Columns |
|---|---:|---|
| **REF — exact reference-name match** | 21 | `oss_mega_amount_pct`, `oss_mega_count_pct`, `oss_large_amount_pct`, `oss_large_count_pct`, `oss_small_amount_pct`, `oss_small_count_pct`, `ap_active_buy_pct`, `ap_active_sell_pct`, `ap_active_net_direction`, `ap_unilateral_intensity`, `pi_open_30min_amount_pct`, `pi_close_10min_amount_pct`, `pi_price_std_pct`, `rs_interval_cv`, `rs_burst_ratio`, `rs_split_similarity`, `cb_cancel_order_ratio`, `cb_cancel_volume_ratio`, `cb_fast_cancel_ratio`, `cb_buy_cancel_ratio`, `cb_sell_cancel_ratio` |
| **REF~ — renamed 1:1 to a reference field** | 3 | `oss_mid_amount_pct`→`oss_medium_amount_pct`, `oss_mid_count_pct`→`oss_medium_count_pct`, `pd_max_price_impact_pct`→ref `pi_max_price_impact_pct` |
| **REF-fam — consolidation of a reference family** | 6 | `pi_time_concentration` (pi_herfindahl/peak), `book_imbalance` (pd_Q1 imbalance), `obp_imbalance_mean`, `obp_spread`, `obp_big_quote_share` (obp_* family), `bigorder_volume_pct` (oss big-order family) |
| **NEW — novel engineered, NOT in the 89** | 3 | `trd_size_entropy` (B.2), `limit_seal_up_ratio`, `limit_seal_down_ratio` (B.3) |
| **INT — internal non-feature / EXCLUDE-listed** | 2 | `cb_available` (bool flag), `n_ticks` (raw count) |

**Reconciliation of the counts (the important part):**

- **Reference coverage** = REF (21) + REF~ (3) = **24 exact/renamed**, or **30** if the 6 REF-fam
  consolidations count. Neither is **34**. The "34 of 89" figure (Row 5) does **not** reproduce as a
  literal name-diff.
- **35 vs 34 vs 31:** the "+1 pass-through" note in §3 was imprecise — there are **2** internal
  non-features (`cb_available`, `n_ticks`), and the clustering matrix drops **4** EXCLUDE-listed
  columns (`n_ticks`, `cb_available`, `limit_seal_up_ratio`, `limit_seal_down_ratio`), giving
  35 − 4 = **31** = the Euclidean clustering-matrix width in Row 10. That identity checks out cleanly.
- **Defensible statement for §3.1 / Row 5:** "The pipeline emits a **35-column** feature matrix;
  **~24 columns map exactly (or by rename) to the 89-field reference set**, ~6 more consolidate
  reference families, **3 are novel engineered features** (trade-size entropy, limit-seal ratios), and
  2 are internal flags; **31 columns feed the clustering matrix** after 4 are EXCLUDE-listed." The bare
  "34 of 89" claim should be **retired or restated** to one of these reproducible forms.

| Field | Prior claim | Frozen finding | Date / HEAD |
|---|---|---|---|
| panel matrix width | 35 cols | **35** ✅ | 2026-07-06 · b26bfed |
| clustering matrix width | 31 cols | **31** ✅ (35 − 4 EXCLUDE) | 2026-07-06 · b26bfed |
| reference coverage | "34 of 89" (retired) | **24 reference by name/rename** (≈30 incl. family) + 3 novel + 2 flags ✅ | 2026-07-06 · b26bfed |

> **F5 disposition (P2 RESOLVED 2026-07-06):** the width facts (35 / 31) are frozen and exact. The
> adopted, author-confirmed coverage statement is: *"35-column matrix; **24** fields match the 89-field
> reference set by exact name or rename (≈**30** if the six family consolidations are counted); **3**
> novel engineered columns (`trd_size_entropy`, `limit_seal_up_ratio`, `limit_seal_down_ratio`); **2**
> internal flags (`cb_available`, `n_ticks`); **31** columns feed Task-1 clustering after four
> EXCLUDE-listed columns (35 − 4 = 31, consistent with H1)."* The unreproducible "34 of 89" is retired.
> §3.1, §8.2, and Row 5 now carry this wording. Read-only finding; no code touched.
