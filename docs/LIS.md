# LIS — Living Implementation Spec · AFAC2026 Track 1

> **What this is:** the single document an execution agent (Sonnet) reads to implement one phase
> without re-reading the whole repo. High-reasoning lead maintains it; execution agents follow it.
> **Read order for an executor:** this file → the one `src/` file your phase names → its test file.
> Do **not** re-read the whole doc tree. Everything load-bearing is summarized or cited here.

| | |
|---|---|
| **Version** | **v1.5.5** (2026-06-18) |
| **Pipeline entry** | `python main.py --input <xlsx|glob> -o outputs/ [--date YYYYMMDD]` |
| **Tests** | `pytest tests/` → **101 passing** (verified 2026-06-18; 37 pre-Track-L → 67 Track-L-a → 74 Phase-1 → 79 Track-V → 86 Phase-1b → 93 Track-L-b → 101 Phase-2) |
| **Branch at authoring** | `feat/task2-3class-capital-type` |
| **Canonical source of truth** | brief `docs/AFAC2026_Track1_Project_Brief.docx` (Rev. 7) + `docs/competition-spec/` |

### Changelog
- **v1.5.5 (2026-06-18)** — **Phase 2 landed** (commit `f932504`): fixed the RS resolution bug in
  `features._rs_features`. Interval computation is now **dtype-portable** —
  `group["datetime_utc"].diff().dropna().dt.total_seconds() * 1000` replaces the
  `astype("int64") // 1_000_000` form that assumed ns and over-divided on `datetime64[ms]`
  (pandas 3.0.x) → `cv≈13.48` / `burst≈0.99`. `rs_burst_ratio` is now an **absolute** `< RS_BURST_THRESHOLD_MS`
  (100ms, new `config.py` constant), not the scale-free `< 0.25·mean` that saturated when mean≈0; added
  `rs_split_similarity = max(0, 1 - cv)`. Fixture (603997.SH, n=1) **before→after: cv 13.48 → 1.3444,
  burst 0.99 → 0.0** (matches LIS expectation); matrix width **31 → 32** (`+rs_split_similarity`). RS tests
  **parametrized over `datetime64[ms]` AND `datetime64[ns]`** with explicit `.astype(dtype)` — a **genuine
  regression guard**: the `[ms]` arm yields cv=0 under the old formula (the original synthetic groups were
  `[ns]`, where the bug is silent — lead caught this and re-dispatched). Suite **93 → 101 green**; xlsx smoke
  valid, `cb_available=False`. **This does NOT change the n=1 fixture label** (still 散户-class on real
  multi-row; the all-0.5 tie emits 游资) — the fix makes the *feature* correct and gives H1 clean ranks; the
  *label* fix is H1/Phase 1b. **§7-R1 resolved.** §4 `features.py` row + RS dtype table updated.
- **v1.5.4 (2026-06-18)** — **Track L-b landed** (commit `87a60a8`): real CB feature math in
  `features._cb_features` true branch — all 5 `CB_KEYS` (`cb_cancel_order_ratio`, `cb_cancel_volume_ratio`,
  `cb_fast_cancel_ratio`, `cb_buy_cancel_ratio`, `cb_sell_cancel_ratio`) computed from the reconstructed cancel
  frame, finite floats in [0,1]. Plumbed via a `cancel_lookup` dict `((stock_code, date) → cancel_df)` threaded
  `build_feature_matrix → compute_daily_features → _cb_features`; xlsx path passes `None` → backward-compatible
  (absent path still zeros + `cb_available=0.0`). New `CB_FAST_CANCEL_MS=500` in `config.py`. 7 new tests
  (red-first 6-fail→pass, hand-computed values, absent/empty guards, finite/[0,1], real-fixture via
  `read_cancel_frame` on `local_l2_tiny`). Suite **86 → 93 green**; xlsx n=1 smoke `cb_available=False`,
  `load_raw` untouched. **Honest limit (tracked):** `cb_fast_cancel_ratio` is an **inter-cancel interval proxy**
  (consecutive `cancel_time` diffs `< CB_FAST_CANCEL_MS`), **not** true order→cancel latency — the latter needs
  `read_cancel_frame` extended to carry order-ref columns (SZ `叫买/卖序号`, SH `交易所委托号`). Deferred to
  **Track L-c** (see §6 Track L note); correctly scoped out of L-b. §4 `ingest_local.py` row + tick-cancel
  inventory updated. **Phase 2** (RS dtype fix) is next.
- **v1.5.3 (2026-06-18)** — **Phase 1b landed** (commit `18cca42`): wired `normalize_matrix` into
  `src/label.weak_label_matrix` — capital scoring now runs on rank-normalized rows; the intent gate
  (`get_intention` / `_intent_confidence`) keeps reading **raw** rows (absolute thresholds). New
  `tests/test_label.py` (7 tests). The panel test is a **genuine red-first discriminator**: planted rows use
  realistic out-of-[0,1] raw values (e.g. `rs_interval_cv=15.0`, `oss_mega_amount_pct=12.0`) so `clip01`
  saturates raw scoring (row 1 → 游资, wrong) while rank-norm separates (row 1 → 量化, right) — the test
  fails if the wiring is reverted. Lead caught a first non-discriminating panel and re-dispatched before gating.
  Suite **79 → 86 green**; xlsx n=1 smoke still valid (emits 游资 via the all-0.5 tie). §4 `normalize.py` / `label.py`
  rows updated. **Track L-b** (real CB math) is next, then **Phase 2** (RS dtype fix).
- **v1.5.2 (2026-06-18)** — **Track V V.1–V.2 landed** (commit `719ebaa`): `src/validate.py::weighted_f1` — pure
  **offline** proxy scorer. Inner-joins pred/truth on `(stock_code, transaction_date)`, returns support-weighted F1 +
  per-class P/R/F1/support; empty join → `0.0`/`n=0`. Hand-rolled (no sklearn in module; the V.1 test pins it to
  `sklearn.metrics.f1_score(average="weighted")`). **Not wired into `main.py`/inference** (verified by grep). 5 tests
  (inline DataFrames, never loads the EXAMPLE `validation_labels.csv`); suite **74 → 79 green**. **V.3** (human label
  seeding) + **V.4** (offline harness) remain before phases can report a real proxy-F1 delta. §4 module table updated.
- **v1.5.1 (2026-06-18)** — **Phase 1 landed** (commit `78bd5a9`): `src/normalize.py::normalize_matrix` — cross-sample
  within-day rank normalization to [0,1] (`rank(method="average")` → `(r-1)/(n-1)`; excludes `cb_available`/`n_ticks`;
  n≤1→0.5; constant col→0.5; index/columns/non-numeric preserved). The **H1 seam**. 7 contract-faithful tests; suite
  **67 → 74 green**. **Pure & unwired** — Phase 1b (wire into `src/label.weak_label_matrix`) still pending; `label.py`
  still scores on the raw matrix. §4 module table + §8 seam note updated.
- **v1.5 (2026-06-18)** — **Track L-a landed** (commit `65116b6`): `src/ingest_local.py` — local GBK-CSV L2
  ingest adapter. Reads per-stock `行情`/`逐笔委托`/`逐笔成交` (gb18030, Chinese headers, explicit 10-level book)
  into the cleaned frame shape `_normalise_and_clean` produces, across multi-stock days; reconstructs embedded
  cancels per exchange (SZ `成交代码=='C'` / SH `委托类型=='D'`) and plumbs `cb_available=1.0`. `load_raw` (xlsx
  path) untouched. 30 new tests + tiny committed GBK fixture (SZ+SH × 3 streams); suite **37 → 67 green**. Real-data
  smoke: 10 stocks → `(39541, 33)`, all `cb_available=1.0`. **Scope: L-a only** — `features._cb_features`'s `True`
  branch still returns **zero** CB values (structural flag wired, values stub); real CB math is **Track L-b**, slotted
  **after Phase 1b, before Phase 2**. §4 module table + data-inventory tick-cancel row updated.
- **v1.4.1 (2026-06-16)** — Doc consistency: Track V honest-limits note now reflects OQ-1 resolved (was "only the
  organizer can"); §3 CB invariant spells out the dual path (xlsx/snapshot → NEUTRAL vs local CSV/Track-L →
  reconstruct cancels). Docs-only; suite 37 green.
- **v1.4 (2026-06-16)** — **OQ-1 closed + local data changes the picture.** (1) **OQ-1 RESOLVED:** the organizer
  confirmed eval truth is **3-class `{游资,量化,散户}`** with `散户` scoring in weighted F1 → R2 downgraded from
  🚩 BLOCKING to ✅ resolved; the "settle before Phase 3" gate is lifted; **no code change** (§2/`config` were
  already 3-class). (2) **Inspected the local corpus** (`scripts/inspect_local_l2.py` →
  `docs/data_inventory_report.md`): **~7,574 stocks × 2 days**, `行情`/`逐笔委托`/`逐笔成交` per stock, **cancels
  embedded per-exchange** (SZ `成交代码=='C'` ~22%, SH `委托类型=='D'` ~24%). This **overturns the v1.3 §4/R3
  "tick-cancel ⛔ missing" premise** — every ⛔ stream is on disk; **CB needs no purchase**. §4 inventory, R3, and
  Track D updated. (3) **Added Track L** (local L2 ingest adapter) — the parallel track that unblocks real-data
  H1/Phase 2/3/CB/Track-V (the corpus is GBK per-stock CSVs with Chinese headers, not the xlsx/JSON `load_raw`
  reads). (4) **Added two human guides** (`docs/human_guides/`) for Track-V label-seeding and Track-D data-sourcing,
  plus a `tests/fixtures/validation_labels.csv` template. Docs + one read-only script; **no `src/` change; suite
  still 37 green**.
- **v1.3 (2026-06-16)** — **Competitive-gap upgrade (strategy, not machinery).** A peer review found the spec
  optimizes *producing* labels but under-invests in whether they match the hidden T+5 truth (weighted F1, 0.6
  weight). Accepted with refinements — **docs-only, no `src/` change, suite still 37 green**; §4 stub claims
  re-verified against `cluster.py`/`model.py`/`rules.py`:
  (1) Added **Track V** (§6) — an *offline* validation harness scoring pipeline output against a small hand-labeled
  truth proxy from **public post-market sources** (龙虎榜 hot-money seats, news). Compliant under §3.3 (your labels,
  never the board's) and §5.1 (post-market info for *retrospective validation* only; never in the inference path).
  Every H1–H3 acceptance now also reports a **proxy-F1 delta**, not only synthetic-panel responsiveness.
  (2) **Promoted R2 (2-class vs 3-class) to 🚩 BLOCKING OQ-1** (§7) with an organizer re-confirm question + a
  per-answer decision tree — *without* reverting the 3-class lock (still level-1 organizer precedence; reversal
  needs new organizer evidence).
  (3) **Re-ranked H5 (Task-1 clustering) above H4 (GBDT)** on **certainty-adjusted ROI** (§5): Task-1's metric is
  offline-computable with zero §3.3 risk → *bankable*; H4 trains on un-validatable pseudo-labels and carries the
  answer-feedback trap. **H1 stays #1** (it gates clustering's normalized inputs too — H-numbers are stable IDs,
  not ranks).
  (4) **Elevated data procurement to tracked Track D** (§6) with a §4 data-inventory table — CB (the named strongest
  游资/量化 separator) is structurally zero without sourced tick-cancel L2, a ceiling cap no feature batch fixes.
  Rejected nothing outright; the review's single "Phase 0" became two *parallel tracks* (V, D) to avoid disturbing
  the executable Phase 1→6 spine.
- **v1.2 (2026-06-16)** — Surgical §4 correction after a 2nd review + independent re-measurement. The RS
  fault is **resolution-*dependent*, not universally "the" current state**: which score triple is live
  depends on the installed pandas (`requirements.txt` floors `pandas>=1.3`, **no upper pin**). Measured here
  on **pandas 3.0.3**: natural `datetime_utc` is `datetime64[ms]`, so the `//1_000_000` over-division **is
  active** → cv=13.48/burst=0.99 → scores `[0.398,0.418,0.457]`. On `datetime64[ns]` builds (pandas 2.2.x,
  the review's env) the code is accidentally correct → cv≈1.34/burst≈0 → scores `[0.398,0.219,0.655]`.
  **Both → 散户.** §4 now shows both as a dtype-keyed table; R1/Phase 2 reworded to "resolution-dependent"
  (note: *active*, not merely latent, on this repo's pandas 3.0.3). Corrects v1.1's "pandas 2.x always
  `[ms]`" overstatement **and** the review's "ns is observed here" (this install is `[ms]`). Docs-only; H1
  stays the first Sonnet task; suite 37 green.
- **v1.1 (2026-06-15)** — Verification pass on a review's flagged issues (A–E). **Found the true root cause**
  of the weak Task-2 output: a latent **`datetime64[ms]` resolution bug** in `features._rs_features`
  (`astype("int64") // 1_000_000` assumes ns, but pandas-2.x `to_datetime(unit="ms")` returns ms), collapsing
  30 s tick gaps to ≈0 → `rs_interval_cv`→13.48, `rs_burst_ratio`→0.99. v1.0's "lunch-gap" mechanism (H2/R1)
  was **wrong — corrected**. Confirmed v1.0's current-state scores `[0.398,0.418,0.457]→散户` are accurate
  (reproduced exactly); the review's `[0.398,0.219,0.655]` is the **bug-fixed** state (also 散户, *more*
  strongly) — proving **H1 (normalization), not H2, is the label fix**. Established the **n=1 fixture cannot
  validate the scorer**. Fixed `rules.py` docstring (D), added `build_notes.md` supersession (C), trimmed a
  memory link (E). No code *behavior* changed; suite still 37 green.
- **v1.0 (2026-06-15)** — Initial spec. Repo discovery, empirical state verification (tests + smoke run),
  feature-gap analysis (31/89), competitive thesis, 6-phase roadmap. Surfaced: Stage-1 scorer is
  near-random on real un-normalized features (defaults to 散户 on the fixture); `build_notes.md` is
  stale (2-class). See **Decision log** and **Risks**.

---

## 1. Purpose & how to use this

The competition is two coupled tasks per `(stock, trading-day)`:

| Task | Weight | Output file | Scored by |
|---|---|---|---|
| **Task 1** — trading-pattern clustering | **0.4** | `pattern_reco.csv` | silhouette + CH + **Wasserstein + DTW** (separation + cohesion) |
| **Task 2** — capital type + intent | **0.6** | `predict_result.csv` | **weighted F1** vs T+5 real-market backtest |

`Total = 0.4·Task1 + 0.6·Task2`. **Task 2 dominates and is currently our weakest link** (§5, §7-R1). Validate
every Task-2 change against the **Track V** offline proxy (§6), not only synthetic panels.

**For executors:** each phase below lists exact files, bite-sized tasks, and acceptance criteria.
Implement test-first (repo is TDD; see `tests/`). Never tune anything against the nightly instant
score — that is a compliance auto-DQ (§3.3). If reality contradicts this spec, **flag it in your PR and
update this file's changelog**, don't silently diverge.

---

## 2. Locked facts (do NOT contradict without new organizer evidence)

| Field | Allowed values (emit these exact bytes) |
|---|---|
| `capital_type` | `游资`, `量化`, `散户` — **3 classes**. Bare `量化`, **never** `量化机构`. |
| `capital_intention` | `买入`, `卖出`, `T0交易` |
| `pattern_type` | **Open vocabulary** — scored on rationality/interpretability, not string match |
| `transaction_date` | `YYYYMMDD` = **yesterday's trading day** at upload |
| Output | **UTF-8-sig** (BOM), exactly **4 columns** fixed order, **no nulls / no blank cells**, `submit.zip` with both CSVs at **root (no nested folders)** |

**Provenance & precedence (when sources conflict, higher wins):**
1. Direct organizer answer (DingTalk) / latest clarification
2. Brief Rev. 7
3. `docs/competition-spec/`
4. `docs/official_guidance/` (baseline guide labels are **stale** — see below)
5. Tutorial examples (illustrative only)

> **The 3-class set is a level-1 organizer override.** The baseline guide, `competition-spec`
> (`topic-specifications-and-data.*` §II/§5.4), the 89-field reference set, and the sample CSVs all say
> **2 classes `{游资, 量化机构}`**. A direct DingTalk answer corrected this to **3 classes `{游资, 量化, 散户}`**
> with **bare `量化`**, and made `散户` a real modelled class. This is encoded in `config.py`,
> `src/postprocess.py` (validator rejects `量化机构`, accepts `散户`/bare `量化`), and the brief Rev. 7.
> `docs/reference/official_baseline_main.py` is **algorithm reference only** — its 2-class
> `{游资, 量化机构}` labels are the bug, not the truth.

Code anchors for the locks: `config.CAPITAL_TYPES`, `config.INTENTION_CLASSES`,
`config.FORBIDDEN_CAPITAL_TYPES`, `src/postprocess.validate_predict`. Tests: `tests/test_config.py`,
`tests/test_postprocess.py`.

---

## 3. Compliance (auto-DQ — these are hard constraints, encode them, never relax)

| # | Rule | How it binds your code |
|---|---|---|
| 1 | **Intraday-only** | No look-ahead / post-close / future data in any feature or rule. Cross-sample normalization must use only the **same day's cross-section** (other stocks that day), never future days. |
| 2 | **No hard-coding** | No per-stock-code label tables, no random fill, no ignoring L2 features. Rules/thresholds are **global constants**, never per-stock. |
| 3 | **No answer-feedback tuning** | The nightly instant score is **verification only**. Never tune thresholds/weights/models on published backtest answers. Threshold search (if any) optimizes on **internal** metrics (silhouette / cross-validation), never leaderboard F1. |
| 4 | **Reproducible** | `main.py` recomputes everything from raw L2, fixed seed (`config.RANDOM_SEED=42`), relative paths, auditable. **No LLM call in the inference path** (LLMs allowed offline for feature ideas / report drafting only). |
| 5 | **Private repo** | No public sharing during competition. (Operational note: git network ops may require the team's proxy/sandbox config — not an executor concern.) |

**Engineering invariants (verified in code — keep them true):**
- Cumulative fields (`volume`/`amount`/`transactions`/`bigordervolume`) → `.diff().fillna(0).clip(lower=0)` **after** temporal sort. (`src/ingest._normalise_and_clean`)
- Session windows via **Beijing `hh`** (8–16), never UTC `date.dt.hour`. `ingest` derives `hour`/`minute` from a Beijing-localized clock and cross-checks against official `hh`. Close window `[14:50,15:00]` is **inclusive of 15:00** (closing-auction prints). (`src/features._pi_features`, `tests/test_features.py::test_pi_windows_use_beijing_clock_and_include_1500_close`)
- `bids`/`asks` are **10-level nested JSON** — parse them. (`src/ingest.parse_book_json`)
- **CB (cancel) features:** On the **xlsx/snapshot path** (`load_raw` + official fixture) there is no cancel table → degrade to zero + `cb_available=0.0`; CB dims vote **NEUTRAL** (never tilt a class). On the **local CSV path** (Track L) reconstruct embedded cancels (SZ `成交代码=='C'`, SH `委托类型=='D'`) → `cb_available=True` and wire `features._cb_features`. (`src/features._cb_features`, `src/rules._class_score`)

---

## 4. Current state — honest snapshot (verified by running it, 2026-06-15)

**Pipeline runs end-to-end, emits two valid CSVs, 37 tests green.** It is an **audit-compliant skeleton
with near-random Task-2 output on real features.**

| Module | State | Notes |
|---|---|---|
| `src/ingest.py` | ✅ real | 65-col read, Beijing clock, cumulative→tick diff, cancel-table detector, book-JSON parser |
| `src/ingest_local.py` | ✅ real (**L-a**) | Track L: local GBK-CSV adapter — multi-stock `行情`/`委托`/`成交`, Beijing time direct from `时间`, explicit book→JSON, per-exchange cancel reconstruction, `cb_available=1.0` plumbed. CB **values now real** via `features._cb_features` (Track L-b, `87a60a8`); `read_cancel_frame` still returns `side`/`cancel_time`/`cancel_qty` (order-ref columns not yet carried → fast-cancel is an inter-cancel proxy, Track L-c). `load_raw` untouched. |
| `src/features.py` | 🟡 **32 of 89 features**; RS family **dtype-portable (Phase 2, `f932504`)** | See gap table below. `_rs_features` now uses `.diff().dt.total_seconds()*1000` (dtype-safe across `[ms]`/`[ns]`); `rs_burst_ratio` = share `< RS_BURST_THRESHOLD_MS` (100ms, absolute); `+rs_split_similarity`. Fixture cv 13.48→1.34, burst 0.99→0. **§7-R1 resolved.** Scope: RS only (PI uses `hour`/`minute`, untouched). |
| `src/aggregate.py` | ✅ real (thin) | groups → daily matrix. `compute_window_features` is an unused seam. |
| `src/normalize.py` | ✅ real (**Phase 1**), **wired (Phase 1b)** | H1 seam: cross-sample within-day rank→[0,1] (`(r-1)/(n-1)`; excludes `cb_available`/`n_ticks`; n≤1 / constant→0.5). Now **called by `label.weak_label_matrix`** before capital scoring (commit `18cca42`). |
| `src/rules.py` | 🟡 real routing, **no cross-sample normalization** | 3-class scorer + 散户 guard + intent gate. Uses `clip01(raw)`, which **saturates** features outside [0,1] (even a *correct* `rs_interval_cv≈1.34` clips to 1.0) → see §7-R1. Class weights are **1.0 stubs**. (Docstring corrected in v1.1 — it had wrongly claimed "z-score/rank".) |
| `src/label.py` | ✅ real (thin), **normalize-wired (Phase 1b)** | weak labels + confidence (top1−top2 margin; intent gate clearance). Scores capital on `normalize_matrix(matrix)` rows; intent gate (`get_intention`/`_intent_confidence`) reads **raw** rows (absolute thresholds). Red-first panel test in `tests/test_label.py`. |
| `src/model.py` | ⛔ **STUB** (pass-through) | `CapitalTypeHead.fit/predict` return weak labels unchanged. Seam ready for LightGBM. |
| `src/cluster.py` | ⛔ **STUB-grade** | `DEFAULT_K=8` clamped, `min(k,n)`; 4 hard-coded pattern predicates; degrades to K=1 on fixture. No K-sweep, Euclidean only. |
| `src/postprocess.py` | ✅ real, hardened | 3-class validator, fails loudly. **Trustworthy compliance gate.** |
| `src/validate.py` | ✅ real (**Track V V.1–V.2**), **offline-only** | Offline proxy scorer `weighted_f1(pred, truth)` (inner-join on stock/day, support-weighted + per-class P/R/F1). **NOT in the inference path** (compliance #1/#3). Awaits V.3 (human labels) + V.4 (harness) to produce a real delta. |
| `main.py` | ✅ real | 5-stage orchestration, dynamic `--date`, holiday calendar is an **empty stub** (weekends only). |

**Raw-data inventory (updated v1.4 from local-corpus inspection — see `docs/data_inventory_report.md`):**

| L2 stream | Status | Unlocks | Note |
|---|---|---|---|
| 10-level snapshot | ✅ have | OBP, PI, OFI, partial OSS | `行情.csv` (66-col explicit book), **7,574 stk × 2 days** local; plus the n=1 `samples/AFAC2026.xlsx` |
| tick-trade | ✅ have | RS cadence, AP runs, TRD, OSS amount splits | `逐笔成交.csv` (~125k rows/stk) |
| tick-cancel | ✅ **values live (L-b, `87a60a8`)** | **CB family — strongest 游资/量化 separator** | Track-L adapter (`ingest_local.py`) reconstructs embedded cancels — SZ `逐笔成交.成交代码=='C'` (~22%), SH `逐笔委托.委托类型=='D'` (~24%) — `cb_available=1.0`. CB feature **values** now real (cancel/order + cancel/volume ratios, buy/sell cancel split, fast-cancel ratio). **Fast-cancel = inter-cancel interval proxy**, not true order→cancel latency; cancel-interval CV not in `CB_KEYS` — both await the order-ref join (**Track L-c**). |
| tick-order (order-level) | ✅ have | PD family (23 fields), iceberg `rs_split_*` | `逐笔委托.csv` (~139k rows/stk) |

> **Format caveat:** the local corpus is **per-stock GBK CSVs with Chinese headers + explicit 10-level columns**,
> **not** the xlsx/JSON-book schema `ingest.load_raw` reads → the **Track-L adapter** is required before any of the
> above is *usable*. The official `samples/AFAC2026.xlsx` (n=1) remains the only input the pipeline reads **today**.

**Smoke run on the official fixture** (`samples/AFAC2026.xlsx`, 1 stock `603997.SH`, 2026-05-07):
- Feature matrix: **1 × 31**. `cb_available=False` (snapshot-only). Clustering → **K=1** (expected on 1 sample).
- Task-2 → **散户 in both pandas regimes**, but the score triple is **resolution-dependent** (the RS
  computation's correctness depends on the `datetime_utc` dtype — §7-R1; `requirements.txt` floors
  `pandas>=1.3`, no upper pin):

  | `datetime_utc` dtype | e.g. pandas | RS `cv` / `burst` | scores `[游资,量化,散户]` | emits |
  |---|---|---|---|---|
  | `datetime64[ns]` | 2.2.x (review's env) | ≈1.34 / ≈0 | `[0.398, 0.219, 0.655]` | 散户 |
  | `datetime64[ms]` | **3.0.3 — this repo's current install** | ≈13.48 / ≈0.99 | `[0.398, 0.418, 0.457]` | 散户 |

  On `[ms]` builds the code's `astype("int64")//1_000_000` over-divides (assumes ns) → intervals collapse to
  ≈0. **Caveat: the fixture is n=1, so neither row validates the scorer** (raw → 散户 in both; rank-normalized
  → an arbitrary all-0.5 tie → 游资). The Phase 1b multi-stock synthetic panel is the proof.

  > **✅ RESOLVED by Phase 2 (`f932504`, 2026-06-18).** The table above is the **pre-fix** historical record.
  > `_rs_features` is now dtype-portable (`.diff().dt.total_seconds()*1000`), so **both** dtype builds now produce
  > `cv≈1.34 / burst≈0` — the `[ms]` row's `13.48 / 0.99` no longer occurs. The label stays 散户-class (the fix
  > corrects the *feature*, not the n=1 label — that's H1/Phase 1b). RS tests now parametrize `[ms]`+`[ns]` to
  > guard against regression.
- Task-1 names the cluster **游资强势连板拉升** — i.e. the two heads **disagree** on the one sample.
  Acceptable for a skeleton (independent heads, 1 sample), but a symptom of R1.

**Feature gap vs the 89-field reference (`docs/competition-spec/reference-feature-set.md`):**

| Family | Have | Ref | Missing (high-value) |
|---|---|---|---|
| OSS (order size) | 8 | 12 | `oss_hot_money_count_pct`, `oss_buy/sell_amount_pct`, `oss_mega_buy_pct` |
| RS (rhythm/seq) | 2 | 8 | `rs_interval_mean/median_ms`, `rs_buy/sell_interval_cv`, **`rs_split_similarity`**, **`rs_split_run_ratio`** (iceberg) |
| CB (cancel) | 6 (all 0) | 8 | needs tick-cancel table — strongest 游资/量化 discriminator, **unavailable on snapshot** |
| AP (active part.) | 4 | 8 | **`ap_active_buy/sell_run_max`**, `ap_dominant_direction`, `ap_active_volume_pct` |
| OBP (book profile) | 3+`book_imbalance` | 8 | best-bid/ask ratios, near-best, cross-spread, avg offset, **OFI** (tutorial Path 1) |
| PD (price discovery) | 1 | **23** | biggest absolute gap; many need order-level data — cherry-pick snapshot-computable ones |
| PI (period intraday) | 4 | 8 | **`pi_herfindahl_5/30min`**, `pi_vwap_deviation`, `pi_peak_amount_ratio`, `pi_max_price_impact_pct` |
| (extras) | `bigorder_volume_pct`, `n_ticks` | — | TRD family (baseline's 8th, ~6 dims) not yet built |

---

## 5. Strategy & ranked hypotheses (the competitive thesis)

**Thesis:** Task 2 is 60% of the score and is *currently the weakest part of the pipeline* (near-random
on real features). The fastest path up the leaderboard is **making the features and scoring actually
discriminate on a 100-stock cross-section** — not adding a model on top of broken inputs. A GBDT trained
on broken pseudo-labels cannot exceed broken pseudo-labels. So the order is: **fix inputs → fix scoring →
expand features → then model → then clustering.**

Ranked by ROI ÷ risk (H1 highest):

| # | Hypothesis | Why it moves score | Audit risk | Depends on |
|---|---|---|---|---|
| **H1** | **Cross-sample normalization** (rank/quantile → [0,1] across the day's stock panel) before scoring & clustering | `clip01(raw)` saturates real features (even a *correct* `rs_interval_cv≈1.34` clips to 1.0) → scores collapse to noise → 散户-by-default. Normalization is the **prerequisite** that makes rules, GBDT, and clustering generalize 1→100 — and it is **the label fix**: fixing RS alone does *not* fix the label (R1). Single biggest unlock. | **None** (same-day cross-section only) | — |
| **H2** | **Fix the confirmed RS resolution bug** — replace `astype("int64")//1_000_000` (assumes ns) with resolution-robust `.diff().dt.total_seconds()*1000` (the official baseline form); make burst an absolute `<100ms` test; add `rs_split_similarity`, `rs_buy/sell_interval_cv` | RS is THE 游资(manual)/量化(machine)/散户(no-cadence) discriminator. Current `cv=13.48`/`burst=0.99` are **bug artifacts** (ms-dtype over-division collapses intervals to ≈0), not signal — and they corrupt the cross-sectional ranks H1 feeds on. **A confirmed bug, not a hypothetical.** | **None** | feeds clean rs_* into H1 |
| **H3** | **Expand features toward 89**, prioritizing snapshot-computable separators: **OFI**, AP run-max, OBP best-level/spread dynamics, PI herfindahl/VWAP-dev, OSS active-buy split | More separable axes → higher F1 and cleaner clusters. OFI is a well-established microstructure signal (tutorial Path 1). | **Low** (all intraday) | H1 (to be usable) |
| **H4** | **Stage-3 GBDT head** (LightGBM, confidence-weighted pseudo-labels, calibrated probs) | Learns nonlinear interactions the equal-weight rule can't; smooths rules. | **Medium** — must train on **pseudo-labels only**, never leaderboard answers (§3.3) | **H1–H3** (garbage-in guard) |
| **H5** | **Metric-aligned Task-1 clustering**: bounded-K sweep over `K_RANGE=(6,12)` by silhouette/CH; evaluate **TimeSeriesKMeans (DTW)** / GMM / HDBSCAN; finance-grounded Chinese cluster names + explanations | Eval uses **Wasserstein+DTW**; Euclidean KMeans is metric-misaligned. Naming is cheap and scored on interpretability. | **Low** | H1 (shared normalization) |
| **H6** | **1→100 generalization layer**: market-cap/sector neutralization, cross-stock pattern consistency, robust (rank) features | Train fixture = 1 stock; leaderboard = 100. This is the central failure mode, not a feature. | **Low** | woven through H1, H3, H5 |

**Certainty-adjusted execution order (v1.3).** ROI÷risk above ranks *expected* gain; it ignores whether we can
*measure* the gain compliantly before the board sees it. Folding in **score-signal certainty** re-orders
*execution* — **H5 rises above H4** (the H-numbers stay fixed identifiers, not ranks):

| H | Gain measurable offline? | How | Audit risk | Exec rank |
|---|---|---|---|---|
| H1 | partial | Track V proxy-F1 + synthetic panel | none | **1** (also *gates* H3/H4/H5 inputs) |
| H2 | yes | unit test: `rs_*` on a real stock-day | none | **2** |
| H3 | yes | Track V proxy-F1 delta per batch | low | **3** |
| **H5** | **yes — fully** | **silhouette / CH / DTW on the matrix, no labels needed** | **none** | **4 ⟵ promoted above H4** |
| H4 | **no** | only the board scores a GBDT on pseudo-labels → §3.3 trap | medium | **5** |
| H6 | n/a | continuous discipline | low | woven through |

Why: Task-1 (0.4) is scored by **offline-computable** metrics, so H5's gain is *bankable with certainty and zero
audit risk*. H4's gain is **unmeasurable offline** (a GBDT on pseudo-labels can only be "validated" by the
leaderboard — the §3.3 trap) and is bounded above by pseudo-label quality (H1–H3). So clustering quality is the
safer points. **H1 stays #1**: it gates the normalized matrix that H3, H4 *and* H5 all consume — promoting H5 over
H4 does **not** demote the normalization prerequisite.

**Deliberately deferred / out-of-scope now:** LSTM/Transformer sequence models (Path 5 — needs many
stock-days we don't have), LLM fine-tuning (Path 6.5), heavy MLOps/K8s. LLM use is allowed **offline**
for feature brainstorming and the top-15 solution report — **never in the inference path** (§3.4).

**Quick wins vs long bets:** H1+H2 are quick, high-certainty wins (days). H3 is steady accretion. **H5 (Task-1)
is a bankable mid bet** (offline-scored, zero audit risk) and should precede **H4 (GBDT)**, whose payoff is real
but unmeasurable offline and bounded by pseudo-label quality. H6 is continuous discipline, not a milestone.

---

## 6. Phased roadmap (executable; each phase ends green + committed)

> Granularity rule: each task is one 2–5 min action; write the failing test first, watch it fail,
> implement minimally, watch it pass, commit. Phase 1 is fully specified (Sonnet can do it from this
> file + the named src file). Later phases are scoped; refine them here before executing.

### Track V — Offline validation & label-truth proxy  ⟵ **PARALLEL; redefines what "acceptance" means**

> **Human guide:** `docs/human_guides/track_v_validation_labels.md` (how to seed the labels, with sources).
>
> Runs alongside Phases 1–6, not before them. It does not gate *starting* a phase; it gates *believing* a phase
> helped. Synthetic panels prove the scorer **responds**; they cannot prove it **discriminates** vs the hidden T+5
> truth (you built the "clearly-游资" row, so of course it scores 游资). Track V adds a small, compliant, real proxy.

**Goal:** an *offline* weighted-F1 proxy of Task-2 output against a hand-labeled truth set drawn from **public
post-market sources**, so H1–H3 (and H5's cluster sanity) report a real-data delta, not only synthetic responsiveness.

**Compliant sources** (§5.1 permits post-market / non-real-time info for *retrospective validation*; §3.3 forbids
only the **board's answers**):
- **龙虎榜 (Dragon-Tiger List)** — publicly names 游资 **seats (营业部)** active on a stock-day → strong-ish **游资**
  positives. *Limit:* only covers 龙虎榜-triggering big movers; says little about **量化**/**散户**; seat-present ≠
  whole-day-dominant (noise).
- Public **quant/HFT-heavy / index-arb / market-maker** name lists → weak **量化** priors. *Limit:* indirect, noisy.
- Low-turnover, no-龙虎榜, retail-chatter names → weak **散户** priors. *Limit:* 散户 is the **least** publicly
  attributable class — expect the noisiest, sparsest labels here.
- Post-market news / broker notes ("main force active in X today").

**Forbidden (compliance):** assigning labels from — or tuning thresholds against — the platform instant score /
backtest answers (§3.3 auto-DQ). Validation labels are **post-market public info, never the board's**. They live in
`tests/fixtures/` and feed **only an offline scorer** — they must **never** enter a feature or the inference path
(compliance #1: no post-close data in features).

**Files:** create `src/validate.py` (offline scorer), `tests/test_validate.py`, `tests/fixtures/validation_labels.csv`
(columns: `stock_code, transaction_date, capital_type, capital_intention, source, confidence, notes`).

**Tasks (TDD):**
- [ ] **V.1** `tests/test_validate.py::test_weighted_f1_matches_sklearn` (fail first): on a tiny hand pred/truth pair,
      `validate.weighted_f1` equals `sklearn.metrics.f1_score(average="weighted")`.
- [ ] **V.2** Implement `src/validate.py::weighted_f1(pred_df, truth_df) -> dict`: inner-join on
      `(stock_code, transaction_date)`, return weighted + per-class P/R/F1 and support. **Pure, offline, no network,
      no read of board answers.** Run → pass.
- [ ] **V.3** Seed `tests/fixtures/validation_labels.csv` with **≥8** human-labeled (stock, day) rows, each citing a
      public source (龙虎榜 URL / news) and a per-row `confidence` (human action — see §below).
- [ ] **V.4** Add an **offline-only** harness (`scripts/validate_offline.py` or a notebook, **NOT** wired into
      `main.py`'s inference): run the pipeline on the labeled stock-days, join to the truth set, print proxy F1.

**How it feeds H1–H5 acceptance (additive, not a replacement):**
- Phase 1b, Phase 2, each Phase 3 batch: the PR records the **proxy-F1 before/after** on the seed set *in addition
  to* the synthetic-panel assertion. A change that moves the synthetic panel but **not** the proxy (or moves it the
  wrong way) is **flagged suspect**, not shipped as a win.
- H5: report cluster **silhouette/CH** (label-free) — Track V's one part that needs no truth labels at all.

**Acceptance (Track V itself):** `test_weighted_f1_matches_sklearn` green; seed CSV exists with cited sources; the
offline harness prints a proxy-F1 number later phases can diff against.

**Honest limits (keep visible — do not over-trust the proxy):**
- Seed set is **tiny and class-imbalanced** (龙虎榜 over-represents 游资 big-movers; 量化/散户 weakly attributable),
  so its class prior ≠ the hidden T+5 truth's. It is a **smoke detector, not a leaderboard simulator**: trust large
  regressions, discount small wins as noise.
- 龙虎榜 seat-presence ≠ whole-day dominance → **label noise**; keep/weight by `confidence`.
- **OQ-1 / R2 is resolved** (eval truth is 3-class `{游资, 量化, 散户}` — §7). The proxy still **cannot simulate the
  full T+5 backtest truth**: tiny seed, class imbalance, label noise, and a different class prior than the hidden
  eval set. Use it as a **smoke detector**, not a leaderboard simulator.

**Audit risk:** none (offline, public post-market labels, never touches inference or board answers).
**Dependencies:** none to start; becomes useful the moment Phase 1b emits real labels.

---

### Phase 1 — Cross-sample normalization seam  ⟵ **DO THIS FIRST**

**Goal:** add a pure normalization layer so rule/model inputs are comparable across stocks. Unblocks H1.

**Files:**
- Create: `src/normalize.py`
- Test:  `tests/test_normalize.py`
- (Phase 1b, separate commit) Modify: `src/label.py` to normalize the matrix before scoring.

**Design contract:**
- `normalize_matrix(matrix: pd.DataFrame) -> pd.DataFrame` — rank-normalize **each numeric column** to
  `[0,1]` across rows (the day's stock-day cross-section). Formula per column: `rank(method="average")`
  then `(r - 1) / (n - 1)`. **Flag/passthrough columns are excluded** (`cb_available`, `n_ticks`).
- **n == 1 degeneracy:** a single row cannot be ranked cross-sectionally → return **0.5** for every
  normalized column (neutral; documented; this is why the 1-stock fixture is not representative).
- Constant column (all equal) → **0.5** (no information).
- Output keeps the same index/columns; non-numeric and excluded columns pass through unchanged.

**Tasks:**
- [ ] **1.1** Write `tests/test_normalize.py::test_ranks_to_unit_interval` (fail first):
  ```python
  import pandas as pd
  from src.normalize import normalize_matrix
  def test_ranks_to_unit_interval():
      m = pd.DataFrame({"a": [10.0, 20.0, 30.0, 40.0], "cb_available": [0,0,0,1]})
      out = normalize_matrix(m)
      assert list(out["a"]) == [0.0, 1/3, 2/3, 1.0]   # min->0, max->1
      assert list(out["cb_available"]) == [0,0,0,1]   # flag passes through untouched
  ```
- [ ] **1.2** Run it → fail (`ModuleNotFoundError: src.normalize`).
- [ ] **1.3** Implement `src/normalize.py`:
  ```python
  """Cross-sample (within-day) rank normalization to [0,1]. Intraday-only: uses only
  the same-day cross-section of stocks, never future data (compliance #1)."""
  from __future__ import annotations
  import pandas as pd

  EXCLUDE = {"cb_available", "n_ticks"}  # flags / counts: not rank-normalized

  def normalize_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
      out = matrix.copy()
      n = len(out)
      for col in out.select_dtypes("number").columns:
          if col in EXCLUDE:
              continue
          if n <= 1:
              out[col] = 0.5
              continue
          r = out[col].rank(method="average")
          out[col] = (r - 1.0) / (n - 1.0)
          if out[col].nunique() == 1:   # constant column
              out[col] = 0.5
      return out
  ```
- [ ] **1.4** Run → pass.
- [ ] **1.5** Add `tests/test_normalize.py::test_single_row_is_neutral` (asserts a 1-row matrix → all 0.5
      except excluded flags) and `::test_constant_column_is_neutral`. Run → pass.
- [ ] **1.6** Commit: `feat: cross-sample rank normalization seam (H1 prerequisite)`.

**Phase 1b (separate commit, after 1):** in `src/label.weak_label_matrix`, normalize before iterating:
`norm = normalize_matrix(matrix)` and score on `norm` rows (keep intent gate on **raw** `matrix` rows —
the intent gate thresholds are absolute, not rank-based). Re-run `pytest` — the smoke test only asserts
label **validity**, so it stays green even as the fixture's emitted class changes (1-row → all-0.5 → valid).

> **The official fixture is n=1 and CANNOT validate scoring** (verified v1.1): single-row normalization
> → all-0.5 tie → arbitrary 游资; raw → 散户 via the RS bug + clip01. **Validate on a multi-row synthetic
> panel**, not the fixture.

**Acceptance criteria (Phase 1):**
- `pytest tests/test_normalize.py` green; full suite still green.
- On a constructed **multi-stock** synthetic matrix (≥10 rows, add a fixture), a clearly-游资 row (top-rank
  mega/aggression) scores `游资` as arg-max, and a clearly-量化 row (top-rank small/burst, low CV) scores
  `量化` — proving scoring became responsive (add as tests in 1b). **This panel test, not the fixture, is
  the real proof.**
- No use of any column outside the current day's matrix (compliance #1 — reviewer checks the diff).

**Audit risk:** none. **Dependencies:** none.

---

### Phase 2 — Fix the RS resolution bug + real rhythm features

**Goal:** make `rs_interval_cv` / `rs_burst_ratio` real (they are currently **bug artifacts**), then add the
split-order (iceberg) signals. **Files:** `src/features.py` (`_rs_features`, line ~103–115),
`tests/test_features.py`.

> **Root cause (verified v1.2):** `ingest` builds `datetime_utc` via `pd.to_datetime(date, unit="ms")`,
> whose **resolution is pandas-version-dependent** — `datetime64[ns]` on pandas 2.2.x but `datetime64[ms]`
> on pandas 3.0.x (this repo's current install). When it is `[ms]`, `group["datetime_utc"].astype("int64")`
> already yields **milliseconds**, so the trailing `// 1_000_000` (written assuming nanoseconds) over-divides
> — every 30 s tick gap collapses to 0 → `rs_interval_cv=13.48`, `rs_burst_ratio=0.9945`. When it is `[ns]`
> the code is accidentally correct → `cv≈1.34`, `burst≈0`. Real cadence is ~30 s (`date.diff()`≈30000 ms;
> intervals 3–30 s, mean ~5.5 s). The fix below **removes the dtype dependency entirely** (portability).

**Tasks (TDD each):**
1. Replace the interval computation with a **resolution-robust** one (the actual baseline form):
   `intervals_ms = group["datetime_utc"].diff().dropna().dt.total_seconds() * 1000` (drop negatives).
   Test: a synthetic group with 30 s-spaced `datetime_utc` yields intervals ≈30000 ms (NOT 0).
2. `rs_interval_cv = std(ddof=0)/mean` over those ms intervals; `n<2 → 0.0`. Test: uniform-cadence group
   → low CV; irregular group → high CV (hand-computed).
3. `rs_burst_ratio` = share of intervals `< 100ms` (absolute, baseline def) — **not** `<0.25·mean` (which
   is scale-free and saturates when mean≈0). Test: uniform 50ms group → burst≈1; uniform 5 s group → 0.
4. Add `rs_split_similarity = max(0, 1 - rs_interval_cv)` (baseline parity); if a `side`/direction signal
   exists add `rs_buy_interval_cv` / `rs_sell_interval_cv`, else 0.0 with a flag.
5. (Optional, only if real multi-session data later shows giant lunch-break gaps) drop intervals spanning a
   session break. **Not** the current fixture's problem — do not add speculatively (v1.0 wrongly assumed it).

**Acceptance:** new tests green; on the real fixture `rs_interval_cv` ≈ **1.34** (not 13.48) and
`rs_burst_ratio` ≈ **0** (30 s cadence has no sub-100ms bursts). Document before/after in the PR. **Note:**
this does NOT fix the fixture's 散户 label (it scores *more* retail after the fix — that's H1's job); it
makes the feature *correct* and gives H1 clean ranks to normalize.

**Audit risk:** none. **Dependencies:** independent of Phase 1; do it right after. Validate *scoring* impact
on a multi-stock synthetic panel, not the n=1 fixture.

---

### Phase 3 — Feature expansion toward the 89-set (snapshot-computable first)

**Goal:** add separable, intraday features. **Files:** `src/features.py`, `tests/test_features.py`,
`config.py` (any new thresholds as named constants). Add in small, individually-tested commits:

| Batch | Features | Source |
|---|---|---|
| 3a OFI | `ofi_mean`, `ofi_std`, `ofi_positive_ratio` from `totalbidvolume`/`totalaskvolume` `.diff()` | tutorial Path 1 |
| 3b AP runs | `ap_active_buy_run_max`, `ap_active_sell_run_max`, `ap_dominant_direction`, `ap_active_volume_pct` | baseline AP |
| 3c OBP | best-bid/ask at-ratio, near-best ratio, spread mean/std/range, weighted spread (`weightedbidprice`/`weightedaskprice` if present) | ref-set OBP |
| 3d PI | `pi_herfindahl_5min/30min`, `pi_vwap_deviation`, `pi_peak_amount_ratio`, `pi_max_price_impact_pct` | ref-set PI |
| 3e OSS | `oss_hot_money_count_pct` (large + price-move), `oss_buy/sell_amount_pct`, `oss_mega_buy_pct` | baseline OSS |

Each batch: write tests on a synthetic group with hand-computed values first; keep every feature a finite
float; register in the appropriate `_*_features` function. **Acceptance:** matrix width grows; all new
features finite on the fixture; suite green. **Audit risk:** low. **Dependencies:** H1 to be *useful*, but
features can be added independently.

---

### Phase 4 — Stage-3 GBDT head (gated on H1–H3)

**Goal:** replace the pass-through with a real LightGBM head over **confidence-weighted pseudo-labels**.
**Files:** `src/model.py`, `tests/test_model.py`, `requirements.txt` (uncomment `lightgbm`).

**Hard guards (compliance #3):** training targets are **Stage-2 weak labels only**; sample weights =
`capital_confidence`; fixed seed; **never** read `outputs/`/leaderboard answers. Cross-validate on
internal folds; if `n_samples` too small to train, **fall back to pass-through** (don't fabricate).

**Tasks:** (1) `fit` trains a 3-class LGBM on the normalized matrix with weak-label targets + confidence
weights; (2) `predict` returns calibrated class; (3) graceful fallback when `len(features) < MIN_TRAIN`;
(4) test: on a synthetic separable 3-class matrix, head recovers the planted labels with >0.9 train F1;
(5) test: tiny matrix → identical to pass-through.

**Acceptance:** tests green; full pipeline still emits valid CSVs; no path reads answers (reviewer checks).
**Audit risk:** medium (the §3.3 trap) — call it out in the PR. **Dependencies:** H1, H2, H3.

---

### Phase 5 — Metric-aligned Task-1 clustering

**Goal:** real bounded-K selection + interpretable naming. **Files:** `src/cluster.py`,
`tests/test_cluster.py`.

**Tasks:** (1) sweep `k ∈ K_RANGE` selecting by silhouette (tie-break CH), on the normalized matrix;
(2) evaluate `tslearn` `TimeSeriesKMeans(metric="dtw")` and/or GMM/HDBSCAN as alternatives — pick by
internal silhouette, document the choice; (3) name each cluster from its **actual centroid** (not fixed
predicates) using finance-grounded open-vocabulary Chinese labels + explanations (≤200 chars); (4) keep
the K=1 graceful path for tiny inputs.

**Acceptance:** on a synthetic multi-cluster matrix, K-sweep picks the planted K and silhouette beats the
fixed-K=8 baseline; every row gets a defensible `pattern_explanation`. **Audit risk:** low (don't import a
clustering lib that pulls network at runtime). **Dependencies:** H1.

---

### Phase 6 — Ops hardening

**Goal:** make nightly submission safe. **Files:** `main.py`, a packaging helper, `tests/`.

**Tasks:** (1) wire a real exchange holiday calendar into `previous_trading_day` (replace `_KNOWN_HOLIDAYS`
empty stub) — `chinese_calendar` or a maintained SSE/SZSE table; (2) `submit.zip` packager that places both
CSVs at the **archive root, no nested folders** (verification O1) with a test asserting the zip layout;
(3) multi-file glob backfill parity with the baseline's multi-input merge.

**Acceptance:** holiday-aware date resolution tested across a weekend+holiday; zip has exactly 2 root
entries. **Audit risk:** low. **Dependencies:** none.

---

### Track D — Data sourcing (local L2 + optional more-days procurement)  ⟵ **TRACKED**

> **Human guide:** `docs/human_guides/track_d_l2_procurement.md`. **v1.4 update:** the local corpus **already
> contains** orders, trades, and **reconstructable cancels** for ~7,574 stk × 2 days — **CB needs no purchase**;
> the blocker is the **Track-L adapter**, not money (`docs/data_inventory_report.md`).

| Need | Status | Unlocks | Action |
|---|---|---|---|
| tick-cancel | 🟡 **present, adapter-gated** | **CB family** — strongest 游资/量化 separator | build Track-L (reconstruct SZ `成交代码=='C'` / SH `委托类型=='D'`), then the `features._cb_features` true branch |
| order-level (tick-order) | ✅ have (`逐笔委托`) | PD (23 fields), iceberg `rs_split_*` | wire via Track-L |
| tick-trade | ✅ have (`逐笔成交`) | RS cadence, AP runs, TRD | wire via Track-L |
| **more trading days** | ⛔ only 2 days | Phase-4 training, multi-day generalization | optional vendor sourcing (guide §5) — Taobao/Xianyu/Baidu |

**Acceptance:** Track-L ingests a real cancel-bearing stock-day with `cb_available=True`; CB dims **stop voting
neutral** (keep `tests/test_rules.py::test_absent_cb_dims_vote_neutral` green for the absent path; add a present-path
test). **Provenance recorded** for the §5.5 audit. **Audit risk:** low. **Dependencies:** Track-L for CB; nothing
for procuring more days.

---

### Track L — Local L2 ingest adapter  ⟵ **PARALLEL; unblocks the local corpus**

**Goal:** read the local per-stock GBK CSVs (`行情`/`逐笔委托`/`逐笔成交`) into the cleaned frame shape
`ingest._normalise_and_clean` produces, so the whole downstream pipeline runs on **real multi-stock days** —
without touching `load_raw` (the xlsx path stays intact). **Files:** create `src/ingest_local.py`,
`tests/test_ingest_local.py`, `tests/fixtures/local_l2_tiny/` (a hand-made ≤50-row GBK sample, 1 stock).

**Tasks (TDD):**
1. Folder discovery: `data/<date>/<date>/<stock>/` → list stock-days (sampling/limit flag for dev).
2. Read `行情` (gb18030) → rename Chinese→canonical (`成交价`→price, `当日累计成交量`→cumulative volume,
   `叫买总量`→totalbidvolume, `加权平均叫买价`→weightedbidprice, …); parse `时间`(HHMMSSmmm)→Beijing hour/minute
   **directly** (no UTC round-trip → sidesteps the RS dtype bug); reshape `申买/卖价|量1..10`→`bids`/`asks` JSON.
3. Reconstruct cancels per exchange (SZ `逐笔成交.成交代码=='C'`; SH `逐笔委托.委托类型=='D'`) into a normalized
   cancel frame; set `cb_available=True`; feed `features._cb_features`.
4. Derive `bigordervolume` from large `逐笔成交` prints (absent as a snapshot column).
5. Emit the same columns downstream expects → `aggregate`/`features`/`rules` unchanged.

**Acceptance:** the tiny GBK fixture ingests; `cb_available=True`; a ≥10-stock sample yields a real
cross-sectional matrix (feeds H1 + Track V); CB dims non-neutral; suite green. **Audit risk:** low (read-only of
licensed local data; keep provenance). **Dependencies:** none — but it gates H1-on-real-data, Phase 2/3 reality,
CB, and Track V's real-data proxy.

> **Status (v1.5.4):** ✅ **Track L-a DONE** (`65116b6`) — adapter + multi-stock matrix + reconstructed cancels +
> `cb_available` plumbed; suite 37→67. ✅ **Track L-b DONE** (`87a60a8`) — real `features._cb_features` `True`-branch
> math for all 5 `CB_KEYS`, plumbed via `cancel_lookup`; suite 86→93. **Sequencing (2026-06-18):** L-b ran **after
> Phase 1b, before Phase 2**.
>
> **🟡 Track L-c OPEN (deferred follow-up — true order→cancel latency).** L-b's `cb_fast_cancel_ratio` is an
> **inter-cancel interval proxy** (consecutive `cancel_time` diffs `< CB_FAST_CANCEL_MS`), correct within a minute
> but distorted across minute boundaries and *not* the true order→cancel latency. Making it true requires extending
> `read_cancel_frame` to retain order-ref columns (SZ `叫买/卖序号`, SH `交易所委托号`), matching each cancel to its
> originating order, and computing real latency; the same join unlocks `cb_cancel_interval_cv` (a ref-set extra not
> yet in `CB_KEYS`). **Disposition:** keep deferred — *not* a Batch-2 blocker. **Do it after Batch 2 (post-Phase 2),
> and gate the win on Track V proxy-F1 once V.3 labels exist** (a proxy→true swap that doesn't move the proxy F1 is
> not worth the added ingest complexity). Audit risk: none (intraday, same-day cancel stream).

---

## 7. Risks (ranked) & open questions

| # | Risk | Evidence / why it matters | Mitigation |
|---|---|---|---|
| 🟡 **R1 — machinery landed; real-data validation pending** | **Task-2 output was near-random on real features** — the 0.6-weight task. | Verified (v1.2): fixture → 散户 in **both** pandas regimes. Two compounding causes, **both now addressed in code:** (a) the **resolution-dependent** RS computation — `astype("int64")//1_000_000` — is **fixed by Phase 2 (`f932504`)** → dtype-portable, cv≈1.34/burst≈0 on both `[ms]` and `[ns]`; (b) `clip01(raw)` saturation + no cross-sample normalization is **addressed by H1/Phase 1b (`18cca42`)** — `normalize_matrix` now rank-normalizes before capital scoring. | **Both mitigations shipped** (Phase 1b normalize-wire + Phase 2 RS fix). **Remaining:** prove the *label* actually improves on a real multi-stock cross-section via Track V proxy-F1 (needs V.3 labels) — the n=1 fixture still emits 散户-class and cannot validate the scorer. Downgrade R1 to ✅ once Track V shows a real-data delta. |
| ✅ **R2 — RESOLVED (3-class)** | **3-class vs 2-class eval mismatch.** Spec/ref-set/samples are 2-class `{游资,量化机构}`; organizer says 3-class. | **Settled 2026-06-16:** the organizer confirmed eval truth is **3-class `{游资,量化,散户}`** with `散户` scoring in weighted F1 (OQ-1 closed). The written spec/samples stay 2-class — already handled by §2 level-1 precedence. | **No code change** — the 3-class config is correct. Keep the `散户` guard (`RETAIL_GATE_MARGIN`); relax only as Track-V confidence grows. The directional-probe fallback is **no longer needed**. |
| **R3** | **CB needs cancel data — present locally, adapter-gated** (was "unavailable"). | The n=1 fixture has no cancels, but the **local corpus does**: SZ `逐笔成交.成交代码=='C'` (~22%), SH `逐笔委托.委托类型=='D'` (~24%) — `docs/data_inventory_report.md`. | **No purchase needed for the 2 local days** — build the **Track-L adapter** to reconstruct cancels, then the `features._cb_features` true branch. Source more days only for model training (Track D). |
| **R4** | **§3.3 answer-feedback trap is easy to trip** ("just grid-search thresholds against the score"). | Tutorial Path 4 literally suggests "use A-leaderboard F1 to tune in reverse" — **that is the DQ.** | Optimize thresholds on **internal** silhouette/CV only. Encode in every model/threshold PR; reviewer checks. |
| **R5** | **1→100 generalization.** Train fixture = 1 stock; leaderboards = 100. | Single-stock normalization is degenerate; rules tuned on 1 stock won't transfer. | Rank/robust features (H1), market-cap/sector neutralization (H6), no per-stock constants. |
| **R6** | **Stale docs mislead executors.** `build_notes.md` (Step B) still says 2-class validator (`量化机构`), `capital_type=量化机构` smoke output, and "24 passed". | The repo is now 3-class (commit `ee2a1d9`); suite is 37 tests; fixture emits 散户. | **Addressed in v1.1:** a supersede-by-LIS notice was added to the top of `build_notes.md`. Treat **this LIS + code** as truth. |

**Open questions to settle (and what would settle them):**
1. ✅ **RESOLVED (OQ-1, 2026-06-16) — eval truth is 3-class `{游资,量化,散户}`**, with `散户` scoring in weighted F1
   (direct organizer answer). **No code change**: the §2 lock and `config.CAPITAL_TYPES` were already 3-class. The
   written spec/samples still say 2-class — that conflict is resolved by §2 level-1 precedence, not by reverting.
   Keep the `散户` guard conservative until Track-V evidence supports relaxing it. *(Was a blocking question gating
   Phase 3; that block is now lifted.)*
2. **What object does Wasserstein/DTW score in Task 1** — per-day static feature vectors, or intraday
   time-series? → re-read brief Rev. 7 § on Task-1 metric; if ambiguous, ask organizer. Drives whether
   H5 needs TimeSeriesKMeans (sequences) or distributional clustering (feature vectors).
3. **"Market-phase recognition" (行情阶段) in spec §5.3** as a *third* F1 component. → `competition-spec/
   README.md` note #4 resolves it as folded into Task 2 (not a third CSV); our 2-head `predict_result`
   aligns. Treated as resolved; flagged so a reader hitting §5.3 isn't surprised.
4. **20% solution-report weight** (tutorial) vs the 0.4/0.6 split. → Separate **top-15 final-round**
   component, not part of the leaderboard split. LLM-drafted report is a late, cheap win for finalists.

---

## 8. Architecture map (pipeline & extension seams)

```
raw L2 xlsx ──> ingest.load_raw ───────────────> cleaned tick frame
   (65 col)        · Beijing hh clock                 · tick_* increments
                   · cumulative→diff().clip(0)         · price_change
                   · detect_cancel_table               · datetime_utc/bj
                          │
                          ▼
            aggregate.build_feature_matrix ──────> matrix [ (stock,day) × N feat ]
                   (groupby stock,day →                    SEAM: compute_window_features
                    features.compute_daily_features)              (per-hh, unused)
                          │
          ┌───────────────┴───────────────────────────────┐
          ▼                                                ▼
  [H1 SEAM] normalize.normalize_matrix              cluster.cluster_patterns   ◀ Task 1 (0.4)
   (rank→[0,1], within-day cross-section)            · K-sweep (STUB: K=8/min)
          │                                          · centroid → pattern name
          ▼                                                ▼
  label.weak_label_matrix                            pattern_reco.csv
   · rules.score_capital_type (3-class + 散户 guard)
   · rules.get_intention (買/賣/T0 gate)
   · confidence = top1−top2 margin
          │
          ▼
  model.apply_model  ◀ [H4 SEAM] CapitalTypeHead.fit/predict (STUB: pass-through)
          │
          ▼
  postprocess.assemble_predict → validate_predict (FAILS LOUD) → predict_result.csv  ◀ Task 2 (0.6)
```

**The four extension seams that matter:** `normalize_matrix` (Phase 1), `CapitalTypeHead.fit/predict`
(Phase 4), `cluster._choose_k`/`_name_cluster` (Phase 5), `features._cb_features` true branch (CB).
The **compliance gate** is `postprocess.validate_predict` — never weaken it.

---

## 9. Dynamic maintenance (when to update this file)

Update the changelog and the relevant section when any trigger fires:

| Trigger | Action |
|---|---|
| **Schema drift** (sourced L2 ≠ 65 cols / new fields like real `side`, cancel stream) | Update §3 invariants + §4 gap table; CB cross-cutting task may unblock. |
| **New organizer FAQ / clarification** | Re-check §2 locks & precedence; if it touches the 3-class question (R2) update immediately. |
| **Cancel data becomes available** | Promote **Track D** (§6); update R3 and the §4 data-inventory table. |
| **Score plateau on A-board** | Revisit H-ranking; do **not** respond by tuning to the score (§3.3) — add features / fix generalization instead. |
| **A phase lands** | Flip its `src/` row in §4 from 🟡/⛔ to ✅; record the decision in §10; bump version. |
| **Spec/brief revision** | Re-run the verification-report style check; reconcile precedence conflicts here. |

---

## 10. Decision log

| Date | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| 2026-06-14 | `capital_type` = **3-class** `{游资,量化,散户}`, bare `量化` | Direct organizer DingTalk answer (level-1 precedence) overrides the 2-class baseline guide. Encoded in config + validator + tests. | 2-class `{游资,量化机构}` (stale baseline/spec). |
| 2026-06-15 | **Normalize before scoring** (rank→[0,1] cross-section), not `clip01(raw)` | Empirically, `clip01` saturates real features → near-random output (§7-R1). Rank is leak-free (compliance #1), generalizes 1→100, and is **robust to the saturating outliers** that break clip01/z-score. | Keep `clip01`; z-score (outlier-sensitive); per-stock scaling (overfits, hard-coding-adjacent). |
| 2026-06-15 | **Fix inputs/scoring before adding a model** (H1–H3 gate H4) | A GBDT on broken pseudo-labels cannot beat broken pseudo-labels. | Jump straight to LightGBM (tutorial Path 3) — would learn noise. |
| 2026-06-15 | **散户 stays a guarded residual** (`RETAIL_GATE_MARGIN=0.05`) | Hedge against R2: if eval is really 2-class, 散户 only fires when neither real class shows signal, limiting F1 damage. | Unconditional 3-way arg-max (risk if truth is 2-class); drop 散户 (contradicts organizer). |
| 2026-06-15 | **No LLM in inference path** | Compliance #4 (reproducible/auditable). LLM allowed offline for feature ideas + report. | LLM-in-loop labeling (Path 6) — fails reproducibility audit. |
| 2026-06-15 | **Task-1 clustering should be metric-aligned** (DTW/Wasserstein-aware), open-vocab naming | Eval uses Wasserstein+DTW; FAQ Q3/A3 confirms open vocabulary scored on interpretability. | Fixed Euclidean KMeans + fixed 8 names (baseline) — metric-misaligned, rigid. |
| **2026-06-15 (v1.1)** | **RS degeneracy is a `datetime64[ms]` resolution bug, not a lunch gap** | `to_datetime(unit="ms")` → ms resolution; `astype("int64")//1_000_000` over-divides → intervals ≈0 → cv=13.48/burst=0.99. v1.0's lunch-gap story was wrong. Fix = `.diff().dt.total_seconds()*1000` (Phase 2). | v1.0 "drop lunch/pre-open gaps" (wrong cause). |
| **2026-06-15 (v1.1)** | **H1 (normalization) stays the first Sonnet task — no reorder** | Fixing RS alone scores the fixture *more* retail (0.655); normalization is the label fix AND the architectural unlock, and is testable in isolation. H2 (RS bug, Phase 2) follows; the two are independent. | RS-first (rejected: doesn't fix the label, doesn't block the normalize seam). |
| **2026-06-15 (v1.1)** | **Validate scoring on a synthetic panel, never the n=1 fixture** | Fixture (1 stock): raw→散户(bug), normalized→arbitrary tie. No single-row test can prove the scorer works. | Trusting the fixture's emitted label as a scorer signal. |
| **2026-06-15 (v1.1)** | **Fixed `rules.py` docstring now (not deferred)** | It claimed "z-score/rank" normalization; code uses `clip01(raw)`. Comment-only, zero behavior risk; a false comment in the file Sonnet reads is worse than a 1-line fix. | LIS-only note / defer to Phase 1b (rejected — leaves the lie in the code). |
| **2026-06-16 (v1.2)** | **RS fault is resolution-*dependent*; both score triples are real, neither is universally "current"** | Re-measured: pandas **3.0.3** here → `datetime64[ms]` → over-division **active** → `[0.398,0.418,0.457]`; pandas 2.2.x → `[ns]` → correct → `[0.398,0.219,0.655]`. Both → 散户. `requirements.txt` has **no upper pandas pin**, so behavior silently varies by env. Corrects v1.1's "pandas 2.x always `[ms]`" and the review's "ns is observed here". | Calling one triple "the" current state (env-dependent); pinning pandas instead of the portable Phase 2 fix (`.diff().dt.total_seconds()*1000`). |
| **2026-06-16 (v1.3)** | **Add Track V — offline validation proxy** from public post-market labels (龙虎榜/news), scored by an offline `weighted_f1`; H1–H3 acceptance reports proxy-F1 delta, not only synthetic responsiveness | Synthetic panels prove the scorer *responds*, not that it *discriminates* vs hidden T+5 truth — and F1 is 60% of the score. Public post-market labels are compliant (§5.1) and are **your** labels, not the board's (§3.3). | Rely on synthetic panels alone; use leaderboard feedback (the §3.3 auto-DQ). |
| **2026-06-16 (v1.3)** | **Promote R2 (2- vs 3-class) to BLOCKING OQ-1** with owner/deadline + per-answer decision tree | The 0.6-weight task hinges on an unverified eval class set; it is resolvable for free by the organizer and dominates Task-2 ROI. | Leave it a passive risk row; preemptively revert to 2-class (no new evidence yet — would violate the §2 level-1 lock). |
| **2026-06-16 (v1.3)** | **Re-rank H5 (Task-1 clustering) above H4 (GBDT)** on certainty-adjusted ROI; H1 stays #1 | Task-1 is scored by offline-computable metrics (silhouette/CH/DTW) → gain is *bankable* with zero §3.3 risk; H4's gain is unmeasurable offline (board-only) and bounded by pseudo-label quality. H1 still gates the normalized inputs H5 consumes. | Keep H4 ahead of H5 (ranks expected gain but ignores whether it can be measured before the board sees it). |
| **2026-06-16 (v1.3)** | **Elevate data procurement to tracked Track D** (status parity with §4) | CB is the named strongest 游资/量化 separator and is structurally zero on snapshot-only data — a ceiling cap no feature batch fixes; sourcing it is a workstream, not a footnote. | Keep CB sourcing "opportunistic / when data allows." |
| **2026-06-16 (v1.4)** | **OQ-1 RESOLVED: eval truth is 3-class `{游资,量化,散户}`** (organizer answer) | Direct organizer confirmation; `散户` scores in weighted F1. No code change — §2/`config` already 3-class. | Reverting to 2-class (the stale written spec) — contradicted by the organizer. |
| **2026-06-16 (v1.4)** | **Local corpus overturns the "cancel-missing" premise** — cancels present & reconstructable (SZ `成交代码=='C'`, SH `委托类型=='D'`), ~7,574 stk × 2 days | Verified by `scripts/inspect_local_l2.py` (`docs/data_inventory_report.md`): every ⛔ stream in the v1.3 inventory is on disk. CB needs **no purchase**. | Treating CB as purchase-gated / structurally missing (true only for the n=1 xlsx fixture). |
| **2026-06-16 (v1.4)** | **Add Track L (local L2 adapter) as the gating step for real-data work** | The corpus is GBK per-stock CSVs with Chinese headers + explicit book — not the xlsx/JSON `load_raw` reads; an adapter is required before H1/Phase2/3/CB/Track-V are *real*. | Hacking `load_raw` in place (entangles the xlsx path); deferring it as a footnote. |

---

## 11. Sonnet session starter (copy-paste)

```
You are an execution agent on AFAC2026 Track 1. Read docs/LIS.md fully, then the ONE src file
your phase names — do NOT read the whole repo.

Phase to implement: <Phase N from docs/LIS.md §6>
Target file(s): <from the phase's "Files:" line>

Hard rules (compliance §3, auto-DQ if broken):
  1. Intraday-only — no future/post-close data; cross-sample normalization uses only the same day.
  2. No hard-coding — no per-stock-code rules, no random fill. Thresholds are global config constants.
  3. No answer-feedback — never read outputs/ or leaderboard answers to tune anything.
  4. Reproducible — fixed seed (config.RANDOM_SEED), relative paths, NO LLM in the inference path.
Locked labels (exact bytes): capital_type ∈ {游资,量化,散户} (bare 量化, never 量化机构);
  capital_intention ∈ {买入,卖出,T0交易}; UTF-8-sig, 4 cols, no nulls. Validator: src/postprocess.py.

Workflow (TDD):
  - For each task in the phase: write the failing test → run it (watch it fail) → minimal impl →
    run (watch it pass) → commit. Keep commits small.
  - Run `pytest tests/ -q` (must stay green: 37+ tests) before each commit.
  - Verify end-to-end when relevant: `python main.py --input samples/AFAC2026.xlsx -o outputs/`.
  - On Windows, Chinese prints as console mojibake — that's cosmetic; the on-disk CSV is UTF-8-sig
    (check with config.CAPITAL_TYPES.index(value), not by eyeballing the console).

When done: report the acceptance criteria you met (with command output), and if you found anything that
contradicts docs/LIS.md, say so — propose a changelog line, don't silently diverge. If your phase is H1/H2/H3,
also report the Track V offline proxy-F1 before/after (§6), not only the synthetic panel.
```
