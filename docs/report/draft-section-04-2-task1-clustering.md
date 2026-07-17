# §4.2 — Modeling: Task-1 pattern clustering (Euclidean KMeans)

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 3, 10, 12). Short by design — the *method-choice* story
> (why not DTW) is the H1 discovery in **§4.3**; this section documents only the production path.

Task 1 asks us to **group** each stock-day into a behavioral pattern. Our production path is
deliberately the plainest defensible one: cluster the day's cross-section in a Euclidean
finance-feature space and name the resulting groups.

The clustering matrix is built by `src/cluster.py::build_clustering_matrix` — a **31-column
production feature matrix** over the day's panel — and partitioned by KMeans in
`cluster_patterns` (L1177). **[CLAIM]** K is not fixed: `_sweep_k` selects it by **argmax-silhouette
over K ∈ (6, 12)**, so the number of patterns is chosen by the data's own separability rather than a
hard-coded constant. **[CLAIM]** Small panels degrade gracefully — with n ≤ 1 the pipeline takes an
explicit K=1 path rather than erroring (observed in the clean smoke run: `n=1 ≤ 1; K=1 path`). Each
cluster is then given an interpretable `pattern_type` name (e.g. `游资强势拉升`) for the
`pattern_reco.csv` output.

Two design choices carry the section. First, the features fed to KMeans are the **same-day
cross-section only** — the matrix is standardized within the day (§3.3), never across dates, so there
is no look-ahead (§3.4). **[CLAIM]** Second, we deliberately did **not** adopt a trajectory-distance
(DTW/Wasserstein) clustering method as the scored-day default, even though the spec's wording points
that way. That decision is not an omission — it is the empirical result of the controlled board
experiment in **§4.3 (H1)**, which found the board's Task-1 metric tracks Euclidean-feature-space
geometry, not DTW. The DTW-complete path exists in the codebase but ships **default-OFF**.

**Honest limit.** KMeans in a fixed feature space is a *local* optimizer of one separation criterion,
and our own falsification record (§5.3) shows the method lever is nearly flat here: the constrained
K-sweep (S6) selected identical K on all 9 days, and the DTW-precomputed path (S4) degenerated. **[ADMIT]**
So we do not claim this clustering is optimal in any absolute sense — only that it is transparent,
reproducible, look-ahead-free, and (per §4.3) aligned with what the board actually rewards. The
remaining Task-1 headroom, if any, is ±0.02 and is argued in §4.3, not here.
