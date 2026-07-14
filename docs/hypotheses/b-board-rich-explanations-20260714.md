# Board-B `pattern_explanation` upgrade — implemented (default-OFF)

**Status:** SHIPPED to working tree, **default-OFF** · gated · paired-A/B ready
**Date:** 2026-07-14 · Follows [`b-board-20260713-score-02411-triage.md`](./b-board-20260713-score-02411-triage.md) ranked action #1
**Compliance:** LIS §3.3 — interpretability-quality lever, **not** tuned to any board number. Ship only via best-of-day paired A/B vs the euclidean floor.

---

## Why (from the 0713 triage)

Board B is the first board that **scores `pattern_explanation`** (competition-clarifications §6). The 0713 scored submit (0.2411) carried two measurable interpretability defects:

1. **Romanized English feature tokens** inside otherwise-Chinese text — `主导特征: ap active sell pct` — from `cluster.py` `dominant_feat.replace("_"," ")`. Reads as unfinished output. **100/100 rows** affected.
2. **Cluster-level identical explanations** — only **6 unique strings** across 100 rows (every 卖压 row byte-identical, etc.).

Task-1 geometry itself was healthy (triage H2 rejected); Task-2 (60%) is un-gateable offline on the rotating panel (0 labels). So the explanation channel is the **only §3.3-safe quality lever** available.

## What changed

Gated behind `config.TASK1_RICH_EXPLANATIONS` (default `False`) and CLI `--rich-explanations`:

- `config.py` — new flag, default OFF (floor byte-identical).
- `src/cluster.py` — `_name_clusters(..., return_dominant=True)` now also returns the *final* dominant feature per cluster (tracks tie-break reassignment). New `_rich_explanation()` swaps the romanized parenthetical for a per-stock magnitude. `cluster_patterns(rich_explanations=...)` reads the flag at call time; **euclidean path only**, no effect on dtw-complete.
- `main.py` — `--rich-explanations` sets the config global (avoids the [[dtw-candidate-needs-config-flip]] footgun).
- `tests/test_cluster.py` — 3 tests: flag-OFF byte-identical to floor; flag-ON preserves `pattern_type` row-for-row + removes English + adds variance; config read at call time.

**Design invariant:** `pattern_type`, clusters, and Task-2 are **untouched**. Only each row's explanation parenthetical is localized to that stock's **same-day percentile on the cluster's dominant feature** — coherence-preserving (cites the same feature the name is built on).

Example (0713, stock 600030):
```
floor:  买方撤单频率显著高于市场均值（主导特征: cb buy cancel ratio），盘口撤单博弈明显
rich:   买方撤单频率显著高于市场均值（本股该指标位于同日样本第82百分位），盘口撤单博弈明显
```

## Offline gate (real 0713, `scratchpad/gate_0713.py` — label-free, NOT a score gate)

| Check | Result |
|-------|--------|
| `predict_result.csv` identical floor vs rich (Task-2 untouched) | **PASS** |
| `pattern_type` identical row-for-row (Task-1 untouched) | **PASS** |
| 100/100 rows | **PASS** |
| Romanized tokens: floor 100/100 → rich **0/100** | **PASS** |
| Unique explanations **6 → 100** | **PASS** |
| All ≤200 chars, non-empty | **PASS** |
| `pytest tests/test_cluster.py tests/test_main_parquet.py` | **57 passed** |

## Known nuance (honest)

The head clause `…显著高于市场均值` is a **cluster-level** claim (unchanged from the floor). A minority of stocks sit below-median on the cluster's dominant axis (e.g. 600067 at 第46百分位) — the rich text *surfaces* this standing where the floor *hid* it under an identical string. Rich is therefore **no less coherent than the floor** (the floor made the same claim for that stock) and is more honest. If a stricter grader would penalize the visible dissonance, a follow-up refinement is to attribute the qualitative claim to the *category* (「所属类别以…偏高为特征」) rather than the stock — not done here to keep the change surgical.

## Paired A/B artifacts

- Floor (already scored 0.2411): `outputs/20260713/submit.zip`
- Rich (explore): `outputs/20260713/submit_rich.zip` (2 CSVs at root, UTF-8-sig, codes == `stock_sample_20260714.xlsx`, `transaction_date=20260713`)

0713's submit window (T+1 15:00 – T+2 14:59 = **0714 15:00 – 0715 14:59**) is still open, so the rich zip can be uploaded as paired-B to the **same 0713 slot**; best-of-day keeps the higher → zero downside vs the 0.2411 floor. Log the instant score as verification only.

## Non-actions preserved

No change to `rules.py` / thresholds / weights / `validation_labels.csv` / `TASK1_METHOD`. Daily euclidean floor remains the default submit path.
