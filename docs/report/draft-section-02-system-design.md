# §2 — System Design & Pipeline

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 1, 2). Architecture facts were re-verified by the
> 2026-07-06 clean smoke run (`repro-pack-readiness.md` G3).

## 2.1 Architecture — one entry point, five deterministic stages

The whole system is a single command, `python main.py`, that recomputes every output from raw
Level-2 data. There is no training artifact to load and no intermediate cache to trust — the pipeline
runs the same five stages end to end on every invocation. **[CLAIM]**

| Stage | Module | Responsibility |
|---|---|---|
| 1 — ingest | `src/ingest` · `src/ingest_parquet` | read raw L2 (xlsx or parquet) into a normalized frame |
| 2 — features | `src/aggregate` (+ `src/features`) | build the per-(stock, day) feature matrix |
| 3 — Task-1 clustering | `src/cluster` | Euclidean KMeans → `pattern_type` (§4.2) |
| 4 — Task-2 labels + head | `src/label` · `src/model` (stub) | weak labels → capital type + intention (§4.1) |
| 5 — assemble + validate + write | `src/postprocess` | contract-check and emit the two CSVs |

The clean smoke run logs exactly this `[1/5] … [5/5]` progression and writes both
`pattern_reco.csv` (Task 1) and `predict_result.csv` (Task 2), each through a loud output contract that
fails the run on any format/label/date breach (Row 22). **[CLAIM]** The design goal is auditability:
every stage is a named module with a single responsibility, so a reviewer can trace any output cell
back to the raw tick that produced it.

## 2.2 Reproducibility contract

Three guarantees, asserted in `main.py`'s header and enforced in code, make the pipeline replayable
and compliant:

1. **Byte-determinism / fixed seed.** All stochastic components draw from `config.RANDOM_SEED = 42`;
   re-running `--pack` produces a byte-identical zip, and the live board reproduced an identical
   instant score (0.5245) on re-upload (Row 1, Row 18). **[CLAIM]**
2. **No LLM in the inference path.** A grep of `src/ main.py` for `openai\|anthropic\|llm\|http`
   returns only docstrings stating the absence; `src/model.py` is a stub, not a model call. LLMs were
   used offline only, for feature research and this report (Row 2). **[CLAIM]**
3. **Relative paths + declared deps.** No absolute paths appear in `src/`, `main.py`, or `config.py`;
   dependencies are declared in `init_env.sh` → `requirements.txt` (§7; spec §5.5). **[CLAIM]**

Recomputing-from-raw is the load-bearing property: because nothing is memoized to disk between runs,
there is no path by which a stale or hand-edited intermediate could leak into a submission.

## 2.3 Dual ingest adapters

The ingest stage carries **two adapters behind one interface** so the same downstream pipeline serves
both the competition's data and our validation corpus. **[CLAIM]** `src/ingest` reads the official
Excel sample (`--input samples/AFAC2026.xlsx`, openpyxl). `src/ingest_parquet` reads our internal
parquet L2 corpus via a `parquet:data/YYYYMM` input scheme (pyarrow), which is what every offline gate
in §5 scores against. The adapters normalize to the same frame, so Stages 2–5 are identical regardless
of source — the pipeline cannot tell which adapter fed it.

**Honest limit.** The two data surfaces are not identical in richness: the parquet corpus carries
tick-level cancel information the snapshot Excel path does not, so a CB (cancel-burst) feature family
**degrades to zero** on snapshot-only input (the smoke run logs exactly this:
`no tick-cancel table detected -> CB features degrade to zero … pipeline continues`). **[ADMIT]** This
is a graceful, logged degradation rather than a failure, but it means CB-dependent discrimination is
only available on the richer parquet source — a caveat we carry into §3.2 and §8.
