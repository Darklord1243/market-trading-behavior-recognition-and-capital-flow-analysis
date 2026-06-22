# Sonnet execution prompt — Track L-c (true order→cancel latency)

> **Status:** Ready to run **after V.3 labels exist and V.4 harness is built** — the win is **gated on Track V
> proxy-F1** (a proxy→true swap that does not move the proxy is not worth the added ingest complexity; LIS §6
> Track L note, R1). **LIS v1.5.5** §6 **Track L** (L-c note), follow-up to Track L-b (`87a60a8`).
>
> **Prerequisite state:** `ingest_local.read_cancel_frame` returns only `side`/`cancel_time`/`cancel_qty`/`time_int`;
> `features._cb_features` computes `cb_fast_cancel_ratio` as an **inter-cancel interval proxy** (`CB_FAST_CANCEL_MS=500`).
>
> **Sequencing (Batch 3):** V.3 (human labels) → V.4 (harness) → **L-c (this)**. Do **not** start L-c until the V.4
> harness can print a baseline proxy-F1 on real V.3 labels. See `WORKFLOW.md` Batch 3.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **Track L-c only** — replace the inter-cancel *proxy*
in `cb_fast_cancel_ratio` with **true order→cancel latency**, by extending `read_cancel_frame` to carry order-ref
columns and matching each cancel to its originating order.

**Read (minimal):**
- `docs/LIS.md` §6 **Track L** (L-c note, lines on order-ref join) + §3 CB invariant + §4 `ingest_local.py` row
- `src/ingest_local.py` — `read_cancel_frame`, `TRADE_COL_MAP`, `ORDER_COL_MAP` (the rename maps **already** name the
  ref columns; see context table)
- `src/features.py` — `_cb_features` (true branch), `CB_KEYS`, `compute_daily_features`
- `config.py` — `CB_FAST_CANCEL_MS`
- `tests/fixtures/local_l2_tiny/` (read the `逐笔委托.csv` + `逐笔成交.csv` for both `000001.SZ` and `600000.SH`),
  `tests/test_ingest_local.py`, `tests/test_features.py`
- This prompt

Do **not** re-read the whole doc tree.

**Out of scope this session:** Phase 3 features; `main.py` local-corpus wiring (xlsx path **must** stay intact);
Track V V.3/V.4 implementation (you **consume** the V.4 harness for the gate, you do not build it); adding a 6th
`CB_KEYS` entry unless this prompt explicitly says so; any `docs/LIS.md` edit (flag a contradiction in your report).

---

# LIS v1.5.5 context (trust these locks; do not re-derive)

| Item | Note for L-c |
|---|---|
| **L-b done (`87a60a8`)** | `_cb_features` true branch computes all 5 `CB_KEYS` from the cancel frame; `cb_fast_cancel_ratio` is an **inter-cancel interval proxy** (consecutive `cancel_time` diffs `< CB_FAST_CANCEL_MS`). **This is what L-c replaces.** |
| **`read_cancel_frame` today** | Returns columns `side`, `cancel_time`, `cancel_qty`, `time_int` only. It **slices off** the ref columns even though the rename maps already produce them. |
| **Ref columns already in the rename maps** | `TRADE_COL_MAP` (SZ trades/`逐笔成交`): `叫卖序号→ask_seq`, `叫买序号→bid_seq`, plus `成交代码→trade_code`, `委托代码→side`. `ORDER_COL_MAP` (orders/`逐笔委托`): `委托编号→order_no`, `交易所委托号→exchange_order_no`, `委托类型→order_type` (`A`=add, `D`=cancel), `委托代码→side`. **No new Chinese header parsing is needed — just stop dropping these and read the orders frame too.** |
| **`CB_KEYS` arity** | A **5-tuple** today; `rules.DIMS_QUANT` references `cb_fast_cancel_ratio`. **Recommendation: REDEFINE `cb_fast_cancel_ratio` to use true latency — keep the 5-tuple unchanged.** Do **NOT** add `cb_cancel_interval_cv` as a 6th key in this session (it is a ref-set extra, **not** in `CB_KEYS`; adding it changes matrix width and the L-b contract). If you believe it must be added, **flag the LIS contradiction in your report and stop** — do not change `CB_KEYS` arity unilaterally. |
| **Time unit subtlety (load-bearing)** | `cancel_time`/`time_int` are **`HHMMSSmmm` integers** (e.g. `93002000` = 09:30:02.000). Raw integer subtraction is **not** linear in milliseconds across second/minute/hour boundaries (`93002000 − 92901000 = 101000` as ints, but the true elapsed time is **61000 ms**). The L-b proxy inherits this distortion. **True latency MUST decode `HHMMSSmmm` → real elapsed ms** (`h*3_600_000 + m*60_000 + s*1_000 + ms`) before differencing. This decoding is the heart of the discriminating test. |
| **Absent path** | `has_cancel_table=False` → zeros + `cb_available=0.0`; `tests/test_rules.py::test_absent_cb_dims_vote_neutral` must stay green. The xlsx path passes `cancel_lookup=None` → unaffected. |

---

# Hard rules (auto-DQ if broken)

1. **Intraday-only** — order/cancel matching uses the **same stock-day** streams only; no future/post-close data.
2. **No hard-coding** — no per-stock constants; the fast threshold stays a `config` constant
   (`CB_FAST_CANCEL_MS`, in **real ms** now).
3. **No answer-feedback** — no leaderboard reads. The proxy-F1 gate uses **our** V.3 labels via the V.4 harness.
4. **xlsx path untouched** — `ingest.load_raw` / `main.py` default input unchanged; absent cancel table still
   degrades gracefully (zeros + `cb_available=0.0`).

---

# What to build

## Goal

Make `cb_fast_cancel_ratio` reflect **true order→cancel latency**: extend `read_cancel_frame` to retain the order-ref
columns, read the originating-order frame, match each cancel to its order, compute real elapsed-ms latency, and define
`cb_fast_cancel_ratio` as the share of cancels with latency `< CB_FAST_CANCEL_MS`.

## Join algorithm (per exchange)

> Ground every column name in the rename maps above. Match each cancel to its originating **add** order, then
> `latency_ms = decode_ms(cancel_time) − decode_ms(order_time)` (drop negatives / unmatched).

- **SZ** (`.SZ`): cancels are rows of `逐笔成交.csv` with `trade_code == 'C'`. The cancelled order's sequence is the
  **side-appropriate** ref: `ask_seq` (叫卖序号) for a **sell** cancel, `bid_seq` (叫买序号) for a **buy** cancel
  (the other ref is `0`). Match that sequence to `order_no` (委托编号) in `逐笔委托.csv`; the order's `time_int` is
  the placement time. `latency = cancel.cancel_time − order.time_int` (decoded to ms).
- **SH** (`.SH`): cancels are rows of `逐笔委托.csv` with `order_type == 'D'`. The cancel and its originating **add**
  (`order_type == 'A'`) share the same `exchange_order_no` (交易所委托号). Match cancel→add on `exchange_order_no`;
  `latency = cancel.time_int − add.time_int` (decoded to ms).

**Unmatched cancels** (ref `0`, no partner, or negative latency) are **excluded from the latency numerator AND
denominator** (document this; do not silently count them as slow). If **no** cancel matches, `cb_fast_cancel_ratio`
falls back to `0.0` (finite float, not NaN) and the report notes the fixture/data limitation.

## ⚠️ Fixture reality — read before writing tests (you WILL hit this)

The committed `local_l2_tiny` fixture **does not** cleanly support the SH join or the SZ buy-cancel as-is:
- **SZ `000001.SZ`:** the sell-cancel (`成交代码=C`, `叫卖序号=2`) **does** match order_no 2 (a sell add at
  `92901000`) → true latency ≈ **61 s**. ✅ usable. The buy-cancel has `叫买序号=0` (no ref) → **unmatched**. ❌
- **SH `600000.SH`:** the `D` cancels carry `exchange_order_no` `20003`/`20006`, which **do not** match any `A`
  order (adds are `20001/20002/20004/20005`) → **no SH cancel matches** in the current fixture. ❌

**Therefore:**
1. The **discriminating** red-first test MUST be built on a **synthetic** order+cancel frame you construct in the
   test (full control of refs and minute-boundary timing) — **not** on the raw fixture. This is mandatory to avoid a
   non-discriminating test (Batch 2 lesson: 2/3 tracks had tests that passed on both old and new code).
2. You **MAY** add/repair a small number of fixture rows so a **fixture-level** true-latency test is meaningful: e.g.
   give the SZ buy-cancel a real `叫买序号` pointing at an existing buy `order_no`, and align an SH `D` cancel's
   `exchange_order_no` with an existing `A` order. If you edit the fixture, **document every changed row** in your
   report and keep all existing `tests/test_ingest_local.py` assertions green (or update them deliberately, noting
   why). Prefer **adding** rows over mutating rows other tests assert on.

## Feature math change

In `_cb_features` true branch, replace the inter-cancel-interval block for `cb_fast_cancel_ratio` with:
`cb_fast_cancel_ratio = (count of matched cancels with latency_ms < CB_FAST_CANCEL_MS) / (count of matched cancels)`,
using `_safe_div` (empty denominator → 0.0). The other 4 `CB_KEYS` are **unchanged**. The latency computation may
live in `ingest_local` (returning a per-cancel `latency_ms` column on the extended cancel frame) or in `_cb_features`
— prefer computing `latency_ms` in `ingest_local` (it owns the order frame) and have `_cb_features` consume it, so
`features.py` stays free of file I/O.

## Files

| Action | Path |
|--------|------|
| Modify | `src/ingest_local.py` — extend `read_cancel_frame` to retain ref columns + match to orders → add a `latency_ms` column (and keep the existing `side`/`cancel_time`/`cancel_qty`/`time_int` columns for backward compatibility) |
| Modify | `src/features.py` — `_cb_features` true branch: `cb_fast_cancel_ratio` from `latency_ms < CB_FAST_CANCEL_MS` |
| Modify (maybe) | `config.py` — only if `CB_FAST_CANCEL_MS` semantics/comment need updating (it is now **real ms**, was proxy-ms); do not rename the constant |
| Modify | `tests/test_features.py` and/or `tests/test_ingest_local.py` — synthetic discriminating test + fixture test |
| Modify (optional) | `tests/fixtures/local_l2_tiny/.../{逐笔委托,逐笔成交}.csv` — repair/add rows for a meaningful fixture join (document changes) |
| Do NOT | Break the xlsx smoke; change `CB_KEYS` arity; wire `main.py --input data/`; import `validate`/`scripts` into the inference path |

---

# TDD workflow (red-first, discriminating)

1. **Lc.1** Write `tests/test_features.py::test_fast_cancel_uses_true_latency_not_inter_cancel` (**fail first**).
   Construct a synthetic orders frame + cancel frame where the **proxy and the truth disagree** — specifically use a
   **minute boundary**: e.g. an order placed at `92959800` (09:29:59.800) cancelled at `93000050` (09:30:00.050) →
   true latency = **250 ms** (< 500 → *fast*), while the L-b proxy's raw-int / inter-cancel handling classifies it
   differently. Pair it with a genuinely-slow matched cancel (latency ≫ 500 ms). Assert the **true-latency**
   `cb_fast_cancel_ratio` (e.g. `== 0.5` for one fast of two matched). Run → **FAIL** under the current proxy code.
   > Self-check: if you reverted L-c, would this test FAIL? It must. A test that passes on both proxy and true
   > latency is non-discriminating — redesign it (cross a minute boundary; that is where raw-int subtraction breaks).
2. **Lc.2** Run → **FAIL**.
3. **Lc.3** Extend `read_cancel_frame` (retain refs, read order frame, compute `latency_ms` with **decoded ms**) +
   update `_cb_features`. Run → pass.
4. **Lc.4** `test_unmatched_cancels_excluded`: a cancel with ref `0` / no partner is dropped from numerator **and**
   denominator (not counted slow). Run → pass.
5. **Lc.5** Fixture test on `local_l2_tiny`: after any documented fixture repair, `read_cancel_frame('…/000001.SZ', '000001.SZ')`
   exposes `latency_ms` and the SZ sell-cancel shows ≈ 61 s (so it is **not** fast); assert `cb_fast_cancel_ratio`
   accordingly. Add the SH case if you repaired it. Run → pass.
6. **Lc.6** Regression: `tests/test_rules.py::test_absent_cb_dims_vote_neutral` green; existing
   `tests/test_ingest_local.py` cancel-frame assertions green (or deliberately updated with rationale).
7. **Lc.7** Full suite + xlsx smoke:
   ```bash
   pytest tests/test_features.py -q -k cb
   pytest tests/test_ingest_local.py -q
   pytest tests/test_rules.py::test_absent_cb_dims_vote_neutral -q
   pytest tests/ -q
   python main.py --input samples/AFAC2026.xlsx -o outputs/   # cb_available=False expected
   ```
8. **Lc.8 — PROXY-F1 GATE (the win condition).** With V.3 labels seeded, run the V.4 harness **before** (on the
   proxy commit / `HEAD~`) and **after** this change:
   ```bash
   python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:data
   ```
   Record `weighted_f1` before → after. **GATE:** if the proxy→true swap **does not move** the proxy F1 (or moves it
   the wrong way) on a real multi-stock sample, this is **FAIL** per the LIS disposition — report it and recommend
   keeping the proxy (do **not** ship added ingest complexity for no measured gain). If V.3 labels are **not** ready,
   L-c is **blocked** — stop and report (do not ship an unmeasured swap).

**Commit message (if committing, and only on a measured F1 improvement):**
`feat: true order→cancel latency for cb_fast_cancel_ratio (Track L-c)`

---

# Acceptance criteria (Track L-c only — copy into your report)

- [ ] `read_cancel_frame` retains ref columns (`ask_seq`/`bid_seq` for SZ, `exchange_order_no` for SH) and exposes a
      finite `latency_ms` per matched cancel; backward-compatible `side`/`cancel_time`/`cancel_qty`/`time_int` kept
- [ ] `cb_fast_cancel_ratio` = share of **matched** cancels with **decoded-ms** latency `< CB_FAST_CANCEL_MS`
- [ ] Unmatched cancels excluded from numerator **and** denominator (documented)
- [ ] `HHMMSSmmm` decoded to real elapsed ms (minute-boundary correct) — the discriminating test proves it
- [ ] `CB_KEYS` arity **unchanged** (5 keys); `cb_cancel_interval_cv` **not** added (or LIS contradiction flagged + stopped)
- [ ] Other 4 CB keys unchanged; `has_cancel_table=False` path unchanged (zeros + `cb_available=0.0`)
- [ ] xlsx smoke green (`cb_available=False`); `load_raw` untouched; `main.py` not wired to local path
- [ ] Full suite green (baseline **101**; count may increase)
- [ ] **Proxy-F1 before→after recorded** via the V.4 harness on V.3 labels; ships **only** if F1 moved up
- [ ] No new heavy dependencies

**Not required this session:** `cb_cancel_interval_cv`; `main.py --input data/` wiring; Phase 3 features.

---

# Honest limitations (state these in your report)

- **Fixture is synthetic and partial** — the committed `local_l2_tiny` SH cancels and the SZ buy-cancel do not
  cleanly join without repair; the *real* multi-stock corpus is the true test bed (via the V.4 harness on real days).
- **Minute/hour boundary** is exactly where the proxy and true latency diverge — call out any rows near session
  edges (09:30, 11:30, 13:00, 15:00) and the lunch break, where elapsed-time semantics matter most.
- **Ref-matching coverage** — some cancels may have no recoverable originating order (partial L2, ref `0`); report
  the matched-fraction so the reader knows how much of the cancel stream the true-latency feature actually covers.
- **Gate honesty** — a real proxy-F1 that does not move means L-c is not worth shipping yet; say so plainly rather
  than declaring victory on green unit tests alone (LIS §6 Track L disposition).

---

# Style

- Match existing `src/` conventions (`from __future__ import annotations`, type hints, minimal diff). Put a one-line
  decode helper (`HHMMSSmmm → ms`) where it reads naturally; do not scatter the formula.
- Test-first; small commits. Delete throwaway debug scripts.
- On Windows, console Chinese may mojibake — the fixture CSVs are **gb18030**; read them with `encoding="gb18030"`
  (as `ingest_local` already does). Verify on-disk, not by eyeballing the console.

---

# When done, report

1. Commands run + pass/fail output (paste counts)
2. Files changed (list) — and **every** fixture row you added/repaired, with before/after
3. Acceptance checklist (checked)
4. Hand-computed latency for the synthetic discriminating test (show the minute-boundary math)
5. Where `latency_ms` is computed (`ingest_local` vs `_cb_features`) and why
6. Matched-fraction of cancels on the fixture (and on real data if you ran the harness)
7. **Proxy-F1 before → after** (V.4 harness on V.3 labels) — or "BLOCKED: V.3 labels not ready" / "FAIL: F1 did not move"
8. xlsx smoke `cb_available` (expect False); confirm `CB_KEYS` arity unchanged
9. Anything that contradicted LIS (if none, say so)

Begin with the first failing test (Lc.1) — and make it cross a minute boundary.
