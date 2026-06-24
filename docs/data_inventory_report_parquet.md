# New L2 Parquet Corpus — Inventory & Gap Report (`data/202606/`)

> **Generated:** 2026-06-19 · read-only inspection of `data/202606/` (gitignored, large).
> **Reproduce:** `conda run -n base python scripts/inspect_parquet_l2.py --all`
> (sub-flags: `--tree --schema --universe --samples --cancels`).
> **Seller spec:** `level2数据说明_简.txt` (repo root). **Old corpus ref:** `docs/data_inventory_report.md`,
> `src/ingest_local.py`. **Sample day inspected:** `20260618` (the only day shipped so far).

## TL;DR

The new pack is a **market-wide, single-day, English-schema parquet corpus** — structurally the
opposite of the old per-stock **GBK-CSV** corpus. It is **richer and easier to consume**, with three
upgrades that matter for our pipeline:

1. **Single-table cancels for both exchanges.** The maintained `order` (委托补全) table carries cancels
   (`OrderType ∈ {-1,-11}`) for **SZ *and* SH** — no per-exchange branching, no `deal` join.
2. **True order→cancel latency is recoverable from `order` alone.** **100%** of cancel rows share their
   `OrderID` with the original add row (verified on `000001.SZ` and `600000.SH`). This unblocks **Track L-c**
   (true latency) that the old corpus could only proxy.
3. **Order-book detail is deeper:** snapshot ships per-level **order counts** (`AskOrder1..10`,
   `BidOrder1..10`) and weighted bid/ask prices — fields the old 66-col CSV lacked.

The cost: an **ingest adapter** is still required (English columns, `×100` integer prices, suffix-less
integer `SecuCode`, market-wide files needing pre-filtering). It is a **new module**, not a tweak to
`ingest_local`. **Universe coverage is 99/100** of the competition `stock-samples.xlsx`.

**Go/no-go: GO** — sufficient for the competition pipeline once a parquet adapter is built (see §8).

---

## 1. Directory & file contract

```
data/202606/
  十盘档口/20260618/            # snapshot (10-level book)
      snapshot_20260618.parquet            2,158,800,927 B  (~2.01 GB)
      snapshot_20260618/                   5,188 per-stock CSVs
          snapshot_20260618_000001.csv … snapshot_20260618_689009.csv
  逐笔成交/20260618/            # deal (tick trades, incl. SZ cancels)
      deal_20260618.parquet                3,694,172,897 B  (~3.44 GB)
      deal_20260618/                       5,188 per-stock CSVs
  逐笔委托/20260618/            # order_raw (raw orders, incl. SH cancels)
      order_raw_20260618.parquet           3,871,257,955 B  (~3.61 GB)
      order_raw_20260618/                  5,188 per-stock CSVs
  委托补全/20260618/            # order (completed/unified order book) ★
      order_20260618.parquet               3,511,248,972 B  (~3.27 GB)
      order_20260618/                      5,188 per-stock CSVs
  指数/20260618/               # index
      index_20260618.parquet                 102,605,935 B  (~98 MB)
      index_20260618.csv                     122,487,375 B  (~117 MB)   # single flat CSV, no subfolder
```

- **Naming pattern:** `<stream>_<YYYYMMDD>.parquet` and a sibling folder `<stream>_<YYYYMMDD>/`
  holding one CSV per stock: `<stream>_<YYYYMMDD>_<SecuCode6>.csv` (SecuCode zero-padded to 6 digits,
  **no exchange suffix**: `…_000001.csv`, `…_600000.csv`).
- **One trading day only** (`20260618`). Each stream folder has exactly one date subdir. (Old corpus had a
  doubly-nested `data/<date>/<date>/<stock>/…`; this layout is `data/202606/<stream-CN>/<date>/…`.)
- **CSV vs parquet — duplicate, not different.** Per-stock CSVs are the parquet **filtered to one stock**:
  identical columns and values (minus the parquet-only pandas artifact `__index_level_0__`). Both are
  **UTF-8 with English headers** — *not* GBK/Chinese like the old corpus.
- ⚠ **Snapshot CSV column order differs by exchange.** `000001`'s header begins
  `TickTime,SecuCode,TotalDealNum,TotalVolume,TotalTurnover,Price,…` while `600000`'s begins
  `TickTime,SecuCode,Price,TotalDealNum,…`. **Read CSVs by header name, never by position.** (The parquet
  is uniform — prefer it.)
- **The index is the only stream with no per-stock CSV subfolder** (one flat `index_…csv`).

## 2. Schema per stream (from `20260618` parquet metadata + sampled rows)

Common to all tick streams: `SecuCode` (int), `TradingDay` (int `20260618`), `Channel`/`BizIndex`
(exchange routing/seq, label-only). **All prices are integers = real price ×100** (seller §3) → divide by
100 (e.g. `AskPrice1=1071` ⇒ `10.71`; deal `Price=920` ⇒ `9.20`).

### snapshot — `十盘档口` · 21,586,607 rows · 5,188 codes · 76 cols
Per-level book is **flat columns**, not nested JSON:
`AskPrice1..10, AskVolume1..10, AskOrder1..10, BidPrice1..10, BidVolume1..10, BidOrder1..10`
(`*Price` int32 ×100; `*Volume`/`*Order` float). Plus
`TickTime` (int), `TickTimeDiff` (int, seconds since prev tick), `Price` (last, ×100), `DealNum`,
`Volume`, `Turnover` (per-tick), `TotalDealNum/TotalVolume/TotalTurnover` (cumulative, double),
`TotalBidVolume/TotalAskVolume`, `WeightBidPrice/WeightAskPrice` (vol-weighted, ×100).
- **Time field:** `TickTime` = `HHMMSSmmm` integer (e.g. `91500000` = 09:15:00.000). Day starts at the
  **09:15 call auction**; pre-open rows have `Price=0`.
- **Sample (`000001.SZ`, first tick `91500000`):** `AskPrice1=1071 (10.71)`, `AskVolume1=54843`,
  `BidPrice1=1071`, `BidVolume1=54843`, all `AskOrder*=0` (auction phase).
- **Sample (`600000.SH`, `91402000`):** all book levels 0 until first SH print (SH auction publishes later).

### deal — `逐笔成交` · 212,109,896 rows · 12 cols
`Channel, DealID, BuyID, SellID, SecuCode, Price(×100,int32), Volume(float), DealTime(HHMMSSmmm,int32),
TradingDay, Side(int8), BizIndex`.
- `BuyID`/`SellID` → the `OrderID` in `order_raw`/`order` (order-ref join key).
- **`Side` ∈ {0: active buy, 1: active sell, -1: buy cancel, -11: sell cancel}** (seller §5). SZ cancels
  live here; SH cancels do **not** (see §3).
- **Sample (`600000.SH` first trade):** `DealTime=92501510`, `Price=920 (9.20)`, `Volume=1600`, `Side=0`.
- **Sample (`000001.SZ`):** opens with `Side=-1`, `Price=0`, `Volume=100` — SZ auction-window cancels.

### order_raw — `逐笔委托` · 267,230,310 rows · 11 cols
`Channel, OrderID, SecuCode, Price(×100), Volume, OrderTime(HHMMSSmmm), OrderType(int8), TradingDay,
BizIndex, DBOrderID`.
- **`OrderType` is exchange-specific** (seller §5):
  - **SH:** `{0: 委买, 10: 委卖, -1: 撤买, -11: 撤卖}` — SH cancels **are** here; SH market orders are **not**.
  - **SZ:** `{1: 市价买, 2: 限价买, 3: 本方最优买, 11: 市价卖, 12: 限价卖, 13: 本方最优卖}` — SZ cancels
    **not** here.
- **Sample (`000001.SZ`):** `OrderType=2` (限价买), `Price=970 (9.70)`. **(`600000.SH`):** `OrderType=0`, `Price=1016`.

### order — `委托补全` (the unified/completed book) ★ · 341,494,990 rows · 12 cols
Same as `order_raw` **plus `LastPrice`** (last trade price at order time, ×100); all int columns widened to
**int64**. This is `order_raw` **+ the per-exchange missing pieces folded in** (seller §1–2):
SZ cancels (from `deal`) and SH market orders (from `deal`).
- **`OrderType` superset:** SH `{0,10,-1,-11}` ∪ SZ `{1,2,3,11,12,13,-1,-11}` — i.e. **cancels `{-1,-11}`
  present for *both* exchanges.**
- **Sample (`000001.SZ`):** `OrderType=2, Price=970, LastPrice=1074, OrderID=1`.

### index — `指数` · 2,930,501 rows · 13 cols
`SecuCode(int64, index code), SeqNo, TickTime, OpenPrice, HighPrice, LowPrice, ClosePrice,
PrevClosePrice, CumVolume, CumTurnover, Volume, Turnover` (all double; OHLC **not** ×100 — already real).
- **`SecuCode` here is an index code, a separate namespace** (e.g. `1`=SSE Composite ~4106, `300`, `510`,
  `680/681`). **Do not map index `SecuCode` to a stock.**
- **`TickTime` here is `HHMMSS`** (6-digit, e.g. `91500`) — **no milliseconds**, unlike the tick streams.

### `SecuCode` → pipeline `stock_code`
`SecuCode` is a **bare integer with leading zeros stripped and no exchange suffix** (`1`, `600000`,
`689009`). Map to canonical `NNNNNN.XX`:
```python
code6 = str(secu).zfill(6)
exch = ("SZ" if secu < 400000
        else "BJ" if (400000<=secu<500000 or 800000<=secu<900000 or 920000<=secu<930000)
        else "SH")          # >=500000 non-BJ: 51x ETF, 6xx, 688/689 STAR, 90x B
stock_code = f"{code6}.{exch}"   # 1 -> 000001.SZ ; 600000 -> 600000.SH ; 688981 -> 688981.SH
```

## 3. Cancel recoverability (critical for Track L-c)

Measured over the full day (vectorized scan, `scripts/inspect_parquet_l2.py --cancels`):

| Stream | Cancel encoding | Overall cancel % | SZ % | SH % |
|---|---|---|---|---|
| `deal` | `Side ∈ {-1,-11}` | **17.77%** | **27.75%** | **0.00%** |
| `order_raw` | `OrderType ∈ {-1,-11}` | **12.62%** | **0.00%** | **28.88%** |
| `order` (补全) | `OrderType ∈ {-1,-11}` | **20.91%** | **20.03%** | **21.99%** |

**Reconciliation (proves the maintained table is complete):**
- SZ cancel rows in `deal` = **37,701,246** = SZ cancel rows in `order` (exact match) → `order` absorbed
  every SZ `deal` cancel.
- SH cancel rows in `order_raw` = **33,713,342** = SH cancel rows in `order` (exact match) → `order`
  absorbed every SH `order_raw` cancel.
- `order` SZ row total exceeds `order_raw` SZ by exactly 37,701,246 (the added SZ cancels); `order` SH total
  exceeds `order_raw` SH by 36,563,434 (the added SH **market** orders).

**`order` (委托补全) is sufficient *alone*** for the entire CB family **and** for true latency:
- **CB** (cancel/order ratio, cancel/volume ratio, buy/sell cancel split): `OrderType {-1,-11}` + `Volume`
  give all of it for both exchanges, one table, no branching, **no `deal` join**.
- **True order→cancel latency (Track L-c):** **100%** of `order` cancel rows share their `OrderID` with the
  original add row — verified `000001.SZ` (26,822/26,822) and `600000.SH` (18,411/18,411). Latency =
  `cancel.OrderTime − add.OrderTime`, computed by **self-join on `OrderID` within `order`** after converting
  `HHMMSSmmm`→ms-of-day. **No order-ref columns and no cross-stream join required.**

**Old-corpus `OrderType` distribution sanity (order, full day):**
`2:77.0M, 12:73.2M, 0:62.2M, 10:57.4M, -1:36.7M, -11:34.7M, 11:206k, 1:122k, 13:24.6k, 3:8.5k`.

**Versus old corpus** (`成交代码=='C'` SZ ~22% / `委托类型=='D'` SH ~24%, two streams, GBK letters):
the new pack replaces letter flags with **signed integers** and, crucially, **unifies both exchanges into
`order`** with full `OrderID` linkage — strictly easier and strictly more capable.

## 4. Snapshot / book depth

- **10 full levels confirmed**, both sides, with **three quantities per level**: price, volume, **and order
  count** (`*Order1..10`) — the order-count fields are new vs the old corpus.
- **Price scale ÷100** confirmed on real rows (`AskPrice1=1071`→10.71; `WeightBidPrice` same scale).
  `AskOrder*` was `0` everywhere in auction samples — expect non-zero in continuous session (per seller §7c,
  order-count is provided since 2019-06-05).
- **Mapping to `ingest_local` canonical columns:** the flat `AskPrice{i}/AskVolume{i}` (and
  `BidPrice{i}/BidVolume{i}`) reshape directly into the `bids`/`asks` list-of-dicts JSON
  (`[{"price":…,"volume":…}, …]`) that `_make_book_json` already emits — same idea as the CSV adapter, but
  source columns are **already English** (no `HQ_COL_MAP` rename) and **integer ×100** (divide before
  emitting). `TotalBidVolume/TotalAskVolume/WeightBidPrice/WeightAskPrice` map 1:1 to
  `totalbidvolume/totalaskvolume/weightedbidprice/weightedaskprice`. Cumulative `TotalVolume/TotalTurnover`
  → `.diff().clip(lower=0)` for per-tick, exactly as the existing baseline contract does.

## 5. Gap analysis vs pipeline

| LIS need | Old CSV path | New parquet path | Adapter work |
|---|---|---|---|
| **Snapshot features** (OBP/PI/OFI/OSS) | `行情.csv` GBK, 66-col flat book, Chinese headers | `snapshot_*.parquet` English, flat 10-lvl + order counts, int×100 | Read parquet (filtered), ÷100 prices, reshape levels→`bids/asks`, cumulative→tick diff. **No Chinese rename.** |
| **CB (cancel) family** | SZ `成交代码='C'` (`逐笔成交`) + SH `委托类型='D'` (`逐笔委托`), two streams, per-exchange branch | `order.OrderType ∈ {-1,-11}` — **one stream, both exchanges** | Map `OrderType`→cancel/side; `Volume`→cancel qty. Single branch. |
| **Order→cancel latency (L-c)** | needs order-ref join (SZ 叫买/卖序号, SH 交易所委托号) — proxy only | `order` **self-join on `OrderID`** (100% linkage) | Parse `OrderTime` HHMMSSmmm→ms; group by `OrderID`; subtract. |
| **RS / PD order-level** | `逐笔委托.csv` ~139k/stk | `order_raw` / `order` (`OrderTime`, `OrderType`, `Price`, `Volume`, `OrderID`) | Real ms timestamps from `OrderTime`; PD/iceberg from order stream. |
| **OSS / big-order** | derive from `逐笔成交` large prints | `deal.Volume` large prints (`Side ∈ {0,1}`), threshold = `OSS_THRESHOLDS["large"]` | Filter real trades (exclude `Side<0`), aggregate per stock-day. |
| **Index context (H6-ish)** | absent | `index_*.parquet` (OHLC + cum vol/turnover, intraday) | Optional join on index code for market-state features. |

Reference: this satisfies every box in `docs/human_guides/track_d_l2_procurement.md` §4 checklist
(all three streams ✓, cancels recoverable 15–30% ✓, 10 levels ✓, intraday HHMMSSmmm 09:15→close ✓,
encoding decodes ✓ (UTF-8), universe overlap ✓ §7, both exchanges ✓).

## 6. Performance & ingestion strategy (recommendation only)

Single-day footprint is large: **~13.3 GB parquet** (≈ same again in CSV mirrors), tick streams **212M–341M
rows each**. **Never `pd.read_parquet()` a whole stream.** Recommended:

1. **Filter before load.** Use `pyarrow.dataset(...).to_table(filter=ds.field("SecuCode")==code, columns=[…])`
   (or `pd.read_parquet(path, filters=[("SecuCode","in",keys)], columns=[…])`). The parquet has 200–326 row
   groups, so predicate + column pushdown is cheap.
2. **Drive by the labeled key set / `samples/stock-samples.xlsx`** (100 stocks) — load only those `SecuCode`s,
   not all 5,188.
3. **Per-stock CSV subfolders are a fine fallback** for one-stock work (a CSV is the parquet pre-filtered),
   but for many stocks the filtered parquet read is faster and avoids the SZ/SH column-order CSV pitfall.
4. For repeated runs, **the seller recommends a DB load** (spec §6); a per-stock parquet re-partition
   (`…/SecuCode=NNNNNN/…`) would also localize reads.

**One stock-day row counts (measured):**

| Stream | `000001.SZ` | `600000.SH` | both | market-wide avg /stock |
|---|---|---|---|---|
| snapshot | 4,951 | 5,032 | 9,983 | ~4,161 |
| deal | 123,213 | 58,268 | 181,481 | ~40,884 |
| order_raw | 133,699 | 77,060 | 210,759 | ~51,510 |
| order | 160,521 | 100,122 | 260,643 | ~65,824 |

So a 2-stock-day slice is **~0.66M rows** — trivial once filtered, vs **~842M rows** if you load all four
tick streams whole.

## 7. Competition / compliance

- **Universe overlap (measured):** new pack covers **99/100** of `samples/stock-samples.xlsx`
  (the competition universe; only `603721` absent on 20260618 — likely halted that day),
  **19/19** of `samples/pattern_reco.csv`, and **197/198** stock targets in `samples/predict_result.csv`
  (only `688143` absent). Coverage is effectively complete for the competition.
- **Provenance note template (save with the pack for the audit):**
  > Source: purchased A-share L2 history pack, parquet. Streams: snapshot(十档)/deal(逐笔成交)/
  > order_raw(逐笔委托)/order(委托补全)/index. Day(s): 20260618. Universe: 5,188 SecuCode
  > (SZ 2,783 / SH 2,306 / BJ 99). Prices ×100, unadjusted (复权乘数 separate). Vendor / purchase date /
  > license: «fill in». Verified 2026-06-19 via `scripts/inspect_parquet_l2.py`.
- **No blocker vs competition L2 requirements:** all four canonical streams present, both exchanges,
  cancels intact (not stripped), 10-level book, intraday timestamps — meets the procurement-guide bar.
  The **only gap is days** (one day shipped; Phase-4 model training wants more — §8).

## 8. Proposed follow-up tracks (no implementation here)

- **New module `src/ingest_parquet.py` (recommended) vs extending `ingest_local.py`.** Prefer a **sibling
  module**: the schemas barely overlap (English vs Chinese headers, parquet filter-read vs CSV-per-stock,
  unified `order` cancels vs split SZ/SH, int×100 prices). It should emit the **same cleaned frame contract**
  `ingest_local.load_local` produces (so aggregate→features→rules consume it unchanged) and set
  `cb_available=1.0` whenever `order` cancels exist. Reuse `_make_book_json` / cumulative→tick logic;
  do **not** touch `load_raw` or `ingest_local`.
- **`inspect_local_l2.py` `--root data/202606` mode:** the layout/encoding differ enough that bolting a mode
  on is awkward; `scripts/inspect_parquet_l2.py` (added here) is the cleaner home — keep them separate.
- **`validate_offline.py --input local:data`:** add a `parquet:data/202606` (or `local2:`) input scheme that
  routes to `ingest_parquet`, so Track V can compute proxy-F1 on this real cross-section.
- **Track L-c (true latency) is now genuinely unblocked** by the 100% `OrderID` linkage in `order` — the
  sibling prompt `sonnet-track-l-c-cb-true-latency.md` should target the parquet `order` self-join, not the
  old order-ref columns.

---

### Reproduce / extend
```bash
conda run -n base python scripts/inspect_parquet_l2.py --tree --schema --universe   # layout + schema + universe
conda run -n base python scripts/inspect_parquet_l2.py --samples                     # 1 SZ + 1 SH rows/stream
conda run -n base python scripts/inspect_parquet_l2.py --cancels                     # per-exchange cancel ratios
conda run -n base python scripts/inspect_parquet_l2.py --all                         # everything (UTF-8 JSON)
```
The script is **read-only** (never writes under `data/`); SecuCode-filtered reads keep memory bounded.
