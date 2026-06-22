# ADDENDUM — Track L-c re-eval (mandatory; read with base prompt)

> **Supersedes** stale sections of [`sonnet-track-l-c-cb-true-latency.md`](sonnet-track-l-c-cb-true-latency.md):
> prerequisites, baseline test count, gate command/input, and "greenfield" scope.
> **Everything else in the base prompt still applies** (join algorithm, minute-boundary TDD,
> unmatched-cancel policy, `CB_KEYS` arity lock, fixture honesty, xlsx path untouched).

---

## Repo state lock (2026-06-22)

| Fact | Value |
|------|-------|
| LIS | **v1.6.0** |
| Head | `d1fc070` (feature B.2 `94ccb90`) |
| Suite | **130 passed** (not 101) |
| V.4 / V.3 / P.1 / B.0 / B.2 | **DONE — do not rebuild** |
| Active gate input | **`parquet:data/202606`** |
| Active gate n | **24** `(stock, day)` keys |
| **Gate baseline (before)** | **weighted_f1 = 0.6599** (post–B.2; 散户 R 5/10, P=0.83) |
| Pre–B.2 reference | weighted_f1 = 0.6094; 散户 R 4/10 |

---

## Prior L-c evaluation (read before coding)

**Parquet path — already implemented (do NOT redo):**

- `src/ingest_parquet.read_cancel_frame_parquet` emits per-cancel **`latency_ms`**
  (OrderID self-join on unified `order` frame, **decoded** `HHMMSSmmm` → real ms, 100% linkage on 委托补全).
- LIS v1.5.7 / `src/features.py` documents the outcome: swapping true latency into
  `cb_fast_cancel_ratio` **regressed** proxy-F1 **0.4917 → 0.4381** on the **n=10** 0618-only slice
  (sub-`CB_FAST_CANCEL_MS` true latency is vanishingly rare; inter-cancel burstiness carries more class signal).
- **Disposition:** inter-cancel **proxy kept**; `latency_ms` infra stays for revisit.

**Local GBK path — not done (your primary implementation scope if shipping a swap):**

- `src/ingest_local.read_cancel_frame` still returns only `side`/`cancel_time`/`cancel_qty`/`time_int`.
- Ref columns exist in rename maps but are **dropped**; no order-frame join; no `latency_ms`.
- Base prompt join algorithm (SZ `ask_seq`/`bid_seq` ↔ `order_no`; SH `exchange_order_no` A↔D) applies here.

---

## Revised mission

1. **Implement true order→cancel latency on the local path** per the base prompt (if not already present):
   extend `read_cancel_frame` → refs + order match + decoded-ms `latency_ms`.
2. **Wire `_cb_features`** so `cb_fast_cancel_ratio` can use true latency **when** `latency_ms` is present
   on the cancel frame (parquet path already has the column — ensure local parity).
3. **Measure on the active gate** — not the stale n=10 / `local:data` baseline:

   ```bash
   conda run -n base --no-capture-output python scripts/validate_offline.py \
     --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
   ```

4. **SHIP only if** weighted_f1 **> 0.6599** on n=24. Flat or down → **FAIL** per LIS §6 Track L disposition;
   revert the swap (keep proxy), report honestly, **do not commit**.

---

## Explicit non-goals

- Re-implementing `read_cancel_frame_parquet` / OrderID self-join (already landed P.1).
- Re-dispatching V.4, V.3, P.1, B.0, B.2.
- Adding `cb_cancel_interval_cv` as a 6th `CB_KEYS` entry (flag LIS contradiction + stop if you believe necessary).
- Wiring `main.py --input data/` or importing `validate_offline` into inference.
- Grid-searching `CB_FAST_CANCEL_MS` against labels (answer-feedback trap) — threshold stays `config.CB_FAST_CANCEL_MS`;
  if true-latency swap fails, you may **flag** re-threshold as a follow-up, not ship it ungated.

---

## Revised Lc.8 — PROXY-F1 GATE

**Before** any `_cb_features` swap, record baseline on **HEAD**:

```bash
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```

Expect **weighted_f1 ≈ 0.6599**, n=24. Paste the exact number.

**After** your change, re-run the same command.

| Outcome | Action |
|---------|--------|
| after **> 0.6599** | PASS — report delta; Opus may commit |
| after **≤ 0.6599** | FAIL — keep inter-cancel proxy; report delta; **no commit** |

Also record per-class P/R/F1 and note whether 散户 recall moved.

---

## Parquet vs local — wiring expectation

`validate_offline` on `parquet:data/202606` uses `ingest_parquet`, not `ingest_local`.
Therefore:

- If you only implement local `latency_ms` but do **not** wire `_cb_features` to consume
  the **existing** parquet `latency_ms` column, the gate will **not move** — that is a FAIL, not a pass on unit tests.
- Preferred seam (match B.2 pattern): compute `latency_ms` in ingest (`ingest_local` / already in `ingest_parquet`);
  `_cb_features` consumes `cancel_df["latency_ms"]` when present, else falls back to inter-cancel proxy.

Document in your report: for the n=24 gate run, what fraction of cancels had matched `latency_ms`, and did
the feature value distribution change vs proxy.

---

## Acceptance addendum (copy into report)

- [ ] Gate baseline recorded: **0.6599** on `parquet:data/202606` n=24 (not 0.4917 / not `local:data` alone)
- [ ] Prior L-c parquet eval acknowledged (0.4917→0.4381 regression reason documented)
- [ ] Local `read_cancel_frame` parity implemented **or** explicitly scoped out with rationale
- [ ] `_cb_features` consumes parquet `latency_ms` when column present (not ignored)
- [ ] Proxy-F1 after **> 0.6599** — or FAIL declared with before→after numbers
- [ ] No re-implementation of parquet OrderID join
- [ ] All base-prompt acceptance items still met (`CB_KEYS`=5, xlsx smoke, absent path, minute-boundary test)

---

## When blocked

If true-latency swap cannot beat **0.6599** after a minimal, correct implementation:

1. State FAIL plainly with before→after F1.
2. Recommend keeping the proxy (LIS disposition).
3. Optionally propose **one** follow-up (e.g. latency-distribution dim, re-threshold study on unlabeled data only)
   — do **not** implement without a new prompt.

---

## Outcome (2026-06-22) — FAIL, not shipped

Re-eval ran. Gate `parquet:data/202606` n=24: **weighted_f1 0.6599 → 0.6500**, 散户 R **5/10 → 4/10**. Only
**0.64%** of 1,018,500 cancels are sub-`CB_FAST_CANCEL_MS` true latency (vs 86.8% proxy-fast) → feature collapses.
Swap **rejected**; `_cb_features` keeps the inter-cancel proxy. Infra retained (`ingest_local` `latency_ms` parity +
xfail minute-boundary tests). See LIS **v1.6.1** §6 Track L-c. Follow-up (re-threshold / latency-distribution) needs
a new prompt — not dispatched.
