# Sonnet execution prompt — Track L-b (real CB feature math)

> **Status:** Ready to run. **LIS v1.5.2** §6 **Track L-b** (follow-up to Track L-a, commit `65116b6`).
> **Prerequisite:** `src/ingest_local.py` reconstructs cancels; `cb_available=1.0` plumbed; `_cb_features` true branch still returns **zeros**.
>
> **Sequential context:** Run **after Phase 1b**. Slot **before Phase 2** per sequencing decision (2026-06-18).

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **Track L-b only** — real Cancel-Behaviour (CB) feature values in `features._cb_features`.

**Read (minimal):**
- `docs/LIS.md` §6 Track L (L-b note) + §3 CB invariant + §4 tick-cancel row
- `src/features.py` (`_cb_features`, `CB_KEYS`), `src/ingest_local.py` (`read_cancel_frame`)
- `tests/fixtures/local_l2_tiny/`, `tests/test_ingest_local.py`, `tests/test_features.py`
- `docs/competition-spec/reference-feature-set.md` (CB family)
- This prompt

**Out of scope:** Phase 2 RS fix, Phase 1b, `main.py` local-corpus wiring (xlsx path must stay intact), Track V V.3/V.4, LIS edits (flag only).

---

# LIS v1.5.2 context (trust these)

| Item | Note for L-b |
|---|---|
| **L-a done** | `read_cancel_frame` returns `side`, `cancel_time`/`time_int`, `cancel_qty` per exchange (SZ from trades `成交代码=='C'`, SH from orders `委托类型=='D'`). **Does not** currently carry order-ref columns (`叫买序号`/`叫卖序号`/`交易所委托号`). |
| **CB_KEYS (code)** | `cb_cancel_order_ratio`, `cb_cancel_volume_ratio`, `cb_fast_cancel_ratio`, `cb_buy_cancel_ratio`, `cb_sell_cancel_ratio` — implement **non-zero** values when `has_cancel_table=True`. |
| **Ref-set extras** | `cb_cancel_interval_cv`, `cb_cancel_amount_ratio` exist in ref-set but are **not** in `CB_KEYS` today — do **not** add keys unless LIS contradicts (flag instead). |
| **Fast cancel — semantics** | True **order→cancel latency** needs matching each cancel to its originating order via ref columns (SZ `叫买/卖序号`, SH `交易所委托号`). `read_cancel_frame` does **not** expose those refs today. |
| **Fast cancel — L-b fallback** | For this session, implement `cb_fast_cancel_ratio` as the share of **consecutive cancel events** whose inter-cancel interval is `< CB_FAST_CANCEL_MS` (from `cancel_time` timestamps). Document in code + report that this is a proxy, not true order→cancel latency. Optional stretch: extend `read_cancel_frame` to retain ref columns and compute true latency if fixture data supports it. |
| **Order-ref join** | Full interval-CV / order-matched fast-cancel is a follow-up if refs are added to `read_cancel_frame`; do not block L-b on it. |
| **Scoring** | `rules.DIMS_YOUZI` uses `cb_sell_cancel_ratio`; `DIMS_QUANT` uses `cb_fast_cancel_ratio` — values must be finite floats in [0,1] where applicable. |
| **Absent path** | `has_cancel_table=False` → zeros + `cb_available=0.0`; keep `tests/test_rules.py::test_absent_cb_dims_vote_neutral` green. |

---

# Hard rules

1. **Intraday-only** — CB stats from same stock-day cancel stream only.
2. **No hard-coding** — no per-stock constants; thresholds in `config.py`.
3. **No answer-feedback** — no leaderboard reads.
4. **xlsx path untouched** — `load_raw` / `main.py` default input unchanged; absent cancel table still degrades gracefully.

---

# What to build

## Goal

Replace the `_cb_features` true-branch stub with real computations from a cancel event frame.

## Plumbing (required — cancel frame must reach `_cb_features`)

Today `ingest_local.load_local` sets `cb_available` but **does not** pass cancel rows to `aggregate`. You must wire cancel data through **one** clean path, e.g.:

- Extend `compute_daily_features(group, has_cancel_table, cancel_df=None)` and `build_feature_matrix(..., cancel_lookup=None)` where `cancel_lookup[(stock_code, date)]` is a cancel DataFrame; **or**
- Attach a per-group cancel summary computed during ingest (minimal, testable).

Use `ingest_local.read_cancel_frame` in tests against `tests/fixtures/local_l2_tiny/`. Do **not** entangle `ingest.load_raw`.

## Feature math (minimum)

For a non-empty cancel frame on a stock-day:

| Key | Suggested definition |
|-----|---------------------|
| `cb_cancel_order_ratio` | cancel count / (cancel count + trade count) or per ref-set semantics |
| `cb_cancel_volume_ratio` | sum(cancel_qty) / (sum(cancel_qty) + sum(order/trade volume)) |
| `cb_fast_cancel_ratio` | **L-b fallback:** share of consecutive cancel pairs with inter-cancel interval `< CB_FAST_CANCEL_MS` (document as proxy; true order→cancel latency needs ref-column extension) |
| `cb_buy_cancel_ratio` | buy-side cancels / total cancels |
| `cb_sell_cancel_ratio` | sell-side cancels / total cancels |

Use `_safe_div`; guard empty denominators → 0.0. All outputs finite floats.

## Files

| Action | Path |
|--------|------|
| Modify | `src/features.py` — `_cb_features` true branch |
| Modify | `src/aggregate.py` — pass cancel data if needed |
| Modify | `config.py` — `CB_FAST_CANCEL_MS` (or similar) if new threshold |
| Modify / create | `tests/test_features.py` — CB tests on synthetic cancel frame + fixture |
| Optional | `src/ingest_local.py` — extend `read_cancel_frame` to carry order-ref columns (only if doing true latency) |
| Do NOT | Break xlsx smoke; do not import `validate` in inference path |

---

# TDD workflow

1. **Lb.1** Write `tests/test_features.py::test_cb_features_nonzero_with_cancel_frame` (**fail first**): synthetic cancel DataFrame with known buy/sell counts and timestamps → assert `cb_fast_cancel_ratio > 0` (or specific hand-computed values using the inter-cancel fallback).
2. **Lb.2** Run → **FAIL** (all CB values 0).
3. **Lb.3** Implement `_cb_features` + plumbing.
4. **Lb.4** Add test on `tests/fixtures/local_l2_tiny/` via `read_cancel_frame` + `compute_daily_features(..., has_cancel_table=True, cancel_df=...)` → non-zero CB keys.
5. **Lb.5** Assert `test_absent_cb_dims_vote_neutral` still passes (xlsx/absent path).
6. **Lb.6** Full suite + xlsx smoke:
   ```bash
   pytest tests/test_features.py -q -k cb
   pytest tests/ -q
   python main.py --input samples/AFAC2026.xlsx -o outputs/
   ```

**Commit message:** `feat: real CB feature math from reconstructed cancels (Track L-b)`

---

# Acceptance criteria (Track L-b only)

- [ ] `_cb_features` true branch returns **non-zero** values on cancel-bearing synthetic + tiny fixture data
- [ ] `has_cancel_table=False` path unchanged (zeros + `cb_available=0.0`)
- [ ] `cb_available` flag behavior unchanged
- [ ] `cb_fast_cancel_ratio` uses documented fallback (inter-cancel interval) unless ref columns were added
- [ ] xlsx smoke green; `load_raw` untouched
- [ ] Full suite green (was 79+; count may increase)
- [ ] No new heavy dependencies

**Not required:** `main.py` `--input data/` wiring (separate future task), true order→cancel latency via order-ref join (document if deferred).

---

# When done, report

1. Commands + counts
2. Files changed
3. Acceptance checklist
4. Hand-computed example for one test
5. Which plumbing path you chose (cancel_lookup vs other)
6. Fast cancel: inter-cancel proxy or true order→cancel latency? Ref columns extended?
7. xlsx smoke `cb_available` (expect False)
8. Phase 2 not started

Begin with Lb.1.
