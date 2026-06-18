# Sonnet execution prompt — Track L (local L2 ingest adapter)

> **Status:** Ready to run. **LIS v1.4.1** §6 **Track L**. Highest-leverage track: turns the local
> ~7.5k-stock corpus into pipeline-readable input and unblocks CB.
>
> **Parallel tracks (context only — out of scope here):** Phase 1 (normalize), Track V (offline validate),
> Track D (human procurement). See `docs/LIS.md` §6.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Track L only** — the local GBK-CSV L2 ingest adapter.

**Read (minimal):**
- `docs/LIS.md` §6 **"Track L — Local L2 ingest adapter"** (and §2–§3 if you have not seen them this session)
- This prompt
- `docs/data_inventory_report.md` — local CSV layout, schemas, per-exchange cancel encoding, adapter sketch (§6)
- `src/ingest.py` — the **target output shape**: what `_normalise_and_clean` produces and `compute_daily_features` consumes

Do **not** re-read the whole doc tree.

**Out of scope this session:** Phase 1 and Phase 1+ (normalize, RS fix, features, model, clustering), **Track V / Track D**,
**modifying `src/ingest.load_raw` in place** (the xlsx path must stay intact — add a *new* module), loading the full
**~102 GB** `data/` in tests (tests use the tiny committed fixture only), any `docs/LIS.md` edit unless you hit a
factual contradiction (flag it; propose a changelog line; don't silently change LIS).

---

# LIS v1.4.1 context (trust these; do not re-derive)

| Item | Note for Track L |
|---|---|
| **OQ-1 / R2** | ✅ Resolved — eval is **3-class** `{游资, 量化, 散户}`. You are not touching labels/scoring. |
| **Official fixture** | `samples/AFAC2026.xlsx` = **1 stock**, xlsx, English headers, JSON book — the `load_raw` path. Leave it working. |
| **Local corpus** | `data/<date>/<date>/<stock>/{行情,逐笔委托,逐笔成交}.csv` — **GBK**, Chinese headers, explicit 10-level columns. **7.5k stocks × 2 days.** This is what you teach the pipeline to read. |
| **Cancels** | Embedded per-exchange: **SZ** `逐笔成交.成交代码=='C'` (~22%), **SH** `逐笔委托.委托类型=='D'` (~24%). No separate `逐笔撤单` file. |
| **CB downstream** | `features._cb_features(group, has_cancel_table)` — the `True` branch is **itself still a stub** (returns zero CB values + `cb_available=1.0`). See "Scope note" below. |

---

# Hard rules (auto-DQ if broken)

From LIS §2–§3:

1. **Intraday-only** — read only the **same trading day's** raw L2 per stock; never future days. Reconstructed cancels are
   intraday events. No external data, no validation labels in the frame.
2. **No hard-coding** — the Chinese→canonical column map is a **global constant dict**, not per-stock branching. No
   per-stock-code special cases, no random fill.
3. **No answer-feedback** — never read `outputs/` or leaderboard answers.
4. **Reproducible** — relative paths (`data/<date>/<date>/<stock>/`), `config.RANDOM_SEED` unchanged, **no LLM in the
   inference path**.
5. **Locked labels unchanged** — Track L does not touch `capital_type` / scoring. Validator stays `src/postprocess.py`.

**CB / cancel path (§3 invariant):** the xlsx path has no cancels → `cb_available=0.0`, CB dims vote NEUTRAL. The **local
path (this track)** reconstructs embedded cancels → `cb_available=True` and feeds `features._cb_features`.

---

# What to build

## Goal (LIS §6 Track L)

Read the local per-stock GBK CSVs (`行情`/`逐笔委托`/`逐笔成交`) into the **cleaned frame shape
`ingest._normalise_and_clean` produces**, so the whole downstream pipeline (`aggregate`/`features`/`rules`/...) runs on
**real multi-stock days** — **without touching `load_raw`** (the xlsx path stays intact).

## Files

| Action | Path |
|--------|------|
| Create | `src/ingest_local.py` |
| Create | `tests/test_ingest_local.py` |
| Create | `tests/fixtures/local_l2_tiny/` — a hand-made **≤50-row GBK** sample, **1 stock**, all 3 streams (commit it; tiny) |
| Do NOT modify | `src/ingest.py` `load_raw` / `_normalise_and_clean` (xlsx path) |

## Design contract

- Public entry, e.g. `load_local(root: str, date: str, max_stocks: int | None = None) -> pd.DataFrame` — returns the
  **same cleaned, temporally-sorted columns** `_normalise_and_clean` yields (so downstream is unchanged), concatenated
  across the sampled stocks. `max_stocks` keeps dev/tests bounded — **never** load all 7.5k in a test.
- **Encoding:** `gb18030`. **Path:** doubly-nested `data/<date>/<date>/<stock>/`.
- **Column rename** (global dict; see `data_inventory_report.md` §6): e.g. `成交价`→`price`, `当日累计成交量`→cumulative
  `volume`, `当日成交额`→cumulative `amount`, `叫买总量`→`totalbidvolume`, `叫卖总量`→`totalaskvolume`,
  `加权平均叫买价`→`weightedbidprice`, `加权平均叫卖价`→`weightedaskprice`, `万得代码`→`stock_code`, `自然日`→`transaction_date`.
- **Time:** parse `时间` (`HHMMSSmmm`, Beijing) → `hour`/`minute` **directly** (no UTC round-trip — sidesteps the RS dtype
  bug); build a sortable per-tick timestamp from `自然日`+`时间` for ordering and RS interval diffs.
- **Book:** reshape `申买价/量1..10` + `申卖价/量1..10` → `bids`/`asks` as the list-of-dicts `ingest.parse_book_json`
  yields (`{"price":.., "volume":..}` per level) so OBP/OFI features read them unchanged.
- **Cancels:** SZ `逐笔成交` rows where `成交代码=='C'`; SH `逐笔委托` rows where `委托类型=='D'` → a normalized cancel frame
  (side + order-ref + timestamp); set `has_cancel_table=True` / `cb_available=True`.
- **`bigordervolume`:** derive from large `逐笔成交` prints (it is not a snapshot column).
- **Emit** exactly the columns downstream expects → `aggregate`/`features`/`rules` unchanged.

> **Scope note (flag, don't silently expand):** setting `cb_available=True` flips CB dims from NEUTRAL to *participating*
> in scoring — but `features._cb_features`'s `True` branch currently returns **zero** CB values (it's a stub). So real CB
> *values* (fast-cancel ratio, buy/sell cancel divergence, cancel-interval CV) need that seam implemented too. If wiring
> real CB math makes this session too big, **split**: ship Track L-a (snapshot+orders+trades → real multi-stock matrix,
> `cb_available` flag plumbed) now, and note Track L-b (cancel-feature math in `_cb_features`) as a follow-up in your
> report. Do **not** quietly leave CB values fake while claiming CB is "done."

---

# TDD workflow (one failing test → fail → minimal impl → pass → commit; LIS §6 Track L tasks 1–5)

1. **L.1 Folder discovery** — test (fail first): given `tests/fixtures/local_l2_tiny`, discovery lists the `(date, stock)`
   and finds all three stream files; `max_stocks` caps the count. Implement minimally → pass.
2. **L.2 `行情` read + map + time + book** — test: a tiny `行情` row (gb18030) maps to canonical columns; `hour`/`minute`
   come from `时间`; `bids`/`asks` parse to 10 levels with `price`/`volume`. Implement → pass.
3. **L.3 Cancel reconstruction (per exchange)** — test: a `.SZ` fixture with a `成交代码=='C'` row yields a cancel in the
   normalized frame and `cb_available=True`; a `.SH` fixture with `委托类型=='D'` does the same via `逐笔委托`. Implement → pass.
4. **L.4 `bigordervolume` derivation** — test: large `逐笔成交` prints aggregate into a non-zero `bigordervolume`. Implement → pass.
5. **L.5 End-to-end emit shape** — test: `load_local(...)` on the tiny fixture returns a frame whose columns **⊇** what
   `features.compute_daily_features` needs, temporally sorted, with `cb_available` set. Implement → pass.

**Final checks before done:**
```bash
pytest tests/test_ingest_local.py -q
pytest tests/ -q                                   # full suite stays green (was 37; count may increase)
python main.py --input samples/AFAC2026.xlsx -o outputs/   # xlsx path UNAFFECTED — still emits valid CSVs
# Manual real-data smoke (NOT a committed test — data/ is gitignored):
# python -c "from src.ingest_local import load_local; df=load_local('data','20260611',max_stocks=10); print(df['stock_code'].nunique(), df.shape)"
```

**Commit message (if committing):** `feat: local GBK L2 ingest adapter (Track L) — multi-stock + reconstructed cancels`

---

# Acceptance criteria (Track L only — from LIS §6)

- [ ] The tiny GBK fixture ingests via `load_local`; columns match the `_normalise_and_clean` output shape
- [ ] `cb_available=True` on the local path; cancels reconstructed (SZ `成交代码=='C'` / SH `委托类型=='D'`)
- [ ] CB dims **non-neutral** in scoring on a cancel-bearing stock (structural at minimum; note if real CB *values* are L-b)
- [ ] A **≥10-stock** sample (manual, against `data/`) yields a real cross-sectional matrix (feeds H1 + Track V) — report the number
- [ ] `python main.py --input samples/AFAC2026.xlsx` still works (xlsx path untouched)
- [ ] Full suite green (`pytest tests/ -q`); no new dependencies; no out-of-scope files changed

**Not required this session** (later): Phase 1 normalize, Phase 1b wiring, real `_cb_features` math if you split (Track L-b),
sourcing more days (Track D).

---

# Style

- Match existing `src/` conventions (`from __future__ import annotations`, type hints, minimal diff, module docstring).
- New module only — do **not** entangle `load_raw`.
- Test-first; small commits. Delete throwaway debug scripts.
- On Windows, console Chinese may mojibake — verify on-disk files are correctly encoded (read fixtures with `gb18030`).

---

# When done, report

1. Commands run + pass/fail output (paste counts)
2. Files created/changed (list)
3. Acceptance checklist (checked)
4. **CB scope:** did you wire real `_cb_features` values, or ship L-a and defer L-b? Say which.
5. `≥10-stock` manual smoke result (stock count + matrix shape) or why skipped
6. Anything that contradicted LIS (if none, say so)
7. **Next hint:** what remains (Phase 1b can now run on real data; Track L-b if deferred)

Begin with the first failing test (L.1).
