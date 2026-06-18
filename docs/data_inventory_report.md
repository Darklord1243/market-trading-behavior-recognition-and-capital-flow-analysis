# Local L2 Data Inventory & Gap Analysis

> **Generated:** 2026-06-16 · by read-only inspection of `data/` (gitignored, ~102 GB).
> **Reproduce:** `python scripts/inspect_local_l2.py --date 20260611 --stock 000001.SZ`
> **Feeds:** LIS §4 data-inventory, R3, Track D. Updates landed in LIS **v1.4**.

## TL;DR (the headline)

The local corpus is **far richer than the official n=1 snapshot fixture** and **overturns the
"cancel data is structurally missing" premise** for our own data:

- **~7,574 stocks × 2 trading days** (20260611, 20260612) — a real market cross-section, not 1 stock.
- Each (date, stock) has **three streams**: `行情` (10-level snapshot), `逐笔委托` (order-by-order),
  `逐笔成交` (trades).
- **Cancellations ARE present** — reconstructable **without buying anything** — but encoded
  **per-exchange**: SZSE in `逐笔成交` (`成交代码=='C'`, ~22%), SSE in `逐笔委托` (`委托类型=='D'`, ~24%).
- **Catch:** the format (per-stock GBK CSVs, Chinese headers, explicit 10-level columns) is **not what
  `src/ingest.load_raw` reads** (xlsx, English headers, nested `bids`/`asks` JSON). An **adapter** is the
  one real blocker — a tracked follow-up phase, not a purchase.

---

## 1. Directory layout (verified)

```
data/
  20260611/20260611/<stock_code>/{行情.csv, 逐笔委托.csv, 逐笔成交.csv}
  20260612/20260612/<stock_code>/{行情.csv, 逐笔委托.csv, 逐笔成交.csv}
```

Note the **doubly-nested date** (`data/<date>/<date>/...`). Stock codes carry exchange suffixes
(`000001.SZ`, `600000.SH`). No `逐笔撤单.csv` exists anywhere (a recursive scan of 20260611 found **0**) —
cancels live **inside** the order/trade streams (§4), not in a dedicated file.

## 2. Coverage

| Date | Stocks | SZ | SH | BJ | Streams/stock |
|---|---|---|---|---|---|
| 20260611 | **7,574** | 5,262 | 2,312 | 0 | 3 (行情/委托/成交) |
| 20260612 | **7,580** | — | — | 0 | 3 |

Both dates fall inside the **A-board window** (2026/06/09–07/10). No 北交所 (`.BJ`) names.

## 3. Stream schemas (from `000001.SZ`, 20260611)

| Stream | Cols | Rows | Size | Header (decoded from GBK) |
|---|---|---|---|---|
| `行情` (snapshot) | **66** | 4,826 | 2.0 MB | 万得代码, 交易所代码, 自然日, **时间**, 成交价, 成交量, 成交额, 成交笔数, IOPV, 成交标志, BS标志, 当日累计成交量, 当日成交额, 最高/最低/开盘价, 前收盘, **申卖价1..10, 申卖量1..10, 申买价1..10, 申买量1..10**, 加权平均叫卖价, 加权平均叫买价, 叫卖总量, 叫买总量, 不加权指数, 品种总数, 上涨/下跌/持平品种数 |
| `逐笔委托` (orders) | **10** | 139,161 | 8.3 MB | 万得代码, 交易所代码, 自然日, 时间, 委托编号, 交易所委托号, **委托类型**, 委托代码(B/S), 委托价格, 委托数量 |
| `逐笔成交` (trades) | **12** | 125,541 | 9.3 MB | 万得代码, 交易所代码, 自然日, 时间, 成交编号, **成交代码**, 委托代码, BS标志, 成交价格, 成交数量, 叫卖序号, 叫买序号 |

- **Encoding:** GBK family (`gb18030` decodes cleanly). **Not** UTF-8.
- **Time:** `时间` is a Beijing-local `HHMMSSmmm` integer (e.g. `91500000` = 09:15:00.000). This is a
  **direct Beijing clock** — the adapter sidesteps the UTC-epoch→Beijing conversion (and the RS dtype bug)
  that the xlsx path wrestles with.
- **Book:** 10 levels are **explicit columns** (`申买价/量1..10`), not nested JSON — the adapter must
  either reshape them into the `bids`/`asks` list-of-dicts `ingest.parse_book_json` expects, or add an
  explicit-column feature path.
- Snapshot starts at the **09:15 call auction** (price/volume 0 until first print).

## 4. Cancellations — the key finding (exchange-aware)

A separate `逐笔撤单` file does **not** exist, but cancels are embedded and countable:

| Exchange | Stream | Flag column | Cancel value | Example | Cancel ratio |
|---|---|---|---|---|---|
| **SZSE (`.SZ`)** | `逐笔成交` | `成交代码` | **`C`** (vs `0`=成交) | `000001.SZ`: 27,774 / 125,541 | **22.1%** |
| **SSE (`.SH`)** | `逐笔委托` | `委托类型` | **`D`** (Delete; `A`=Add) | `600000.SH`: 18,291 / 74,924 | **24.4%** |

This is enough to build the full **CB family** (fast-cancel ratio, buy/sell cancel divergence,
cancel-interval CV): the cancel records carry side and an order reference (`叫买/卖序号` on SZ;
`交易所委托号` on SH) to link back to the original order's timestamp.

> **`ingest.CANCEL_TABLE_HINT_COLS` will NOT fire on this data** — those hint columns
> (`cancelvolume`, `canceltime`, …) are English-snapshot-schema artifacts. Local cancels are detected by
> the **exchange-specific flag** above. The detector needs an adapter-aware branch (§6).

## 5. Gap analysis vs LIS §4 data-inventory

| LIS §4 stream | Old status | **Reality (local data)** | New status |
|---|---|---|---|
| 10-level snapshot | ✅ have (fixture, n=1) | ✅ **7,574 stocks × 2 days**, 66-col explicit book | ✅ **upgraded** |
| tick-trade | 🟡 thin / verify | ✅ **real 逐笔成交**, ~125k rows/stock | ✅ **have** |
| tick-cancel | ⛔ **missing** | 🟡 **present but not wired** (embedded, per-exchange) | 🟡 **available, adapter-gated** |
| tick-order (order-level) | ⛔ missing | ✅ **real 逐笔委托**, ~139k rows/stock | ✅ **have** |

**Net:** every ⛔ in the v1.3 inventory is actually **present on disk**. The blocker moved from
*"we don't have the data"* to *"the pipeline can't read this format yet."*

## 6. The one real blocker — ingest adapter (proposed follow-up phase)

`src/ingest.load_raw` reads **xlsx with English headers + JSON book**; the corpus is **per-stock GBK CSV
with Chinese headers + explicit 10-level columns**. This is **not a 1-line change** → documented as a
tracked phase in LIS (not implemented in this pass).

**Minimal adapter sketch** (`src/ingest_local.py`, new — does not touch `load_raw`):

1. **Discover** `data/<date>/<date>/<stock>/` folders; iterate stock-days (sampling flag for dev).
2. **Read `行情`** (gb18030) → rename Chinese→canonical (`成交价`→`price`, `成交量`→`volume`,
   `当日累计成交量`→cumulative `volume`, `叫买总量`→`totalbidvolume`, `加权平均叫买价`→`weightedbidprice`, …);
   parse `时间` → Beijing `hour`/`minute` directly; reshape `申买价/量1..10` → `bids`/`asks` JSON.
3. **Reconstruct cancels** per §4 into a normalized cancel frame, set `cb_available=True`; feed the real
   `features._cb_features` branch.
4. **Emit** the same cleaned frame shape `_normalise_and_clean` produces, so everything downstream
   (`aggregate`/`features`/`rules`/...) is unchanged.

**Acceptance (when built, TDD):** a tiny GBK CSV fixture (≤50 rows, 1 stock) ingests; `cb_available=True`;
CB dims become non-neutral; matrix has ≥10 real stock rows on a multi-stock sample. Suite green.

## 7. Significance — what this unblocks (no purchase needed)

| Workstream | Before (fixture) | After (local data + adapter) |
|---|---|---|
| **Track V** (validation) | n=1; synthetic panels only | **real ~7,500-stock cross-section** to compute proxy-F1 against hand labels |
| **H1 / Phase 1** (normalize) | degenerate (1 row → all 0.5) | **real cross-sectional ranks** — the seam finally does its job |
| **Phase 2** (RS cadence) | bug-artifact `cv` on snapshot | **true order/trade timestamps** for real interval CV / burst |
| **Phase 3** (OFI/AP/PD) | snapshot-limited | **order-level** PD, AP runs, iceberg `rs_split_*` now computable |
| **Track D** (CB) | "buy cancel data" | **already have cancels** — build the adapter, skip the purchase |

## 8. Honest caveats / still missing

- **Adapter is required** before any of §7 is real — until then the pipeline still runs only on the xlsx fixture.
- **Only 2 days.** Good for a cross-section and CB, thin for multi-day model training (Phase 4) or
  time-series generalization. More days still warrant procurement (Track D guide).
- **No fundamentals** (market-cap/sector) here → H6 neutralization needs an external join.
- **`bigordervolume`** is not a snapshot column; derive it from `逐笔成交` (large prints) in the adapter.
- **Provenance:** keep a record of how this corpus was sourced — the §5.5 top-15 audit checks reproducibility.
- Cancel **side-linking** (cancel → original order time) needs the order-ref join; straightforward but must be
  built and tested, not assumed.

## 9. Reproduce / extend

```bash
python scripts/inspect_local_l2.py --date 20260611 --stock 000001.SZ      # one SZ stock (full counts)
python scripts/inspect_local_l2.py --date 20260611 --stock 600000.SH      # one SH stock (cancel via 委托)
python scripts/inspect_local_l2.py --date 20260611 --max-stocks 20 --sample-only   # fast multi-stock peek
python scripts/inspect_local_l2.py --date 20260612 --coverage             # counts only
```

The script is **read-only** (never writes under `data/`); `--out <path>` dumps a small JSON summary
elsewhere for committing.
