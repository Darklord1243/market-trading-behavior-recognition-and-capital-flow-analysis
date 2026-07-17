# Competitive Gap Audit — 2026-07-03 (Fable 5, Phase 0, READ-ONLY)

**Repo:** market-trading-behavior-recognition-and-capital-flow-analysis · **Branch:** feat/phase6-parquet-submit · **HEAD:** cf46986
**Board context:** latest instant score **0.5245** (Jul 2 upload, 20260701 data); prior points 0.2597 / 0.4586 / 0.4558 / 0.3265 / 0.3333; rank ~157; leaders ~0.85/0.81/0.77. Deadline **2026-07-10 23:59**; ~6 submission days left.
**Compliance:** read-only audit; no source/config/label changes; no board tuning proposed anywhere below (LIS §3.3). All new measurements are label-free.

---

## 1. Executive verdict

1. **The single concrete, new defect found: our submitted Task-1 grouping has NEGATIVE cohesion in the metric space the spec names.** Measured today: DTW-space silhouette of the *production* (submitted) cluster labels = **−0.1248 (0625)** and **−0.1625 (0629)**. Under the Wasserstein+DTW metric family the spec explicitly lists for Task-1 (§5.2), the average stock in our submission is closer to *other* clusters' intraday trajectories than to its own. No prior slice ever measured this number — Slices 1/4/6 compared *alternative clusterings*, never the production labels in DTW space. Confidence in the measurement: high. Confidence that the board scores something DTW-like on our grouping: medium (spec says so; exact blend unknown).
2. **A non-degenerate fix is feasible and was demonstrated today.** Complete-linkage clustering on the same precomputed DTW matrix at K=3 gives **DTW-sil +0.4405 with cluster sizes [4, 34, 62] — no singletons** (0629). The Slice-4 degeneracy was an **average-linkage artifact**, not a property of DTW clustering. This is the one Sonnet slice to ship this week (§6).
3. **The A-board is a moving weighted average over daily submission slots, and a missed day scores 0** (spec §5.1: 移动加权平均; “过期当天得 0 分”). We missed ~11 early trading days (first upload Jun 24) plus **20260630** (no parquet ever procured), and **outputs/20260702 does not exist yet** — tonight’s upload is not generated. Ops discipline is a quantifiable lever: every remaining missed day costs a full day-slot; every submitted day banks ~0.45–0.52 at the current pipeline level. This also gates B-board entry (valid A-board result required; B-board then *requires* ≥8 daily submits).
4. **Day-to-day board variance is not explained by anything we control.** Across the six scored days, capital/intent/pattern output distributions are stable while the board swings 0.26↔0.52 with zero scorer changes between 0.3333 (0629) and 0.5245 (0701). The H5 “hard key day” reading stands. Do not interpret single-day deltas; the moving average is the objective.
5. **Task-2 is measured-out for this week. Stop polishing it.** Capital rules are boxed in by five frozen floors and six falsified slices; the LHB proxy (n=154, audit-grade) is a smoke detector that has already caught everything it can catch. No Task-2 rule change is offline-measurable enough to justify spending the last week on it. The proxy work itself (daily 16-row label batches with dual audits) should be **paused** — its marginal decision-value is now near zero.
6. **行情阶段 (market-phase F1) remains the least-understood scored component of Task 2** — resolved by assumption (“rolled into Task 2 or legacy”) rather than by evidence. A DingTalk question to the organizer is free, compliant, and could reprice the whole roadmap. Same for “what representation does Task-1 区分度/聚合度 score?”. Ask both **today**.
7. **The trajectory-space Task-1 fix doubles as a phase hedge**: trajectory clusters are literally intraday-price-path shapes (单边拉升 / 冲高回落 / 横盘震荡…), so their names & explanations carry 行情阶段 semantics that our current microstructure-feature names (55–64% fallback 机构长线配置) do not.
8. **What isn't worth doing this week:** GBDT (unmeasurable, §3.3 trap), more label expansion, any capital-rule tweak, another Euclidean K-sweep variant, intent-band retuning (proxy already optimized it; board semantics unknown), re-litigating 0626/0629.
9. **Honest ceiling:** nothing here closes to 0.85 in a week. Realistic path: consolidate a 0.5+ daily band, add whatever the Task-1 alignment buys (0 to ~+0.15/day, unknowable offline), qualify for B-board, and win the reproducibility/report stage (the written report is 20% of final review scoring — tutorial §6.2).

---

## 2. Evidence (commands, files, numbers)

### 2.1 New measurements (this audit, label-free)

Scratch scripts `scripts/_audit_dtw_prod_labels.py` and `scripts/_audit_lowk_probe.py` (deleted after this audit, per Phase-0 rules). Both rebuilt the production panel matrix via `src.pipeline_parquet.build_feature_matrix_for_panel`, reproduced the exact production Task-1 path (`build_clustering_matrix(matrix, None)` → `_sweep_k` → `KMeans(seed=42)`), built the (30-bin × 3-series) intraday trajectories via `src.intraday_trajectory.build_trajectories`, and the pairwise DTW matrix via `src.cluster._dtw_distance_matrix`.

**A. DTW-space silhouette of PRODUCTION labels (the submitted grouping):**

| date | panel n | prod K | prod sizes | Euclid sil | **DTW-sil of prod labels** | wass_sep | dtw_sep |
|------|---:|---:|---|---:|---:|---:|---:|
| 20260625 | 100 | 6 | [8,8,14,17,22,31] | 0.1548 | **−0.1248** | 0.0086 | 10.31 |
| 20260629 | 100 | 8 | [9,10,11,11,13,14,15,17] | 0.1427 | **−0.1625** | 0.0047 | 5.86 |

Negative silhouette = anti-structure: our clusters actively cut across trajectory-space neighborhoods. For calibration, the *degenerate* Slice-4 average-linkage solution scored +0.36–0.54 in this space, and random-ish labels would score ≈0. **We are below random under this metric.**

**B. Feasibility probe (20260629): non-degenerate DTW clustering + the untested low-K region.**

Euclidean KMeans silhouette by K (production sweep is clamped to `K_RANGE=(6,12)` — K=2..5 had never been evaluated):

```
K=2 0.1809*  K=3 0.1552  K=4 0.1465  K=5 0.1497  K=6 0.1377
K=7 0.1396   K=8 0.1427(prod)  K=9 0.1288  K=10 0.1345  K=11 0.1289  K=12 0.1284
```

DTW-space complete-linkage (chaining-resistant) on the precomputed DTW matrix:

```
K=2 dtw_sil=0.7300 sizes=[4,96]         (max-share 0.96 — degenerate)
K=3 dtw_sil=0.4405 sizes=[4,34,62]      (min=4, NO singletons)  ⟵ feasible
K=4 dtw_sil=0.4333 sizes=[1,4,34,61]    (1 singleton)
K=7 dtw_sil=0.2839 sizes=[1,1,3,4,22,30,39]
```

Complete linkage at K=3 (and near-K with singleton-merge) delivers a coherent 3-mode trajectory partition at **+0.44 DTW-sil vs the production grouping’s −0.16** — a ~0.6 swing in the spec-named metric, with zero labels touched. The Slice-4 rejection (“degeneracy on every day”) does **not** transfer: it was average-linkage-specific.

### 2.2 Board & submission record (docs + outputs/ on disk)

| data day | instant score | rows | capital 游/量/散 | intent T0/买/卖 | top pattern (share) |
|---|---:|---:|---|---|---|
| 20260623 | 0.2597 | 99 | 44/27/28 | (uploaded zip was pre-P2-intent: T0=92) | diverse, 6 types |
| 20260624 | 0.4586 | 99 | 38/31/30 | 61/19/19 | 机构长线配置 32% |
| 20260625 | 0.4558 | 100 | 41/31/28 | 64/26/10 | 机构长线配置 61% |
| 20260626 | 0.3265 | 100 | 42/30/28 | 63/16/21 | 机构长线配置 43% |
| 20260629 | 0.3333 | 100 | 42/28/30 | 66/31/**3** | 机构长线配置 64% |
| 20260701 | **0.5245** | 100 | 48/22/30 | 59/38/**3** | 机构长线配置 55% |

Reading: output composition is nearly constant; board swings ±0.19 anyway. The only quasi-causal signal in the whole series is 0623→0624 (+0.20) coinciding with the intent de-degeneration (T0 92%→~50%) *and* the P5.1b naming change — not decomposable. 0629→0701 (+0.19) had **no scorer change at all** (`git log d429674..cf46986`: docs, label seeding, default-off harness, --pack path fix) — pure key/day variance. Corollary: the 0.5245 does not validate anything we did, and 0.3333 did not falsify anything either.

Missed day-slots so far: Jun 9–23 never uploaded (~11 trading days; first upload Jun 24), **20260630 missing entirely** (no parquet under `data/202606/`, no `outputs/20260630`). `data/202607/十盘档口/` has 20260701 + 20260702; **`outputs/20260702` does not exist yet** → tonight’s submission must still be generated and uploaded.

### 2.3 Scoring mechanics (spec re-read — the load-bearing lines)

- `topic-specifications-and-data.zh.md` §5.1: “多次更新按**时序跟踪效果**综合评分（**移动加权平均**）” + A-board “截止 交易日 23:59 前提交，**过期当天得 0 分**”; ≤3 uploads/day, last one counts. §5.2 Task-1: “评估：类间区分度 + 类内聚合度；距离：**Wasserstein + DTW**”. §5.3: 参与者/方向意图/**行情阶段** each scored by F1 inside Task 2 (0.6); Total = 0.4·Task1 + 0.6·Task2.
- `competition-clarifications.md` A3: pattern_type open vocabulary, scored on **rationality & interpretability**.
- `competition-spec/README.md` note 4: the 行情阶段 component is unresolved (“treat as rolled into Task 2 or legacy”) — an assumption, not an organizer answer.
- B-board (Jul 13–24): daily submission mandatory, <8 days → unranked; TOP15 reproducibility review; tutorial §6.2: written solution report ≈ **20% of final score**.

### 2.4 State verified (not re-derived from docs)

- Labels: `tests/fixtures/validation_labels.csv` = **154 rows / 11 days** (0616–0702, 0702 batch on disk, uncommitted); 20260702 batch independently audited (0 disputes, 0 blocking errors — `scripts/lhb_0702_independent_audit_report.md`).
- Offline gates: capital **0.6438/n=122** (through-0629) and intention **0.6750/n=115** floors held byte-identical at the Jul-1 verify (n=138 combined gate: capital 0.6627, intention 0.6638). No scorer-path commit since → floors stand without re-run. The n=154 combined gate has not been run yet (0702 batch pending Track-V verify).
- Test suite re-run this audit: **222 passed, 2 xfailed** (green).
- Production Task-1 path (`src/cluster.py::cluster_patterns`): Euclidean KMeans on rank-normalized daily matrix, K=argmax-silhouette in (6,12), one-dominant-feature naming, fallback 机构长线配置 — hence the 43–64% fallback share on recent days.
- Intent gate (`src/rules.py::get_intention`): net = buy−sell with asymmetric bands (+0.08 / −0.18, the τ_sell fitted on the n=64 proxy). On broad up-days almost nothing crosses −0.18 → 卖出 = 3/100 on both 0629 and 0701.

---

## 3. Gap analysis — my framing

**The gap to 0.85 has three independent layers:**

**Layer 1 — Missed day-slots (ops).** Final A-board = moving weighted average over daily slots with zeros for misses. We have ~6 scored slots out of ~17 elapsed; leaders likely have all of them. Whatever the weighting, a zero-slot is the one number we control with certainty. This layer needs no model work, only discipline: procure data + run + upload, every day through Jul 10. The 0630 hole and the not-yet-generated 0702 zip show this is a real, current failure mode, not hypothetical.

**Layer 2 — Task-1 (0.4 weight) actively mis-aligned.** Previous audits framed Task-1 as “mediocre at silhouette 0.15.” The new measurement says it’s worse than mediocre **in the spec’s own metric space**: negative DTW cohesion. Mechanism: KMeans partitions the rank-normalized *microstructure feature* space into 6–12 statistically-thin slices; those slices scramble the *trajectory* neighborhoods that Wasserstein/DTW see. If the board’s 区分度/聚合度 is computed on anything trajectory- or distribution-shaped (the two distance names strongly suggest it), our Task-1 contribution is at or near the floor of what any submission could score — i.e. up to ~0.4·(mid-tier Task-1) ≈ 0.1–0.2 of total is recoverable. This is the only layer where a week of engineering has a plausible large payoff, and it is fully offline-measurable and label-free.

**Layer 3 — Task-2 vs a truth generator we cannot see.** Proxy-F1 ~0.64–0.68 on LHB names; board Task-2 unobservable. Six falsified slices + five frozen floors say the rules are at their local optimum given what we can measure. The two known distribution-level oddities — 卖出 3%, 游资 48% — are *suspicious* but not offline-falsifiable: the proxy blessed the current bands, and re-tuning them by “what feels like the right distribution” is exactly the un-measurable tinkering that burned 0626/0629 chases. The only cheap, compliant moves on this layer are (a) organizer clarification on 行情阶段 semantics, and (b) keeping the floors frozen so daily submits stay stable.

**What do leaders plausibly have that we don't?** In order of likelihood: (1) full attendance since Jun 9 under the moving average; (2) a Task-1 grouping that is coherent under trajectory/distribution distances (any team that clustered price-path shapes directly gets this for free); (3) possibly a Task-2 head aligned with the organizer's truth generator (their baseline lineage + richer features). (3) is the one we can neither verify nor safely chase in a week.

---

## 4. Ranked recommendations

| # | Action | Type | Expected lift | Offline-measurable? | Compliance / gate risk | Effort |
|---|---|---|---|---|---|---|
| 0 | **Zero missed submissions through Jul 10** — generate + upload 20260702 tonight; daily parquet procurement checklist; treat a missed day as a P0 incident | ops (human) | protects ~0.45–0.52 × weight of each remaining slot; the only *certain* lever | n/a | none | ~1h/day |
| 1 | **Task-1 trajectory-space production clustering** (complete-linkage on precomputed DTW, low K, singleton-merge, phase-flavored naming) — §6 | Sonnet slice | board: **0 to ~+0.15/day** (unknown blend — honest); internal: DTW-sil −0.15 → ≥ +0.25, certain | **yes, fully** (label-free DTW-sil/CH/degeneracy per day) | none (label-free, spec-aligned); Task-2 untouched byte-identical | 8–14h |
| 2 | **Two DingTalk questions to the organizer**: (a) how exactly is 行情阶段识别分 computed from our two CSVs? (b) what object does Task-1 区分度/聚合度 score? | human, free | possibly strategy-repricing (行情阶段 could be a silently-zero component) | n/a | none — scoring-mechanics clarification, same class as the answered 3-class question | 15 min |
| 3 | **Pattern-explanation quality pass** (rides on #1): per-cluster quantitative explanations (actual trajectory/feature values vs market mean) instead of one-line templates; eliminate the 55–64% generic-fallback share | small Sonnet add-on | unknown (judged “rationality/interpretability” channel); cheap hedge | no — admit it (judged component) | none | 2–4h |
| 4 | **Do-nothing guard on Task-2**: no rule/threshold/feature changes this week; floors stay frozen; pause daily LHB label batches (n=154 is enough for any regression gate) | resource reallocation | frees ~2–3 human-hours/day + audit effort | n/a | reduces risk (fewer changes before deadline) | negative |

Not ranked (rejected): GBDT head (§3.3 trap, unmeasurable, bounded by pseudo-labels), intent-band retune (proxy already optimized it; falsified Slice 3 showed absolute bands beat alternatives on everything measurable; board semantics unknown), label CSV expansion as a lever, any Euclidean K-sweep variant (Slice 6 proved production Euclidean clustering is non-degenerate and at its sweep optimum; the residual Euclidean gain of low-K — 0.18 vs 0.14 — is small next to the DTW swing and conflicts with it).

**Why #1 is not a rehash of the falsified slices** (all three structural deltas at once):
- *vs Slice 1 (metric-alignment enrichment):* no Euclidean space, no summary-feature enrichment, no composite-K. We cluster **on** the DTW distance.
- *vs Slice 4 (DTW-precomputed):* different linkage (**complete**, chaining-resistant — today's probe shows it produces [4,34,62] instead of [91,2,3,1,1,1]); different acceptance object (**production labels’ DTW-sil**, baseline −0.12/−0.16, must go positive) instead of “beat 0.1509 Euclidean”; **degeneracy constraints baked into selection** (min size ≥ 2 via singleton-merge, max share ≤ 0.60/0.65) exactly as Slice-4’s own post-mortem recommended for “a fresh falsifiable attempt”.
- *vs Slice 6 (constrained K-sweep):* not Euclidean, not KMeans, not a K-selection tweak — a different metric space entirely, which is the “different feature/metric space” Slice-6’s memory note said would be required.

---

## 5. The arithmetic of what remains

Unknown weighting prevents precision; bounding scenarios (≈23 A-board trading days, ours: ~6 scored + ~6 remaining):

- **Uniform average with zeros:** ceiling ≈ (6×0.42 + 6×s)/23 → ≈0.24 even at s=0.55; rank stays low regardless of model work. If the platform instead averages only submitted days (or weights recent heavily — “时序跟踪效果” suggests recency), each remaining day at 0.5+ materially moves the number. Either way the decision is identical: **submit all 6 remaining days, and raise the per-day band where measurable (Task-1).**
- **B-board is the real prize.** A valid A-board result qualifies us; B-board (Jul 13–24, daily mandatory, ≥8 days) restarts the average — full attendance there puts us on equal footing structurally. Everything shipped this week (Task-1 alignment, ops pipeline, report drafting) compounds into B-board.

---

## 6. The one pick (for Opus to write the Sonnet dispatch)

**Slice P5.7 — Task-1 production path: trajectory-space clustering (DTW complete-linkage, low-K, phase-named).**

- **Hypothesis:** the board’s Task-1 区分度/聚合度 under Wasserstein+DTW rewards grouping stocks by intraday trajectory shape; our submitted grouping is anti-correlated with that space (DTW-sil −0.12/−0.16). Clustering on the DTW distance with complete linkage at low K yields a coherent partition (+0.44 at K=3 on 0629, sizes [4,34,62], no singletons).
- **Files:** `src/cluster.py` (new production method `dtw_complete`: complete-linkage on `_dtw_distance_matrix`, K selected by argmax DTW-sil over K∈2..8 **subject to** min-cluster-size ≥ 2 after singleton-merge-to-nearest-cluster and max-share ≤ `TASK1_MAX_CLUSTER_SHARE`; reuse existing Slice-6 constants), `src/pipeline_parquet.py` + `main.py` (thread trajectories into `cluster_patterns` on the parquet path — seam already exists), naming layer (trajectory-shape lexicon from `summary_features`: front/back load, return amplitude & direction, imbalance trend → phase-flavored Chinese names e.g. 全天单边拉升 / 冲高回落出货 / 尾盘集中放量 / 横盘均衡震荡, plus per-cluster quantitative explanations), `tests/test_cluster.py`.
- **Config-gated:** `TASK1_METHOD = "dtw_complete"` new constant; `"euclidean"` legacy path retained byte-identical for rollback.
- **Acceptance (pre-registered, label-free, all 11 days 0616–0702):**
  1. DTW-sil of the production labels ≥ **+0.15** on every day (baseline −0.12/−0.16 on the two measured days; re-baseline the rest in the slice);
  2. no singleton clusters after merge; max cluster share ≤ 0.65; K ≥ 3;
  3. ≥ 3 distinct pattern_type per day, none > 65% share (fixes the 55–64% fallback degeneracy as a side effect);
  4. Euclidean silhouette reported honestly per day (it will drop — an explicit accepted trade, stated in the PR);
  5. Task-2 gates byte-identical (capital 0.6438/n=122, intention 0.6750/n=115, all frozen floors) — clustering must not touch `rules.py`/`label.py`/`features.py`;
  6. runtime ≤ ~7 min/day added to the submit run (DTW matrix ~5–6 min on 100 stocks; acceptable inside the nightly window — if not, cdist-vectorize the local cost before widening bins);
  7. suite green.
- **Falsification:** if complete-linkage (and one fallback: hand-rolled PAM/k-medoids on D, ~60 lines, seed-fixed) cannot reach +0.15 non-degenerately on ≥ 9/11 days, do **not** ship; file the negative and revert to `euclidean`.
- **Why now:** it is the only lever that is simultaneously (a) large-if-right (0.4 weight currently at/below floor), (b) fully offline-measurable, (c) zero compliance risk, and (d) small enough to ship + soak on 2–3 live submits before Jul 10 (and to carry into B-board).

---

## 7. Do-not-do list (tempting, wastes the clock)

1. **Do not** retune the intent bands (τ_sell) or capital rules to “fix” 卖出=3% / 游资=48% — no offline instrument can validate it; the proxy already optimized these; this is the 0626/0629 trap shape.
2. **Do not** run GBDT/Phase 4. Unmeasurable offline; bounded by pseudo-label quality; §3.3 trap.
3. **Do not** add LHB label batches this week (and stand down the dual audits). n=154 is regression-gate-sufficient; the marginal row changes no decision.
4. **Do not** iterate further inside Euclidean space for Task-1 (enrichment, K tweaks, balance constraints — Slices 1/4/6 closed this).
5. **Do not** chase per-day board deltas, including tomorrow’s settled T+ number for 0701 (verification-only, §3.3).
6. **Do not** spend the week widening features toward the 89-set — with no measurable Task-2 head to consume them before Jul 10, it's B-board work at best.
7. **Do not** skip a submission day to “finish the slice” — the slice is worthless if a day-slot zeroes.

---

## 8. Open questions (what tomorrow can teach us)

1. **Settled T+ score for 0701 (and 0702’s instant score):** if 0702 also lands ≥0.5 with the unchanged pipeline, the 0.33 band was key-mix variance and our stable band is ~0.45–0.52 — raising confidence that per-day consistency (ops) + Task-1 are the right two bets. If 0702 collapses to ~0.33 again, it further confirms variance and changes nothing strategically (do not react to it).
2. **Organizer answers** to the 行情阶段 and Task-1-object questions (§4 #2) — the highest-information pending input; could add or remove an entire scored component from our model of the objective.
3. **After P5.7 ships:** do the 2–3 live submits carrying the new Task-1 land visibly above the 0.45–0.52 band? One or two points prove nothing (see #1) — but a sustained shift by Jul 13 (A-board final publication) plus B-board week is the real test.
4. **Unresolved and accepted:** whether the board’s Task-1 blend weights interpretability-judging vs metric cohesion; whether Task-2’s truth generator can be approximated at all without account-level data. Both parked — no compliant instrument exists this side of the deadline.

---

*Audit artifacts: scratch scripts `scripts/_audit_dtw_prod_labels.py`, `scripts/_audit_lowk_probe.py` deleted after measurement (results reproduced verbatim in §2.1). No source, config, data, or label file modified. Test suite re-run at audit close: **222 passed, 2 xfailed** (green; suite has grown past the 169 recorded in LIS v1.6.8).*
