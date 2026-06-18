# Human Guide — Track D: L2 data, what we have, and what (if anything) to buy

> **Headline:** the local corpus under `data/` **already contains tick orders, tick trades, and
> reconstructable cancellations** for ~7,574 stocks × 2 days. **You do not need to buy cancel data to unblock
> CB.** The blocker is an **ingest adapter**, not a purchase. This guide covers (a) verifying what a data pack
> contains, and (b) sourcing *more days* if/when we want them.
>
> **Evidence:** `docs/data_inventory_report.md` · **Spec:** LIS §6 *Track D*, §4 inventory, R3

## 1. What the competition's L2 universe consists of

A-share Level-2 has four canonical streams (spec §II, `topic-specifications-and-data`):

| Stream (CN) | English | Carries |
|---|---|---|
| 十档快照 / 行情 | 10-level snapshot | best±10 prices/volumes, totals, weighted prices, cumulative vol/amt |
| 逐笔委托 | order-by-order | every order: side, price, qty, type (**SSE cancels = `委托类型 D`**) |
| 逐笔成交 | tick trades | every fill (**SZSE cancels = `成交代码 C`**) |
| 逐笔撤单 | tick cancels | *(often absent as a file — cancels are embedded above)* |

## 2. What our pipeline needs

| Need | Code seam | Status |
|---|---|---|
| Snapshot features (OBP/PI/OFI/OSS) | `src/features._*_features` | ✅ logic exists; needs the adapter to feed it real rows |
| Cancel features (CB) | `src/features._cb_features` `has_cancel_table` branch + `ingest.detect_cancel_table` | 🟡 seam exists; **cancels available locally**, detector needs an adapter-aware branch |
| Order-level (RS cadence, PD, iceberg) | `src/features` RS/PD | 🟡 data present (`逐笔委托`), not yet wired |

## 3. Local data status (verified 2026-06-16)

| Stream | Present locally? | Cancels |
|---|---|---|
| 行情 (snapshot, 66-col, 10-level) | ✅ 7,574 stk × 2 days | — |
| 逐笔委托 (orders) | ✅ ~139k rows/stk | **SSE cancels here** (`委托类型=='D'`, ~24%) |
| 逐笔成交 (trades) | ✅ ~125k rows/stk | **SZSE cancels here** (`成交代码=='C'`, ~22%) |
| 逐笔撤单 (separate file) | ❌ none found | not needed — embedded above |

➡ **CB is unblockable with the data we already hold.** The only work is the **adapter** (read GBK
per-stock CSVs → pipeline schema + reconstruct cancels). See `docs/data_inventory_report.md` §6 and the
LIS adapter phase. **No purchase required for these 2 days.**

## 4. Checklist — evaluating ANY L2 pack (local folder or a vendor's)

Run the inspector first: `python scripts/inspect_local_l2.py --date <YYYYMMDD> --stock <code>`

- [ ] **All three streams** present per stock (snapshot + orders + trades)?
- [ ] **Cancels recoverable?** SZ → `逐笔成交.成交代码` has `C`; SH → `逐笔委托.委托类型` has `D`. Ratio
      plausibly **15–30%** (near-zero ⇒ cancels stripped — a red flag).
- [ ] **10 full book levels** in the snapshot (`申买价/量1..10`), not just best-bid/ask?
- [ ] **Time** is intraday-resolved (`HHMMSSmmm`), covers **09:15 auction → 15:00 close**?
- [ ] **Encoding** decodes (`gb18030`/`gbk`/`utf-8-sig`)?
- [ ] **Universe overlap** with the Tianchi stock list (`samples/stock-samples.xlsx`)?
- [ ] **Both exchanges** (`.SZ` and `.SH`) covered if the target universe spans both?
- [ ] **Provenance recorded** (where/when sourced) — the §5.5 top-15 audit checks reproducibility & licensing.

## 5. Where to source MORE days (when we want them)

Per spec §II, contestants self-source L2 (organizer provides only the stock list):

| Channel | Notes |
|---|---|
| **淘宝 / 闲鱼** (Taobao/Xianyu) | Common A-share L2 tick vendors; specify 逐笔委托+逐笔成交+十档, both exchanges, date range |
| **百度网盘** shares | Bulk historical L2 packs |
| **Tianchi stock list** | `samples/stock-samples.xlsx` — the universe to request |
| Licensed APIs | Wind / 聚宽 / 迅投QMT etc. if the team has access |

**When buying, demand:** all three streams, **cancels not stripped**, 10-level book, both exchanges, GBK or
documented encoding, and a license note we can cite in the audit.

## 6. If a pack is snapshot-only (no orders/trades — the fallback)

Some cheap packs ship **snapshot only**. Then:

- CB dims **stay neutral** (already enforced — `tests/test_rules.py::test_absent_cb_dims_vote_neutral`); never
  let them tilt a class.
- RS cadence degrades to snapshot resolution (the known fragile path); lean on OFI/OSS/PI instead.
- Flag it: such a pack does **not** unblock CB — don't pay extra for it expecting cancel features.

## 7. Acceptance — "Track D is unblocked" means

- [ ] Adapter ingests a real stock-day → `cb_available=True`.
- [ ] CB dims become **non-zero / non-neutral** on a cancel-bearing stock (add a present-path test).
- [ ] A **≥10-stock** sample produces a real cross-sectional matrix (feeds H1 / Track V).
- [ ] Sourcing/provenance note saved for the audit.

## 8. What you (human) must decide

1. **Now:** nothing to buy — approve building the **ingest adapter** (engineering) to use the 2 local days.
2. **Soon:** decide whether to **source more days** (Phase-4 model training & generalization want >2 days).
   For just CB + a cross-section, the 2 local days already suffice.
