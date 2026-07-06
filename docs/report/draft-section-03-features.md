# §3 — Feature Engineering

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 3–7). The 35-column panel width was re-verified by the
> 2026-07-06 smoke run (freeze F5).

## 3.1 Coverage — a chosen subset of the 89-field reference set, not maximized

The reference feature set enumerates 89 candidate Level-2 fields; we build a **35-column** feature
matrix (confirmed by the smoke run: `1 (stock, day) rows × 35 features`). **[CLAIM]** Of those 35,
**24 match the reference set by exact name or rename** (e.g. `oss_mid_*`→`oss_medium_*`; ≈30 if the six
reference-family consolidations are counted), **3 are novel engineered columns** we added —
`trd_size_entropy`, `limit_seal_up_ratio`, `limit_seal_down_ratio` — and 2 are internal flags
(`cb_available`, `n_ticks`). **[CLAIM]** This is a deliberate under-build, not an incomplete one: each
feature earned its place on the offline gate (§3.2), and families that did not move the proxy were left
out or reverted (§5.3).

> **Footnote (matrix width vs clustering width).** The **35**-column feature matrix drops **4**
> EXCLUDE-listed columns (`n_ticks`, `cb_available`, `limit_seal_up_ratio`, `limit_seal_down_ratio`)
> before clustering, giving the **31**-column Euclidean clustering matrix used in §4.2/§4.3
> (35 − 4 = 31, consistent with H1). The exact column-to-reference mapping is frozen in ledger **F5**;
> coverage is stated as this reproducible mapping, not a single headline count (an earlier draft's
> "34 of 89" did not reproduce and was retired — parity flag **P2**, resolved). **[ADMIT]**

## 3.2 Discriminating families

The features that carry the capital-type signal are microstructure summaries of the day's tape, not
price alone. The gate history in §5.2 is the record of which families paid off: retail routing and a
relative-dominance guard, then trade-size entropy (`_trd_size_entropy`), then limit-up
de-contamination (`_limit_seal_features`) — together moving the proxy-F1 from 0.3371 up through the
0.60s (Row 6). **[CLAIM]** Cancel-burst (CB) features (`_cb_features`) add a manipulation-pattern
signal on the richer parquet source.

**Honest limit — the CB proxy.** Our CB features are an **inter-cancel-interval proxy**, not a true
order→cancel latency: the parquet corpus carries a dormant `latency_ms` field, but swapping it in
**regressed** the gate (0.6599 → 0.6500), so we kept the proxy and did not consume true latency
(Row 7). **[ADMIT]** We report the CB family as a heuristic manipulation signal, not a latency
measurement.

## 3.3 Cross-sample within-day rank normalization (the H1 seam)

The single most load-bearing transform is `src/normalize.py::normalize_matrix` (L33), wired into
`src/label.weak_label_matrix`: within each day's cross-section it converts raw feature values to
**per-column ranks over the day's rows**. **[CLAIM]** This is what lets a scorer trained on the
sample's handful of stocks generalize to the 100-stock scoring panel — absolute feature magnitudes
vary by regime, but a stock's *rank among its same-day peers* is stable. It is also the seam behind the
H1 finding: the board's Task-1 metric rewards geometric separation in this normalized Euclidean space
(§4.3 / §5.4). A red-first panel test discriminates when the wiring is reverted (Row 3).

## 3.4 Compliance by construction

Normalization is exactly where a look-ahead leak would hide, so the design forecloses it: the rank is
taken **only over the same day's panel rows, never across dates** (`EXCLUDE` list + per-column rank in
`normalize.py`), so no future information and no cross-day statistic can enter a feature (Row 4;
compliance #1). **[CLAIM]** Combined with §2.2 (no LLM, fixed seed, recompute-from-raw), the feature
layer satisfies the competition's information-timing rules by construction rather than by promise —
the property a reviewer can confirm by reading the diff, not by trusting a claim. **[CLAIM]**
