"""Tests for src/ingest_parquet.py — Track P.1 parquet L2 ingest adapter.

The adapter consumes the new English-schema parquet corpus (data/202606/) and
emits the **same cleaned-frame contract** as ingest_local.load_local, so the
downstream pipeline (aggregate → features → rules) runs unchanged.

Fixtures are tiny parquet files written at test time into tmp dirs (the real
13 GB corpus is gitignored), in the real column schema so the adapter exercises
the actual parquet read path.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from src import ingest_parquet

_DATE = "20260618"

_HARNESS_PATH = Path(__file__).parent.parent / "scripts" / "validate_offline.py"


def _import_harness():
    spec = importlib.util.spec_from_file_location("validate_offline", _HARNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Stream folder (Chinese) ↔ file prefix, mirroring data/202606/ layout.
_STREAM_DIR = {
    "snapshot": "十盘档口",
    "deal": "逐笔成交",
    "order": "委托补全",
}


def _write_parquet(root, stream, rows):
    """Write rows (list of dicts) to <root>/<CN>/<DATE>/<stream>_<DATE>.parquet."""
    d = os.path.join(root, _STREAM_DIR[stream], _DATE)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{stream}_{_DATE}.parquet")
    pd.DataFrame(rows).to_parquet(path, engine="pyarrow", index=False)
    return path


def _snap_row(secu, ticktime, price, totvol, totturn, ap1, av1, bp1, bv1,
              tav, tbv, wap, wbp):
    return dict(
        SecuCode=secu, TradingDay=int(_DATE), TickTime=ticktime, Price=price,
        TotalVolume=float(totvol), TotalTurnover=float(totturn),
        TotalAskVolume=float(tav), TotalBidVolume=float(tbv),
        WeightAskPrice=wap, WeightBidPrice=wbp,
        AskPrice1=ap1, AskVolume1=float(av1), BidPrice1=bp1, BidVolume1=float(bv1),
    )


def _order_row(secu, oid, otype, otime, price, vol, last):
    return dict(SecuCode=secu, OrderID=oid, OrderType=otype, OrderTime=otime,
                Price=price, Volume=float(vol), LastPrice=last,
                TradingDay=int(_DATE), Channel=1, BizIndex=oid, DBOrderID=oid)


def _deal_row(secu, side, vol, dtime, price):
    return dict(SecuCode=secu, Side=side, Volume=float(vol), DealTime=dtime,
                Price=price, TradingDay=int(_DATE), Channel=1, DealID=0,
                BuyID=0, SellID=0, BizIndex=0)


def write_tiny_parquet(root):
    """Write a tiny but real-schema corpus: SZ SecuCode 1 + SH SecuCode 600000."""
    # --- snapshot ---
    _write_parquet(root, "snapshot", [
        # SZ 000001 — 3 ticks, cumulative TotalVolume 1000→1500→1800
        _snap_row(1, 93000000, 1000, 1000, 1000000, 1001, 500, 999, 400, 5000, 4000, 1002, 998),
        _snap_row(1, 93001000, 1010, 1500, 1505000, 1011, 300, 1009, 600, 5200, 4300, 1012, 1008),
        _snap_row(1, 93002000, 1005, 1800, 1806000, 1006, 350, 1004, 550, 5100, 4200, 1006, 1004),
        # SH 600000 — 1 tick
        _snap_row(600000, 93000000, 2000, 500, 1000000, 2001, 100, 1999, 100, 900, 800, 2001, 1999),
    ])
    # --- order (委托补全): cancels OrderType ∈ {-1,-11} for BOTH exchanges ---
    _write_parquet(root, "order", [
        _order_row(1, 1, 2, 93000000, 999, 100, 1000),    # add buy
        _order_row(1, 2, 12, 93000100, 1001, 200, 1000),  # add sell
        _order_row(1, 1, -1, 93000500, 999, 100, 1000),   # buy cancel  -> side B
        _order_row(1, 2, -11, 93000800, 1001, 200, 1000), # sell cancel -> side S
        _order_row(1, 3, 2, 93001000, 1000, 150, 1010),   # add buy
        _order_row(1, 3, -1, 93001050, 1000, 150, 1010),  # buy cancel  -> side B
        _order_row(600000, 10, -11, 93000300, 2001, 50, 2000),  # SH sell cancel (from order!)
        # SecuCode 2 — Track L-c true-latency cases (matched self-join + minute boundary + unmatched)
        _order_row(2, 100, 2, 93000000, 1000, 100, 1000),   # add  @ 09:30:00.000
        _order_row(2, 100, -1, 93000500, 1000, 100, 1000),  # cancel @ 09:30:00.500 -> true 500ms
        _order_row(2, 101, 2, 93059950, 1000, 100, 1000),   # add  @ 09:30:59.950
        _order_row(2, 101, -1, 93100050, 1000, 100, 1000),  # cancel @ 09:31:00.050 -> true 100ms (raw int diff 40100!)
        _order_row(2, 999, -11, 93002000, 1000, 100, 1000), # UNMATCHED cancel (no add OrderID 999)
    ])
    # --- deal (逐笔成交): bigorder from Side ∈ {0,1} large prints ---
    _write_parquet(root, "deal", [
        _deal_row(1, 1, 100, 93000500, 1000),     # small sell
        _deal_row(1, -1, 999999, 93000600, 1000), # a cancel — MUST be excluded from bigorder
        _deal_row(1, 0, 20000, 93001500, 1005),   # big buy (≥ 10000)
        _deal_row(600000, 0, 100, 93000400, 2000),
    ])
    return root


# ---------------------------------------------------------------------------
# P1.1 — SecuCode (bare int) → canonical NNNNNN.XX stock_code
# ---------------------------------------------------------------------------

def test_secu_to_stock_code_maps_exchanges():
    """Bare integer SecuCode maps to zero-padded code + correct exchange suffix.

    Per data_inventory_report_parquet.md §2:
      SZ if <400000 ; BJ for 400000–499999 / 800000–899999 / 920000–929999 ;
      else SH (incl. 51x ETF, 6xx, 688/689 STAR, 90x B).
    """
    assert ingest_parquet.secu_to_stock_code(1) == "000001.SZ"
    assert ingest_parquet.secu_to_stock_code(2856) == "002856.SZ"
    assert ingest_parquet.secu_to_stock_code(301563) == "301563.SZ"
    assert ingest_parquet.secu_to_stock_code(600000) == "600000.SH"
    assert ingest_parquet.secu_to_stock_code(603271) == "603271.SH"
    assert ingest_parquet.secu_to_stock_code(688981) == "688981.SH"
    assert ingest_parquet.secu_to_stock_code(430047) == "430047.BJ"
    assert ingest_parquet.secu_to_stock_code(830799) == "830799.BJ"
    assert ingest_parquet.secu_to_stock_code(920819) == "920819.BJ"


def test_stock_code_to_secu_roundtrips():
    """stock_code_to_secu is the inverse of secu_to_stock_code (suffix-agnostic int)."""
    for secu in (1, 2856, 301563, 600000, 603271, 688981, 430047):
        code = ingest_parquet.secu_to_stock_code(secu)
        assert ingest_parquet.stock_code_to_secu(code) == secu


# ---------------------------------------------------------------------------
# P1.2 — load_parquet emits the ingest_local.load_local cleaned-frame contract
# ---------------------------------------------------------------------------

# Every column ingest_local.load_local guarantees downstream consumers.
_CONTRACT_COLS = {
    "stock_code", "transaction_date", "price", "volume", "amount",
    "tick_volume", "tick_amount", "hour", "minute", "datetime_utc",
    "price_change", "bids", "asks", "totalbidvolume", "totalaskvolume",
    "weightedaskprice", "weightedbidprice", "cb_available", "tick_bigordervolume",
}


def test_load_parquet_emits_cleaned_contract(tmp_path):
    """load_parquet on the tiny corpus emits every contract column with ×100-decoded
    prices, reshaped book JSON, cumulative→tick volume, and cb_available=1.0."""
    root = write_tiny_parquet(str(tmp_path))
    df = ingest_parquet.load_parquet(root, _DATE, keys=["000001.SZ"])

    assert not df.empty
    assert _CONTRACT_COLS.issubset(set(df.columns)), \
        f"missing: {_CONTRACT_COLS - set(df.columns)}"
    assert (df["stock_code"] == "000001.SZ").all()
    assert (df["transaction_date"].astype(str) == _DATE).all()

    # ×100 price decode: 1000/1010/1005 → 10.00/10.10/10.05
    assert list(df["price"].round(2)) == [10.00, 10.10, 10.05]
    # cumulative TotalVolume 1000→1500→1800 → tick_volume 0/500/300
    assert list(df["tick_volume"]) == [0.0, 500.0, 300.0]
    # weighted prices ×100-decoded
    assert df["weightedbidprice"].iloc[0] == pytest.approx(9.98)

    # book JSON parses and is ×100-decoded (bid level 1 of first row = 9.99 @ 400)
    bids0 = json.loads(df["bids"].iloc[0])
    assert bids0[0]["price"] == pytest.approx(9.99)
    assert bids0[0]["volume"] == pytest.approx(400.0)

    # cancels exist in `order` → cb_available flagged
    assert (df["cb_available"] == 1.0).all()
    # bigorder from deal: only the 20000 Side=0 print (cancel Side=-1 excluded)
    assert df["tick_bigordervolume"].sum() == pytest.approx(20000.0)


def test_load_parquet_key_filter_excludes_other_stocks(tmp_path):
    """keys= restricts the load to the requested stock(s) only."""
    root = write_tiny_parquet(str(tmp_path))
    df = ingest_parquet.load_parquet(root, _DATE, keys=["600000.SH"])
    assert set(df["stock_code"].unique()) == {"600000.SH"}


# ---------------------------------------------------------------------------
# P1.3 — read_cancel_frame_parquet from unified `order` (both exchanges)
# ---------------------------------------------------------------------------

def test_read_cancel_frame_parquet_sz(tmp_path):
    """SZ cancels from order.OrderType {-1,-11}: -1→B, -11→S, with qty + time."""
    root = write_tiny_parquet(str(tmp_path))
    c = ingest_parquet.read_cancel_frame_parquet(root, _DATE, "000001.SZ")

    assert set(["side", "cancel_time", "cancel_qty", "time_int"]).issubset(c.columns)
    assert len(c) == 3                                   # two -1 + one -11
    side = c["side"].tolist()
    assert side.count("B") == 2 and side.count("S") == 1  # -1→B, -11→S (not reversed)
    assert c["cancel_qty"].sum() == pytest.approx(450.0)  # 100 + 200 + 150
    assert set(c["cancel_time"]) == {93000500, 93000800, 93001050}


def test_read_cancel_frame_parquet_sh_from_order(tmp_path):
    """SH cancels are recoverable from the SAME `order` table (unification point)."""
    root = write_tiny_parquet(str(tmp_path))
    c = ingest_parquet.read_cancel_frame_parquet(root, _DATE, "600000.SH")
    assert len(c) == 1
    assert c["side"].iloc[0] == "S"          # OrderType -11
    assert c["cancel_qty"].iloc[0] == pytest.approx(50.0)


def test_read_cancel_frame_parquet_feeds_cb_features(tmp_path):
    """The parquet cancel frame is consumed unchanged by features._cb_features."""
    from src.features import _cb_features

    root = write_tiny_parquet(str(tmp_path))
    cancel_df = ingest_parquet.read_cancel_frame_parquet(root, _DATE, "000001.SZ")
    group = ingest_parquet.load_parquet(root, _DATE, keys=["000001.SZ"])

    out = _cb_features(group, has_cancel_table=True, cancel_df=cancel_df)
    assert out["cb_available"] == 1.0
    # buy/sell cancel split: 2 buy / 1 sell of 3
    assert out["cb_buy_cancel_ratio"] == pytest.approx(2 / 3)
    assert out["cb_sell_cancel_ratio"] == pytest.approx(1 / 3)
    # all CB outputs finite floats in [0,1]
    for k in ("cb_cancel_order_ratio", "cb_cancel_volume_ratio", "cb_fast_cancel_ratio"):
        assert 0.0 <= out[k] <= 1.0


# ---------------------------------------------------------------------------
# P1.4 — validate_offline `parquet:<root>` input scheme routes to ingest_parquet
# ---------------------------------------------------------------------------

def test_validate_offline_parquet_scheme_scores_keys(tmp_path):
    """`--input parquet:<root>` runs the parquet pipeline on the labeled keys and
    returns a real proxy-F1 result (n >= 1), not a file-not-found skip."""
    harness = _import_harness()
    root = write_tiny_parquet(str(tmp_path))

    truth = pd.DataFrame({
        "stock_code":        ["000001.SZ", "600000.SH"],
        "transaction_date":  [_DATE, _DATE],
        "capital_type":      ["游资", "散户"],
        "capital_intention": ["买入", "卖出"],
        "source":            ["https://s1", "https://s2"],
        "confidence":        [0.8, 0.6],
        "notes":             ["n1", "n2"],
    })

    result = harness.predict_for_keys(filtered_truth=truth, input_source=f"parquet:{root}")

    assert isinstance(result, dict)
    assert "weighted_f1" in result and "n" in result
    assert result["n"] >= 1, f"expected parquet pipeline to score >=1 key, got n={result['n']}"


# ---------------------------------------------------------------------------
# L-c — true order→cancel latency via OrderID self-join (decoded ms)
# ---------------------------------------------------------------------------

def test_cancel_frame_carries_true_latency_ms(tmp_path):
    """read_cancel_frame_parquet adds latency_ms = decoded(cancel) - decoded(add) ms,
    matched on OrderID; unmatched cancels get NaN; minute boundaries are correct."""
    root = write_tiny_parquet(str(tmp_path))
    c = ingest_parquet.read_cancel_frame_parquet(root, _DATE, "000002.SZ")

    assert "latency_ms" in c.columns
    lat = dict(zip(c["cancel_time"], c["latency_ms"]))

    # OrderID 100: 09:30:00.500 − 09:30:00.000 = 500 ms
    assert lat[93000500] == pytest.approx(500.0)
    # OrderID 101 crosses the minute: 09:31:00.050 − 09:30:59.950 = 100 ms.
    # A naïve raw-int subtraction would give 93100050 − 93059950 = 40100 (WRONG).
    assert lat[93100050] == pytest.approx(100.0)
    assert lat[93100050] != pytest.approx(40100.0)
    # OrderID 999 has no matching add → unmatched → NaN
    assert pd.isna(lat[93002000])


# NOTE: Track L-c true-latency swap was EVALUATED and REJECTED — twice.
# Prior eval (n=10 / 0618-seed): proxy-F1 0.4917 → 0.4381. Re-eval (n=24 /
# parquet:data/202606, post-B.2): weighted_f1 0.6599 → 0.6500, 散户 R 5/10 → 4/10.
# Mechanism: genuine sub-CB_FAST_CANCEL_MS latency is vanishingly rare (0.64% of
# cancels) while the inter-cancel-burstiness proxy (~86.8% fast) carries stronger
# class signal. Disposition: _cb_features keeps the inter-cancel proxy; the true
# per-cancel `latency_ms` (asserted above, and the ingest_local parity) is RETAINED
# as dormant infra for a future re-thresholded / latency-distribution feature, but
# is NOT consumed by _cb_features. See docs/LIS.md §6 Track L-c re-eval note.


# ---------------------------------------------------------------------------
# A — measurement fix: normalize labeled keys against a real universe panel
# (not just the cherry-picked labeled set) — but still SCORE only labeled keys.
# ---------------------------------------------------------------------------

def test_load_universe_codes_reads_codes(tmp_path):
    """_load_universe_codes reads stock codes from a CSV/xlsx (股票代码 or stock_code)."""
    harness = _import_harness()
    p = tmp_path / "univ.csv"
    pd.DataFrame({"股票代码": ["000001.SZ", "600000.SH"]}).to_csv(p, index=False, encoding="utf-8")
    assert set(harness._load_universe_codes(str(p))) == {"000001.SZ", "600000.SH"}


def test_build_parquet_matrix_uses_union_panel(tmp_path):
    """The feature matrix is built over (labeled ∪ universe) so rank-normalization
    sees a realistic panel, not only the labeled keys."""
    harness = _import_harness()
    root = write_tiny_parquet(str(tmp_path))
    m = harness._build_parquet_matrix(root, _DATE, ["000001.SZ"], ["000001.SZ", "600000.SH"])
    codes = {(i[0] if isinstance(i, tuple) else i) for i in m.index}
    assert codes == {"000001.SZ", "600000.SH"}, f"panel should include universe, got {codes}"


def test_predict_parquet_norm_universe_excludes_universe_from_output(tmp_path):
    """With a norm_universe, the extra stocks shape normalization but are NOT scored —
    output is restricted to the labeled keys."""
    harness = _import_harness()
    root = write_tiny_parquet(str(tmp_path))
    truth = pd.DataFrame({
        "stock_code": ["000001.SZ"], "transaction_date": [_DATE],
        "capital_type": ["游资"], "capital_intention": ["买入"],
        "source": ["https://s"], "confidence": [0.8], "notes": ["n"],
    })
    preds = harness._predict_parquet(truth, root, norm_universe=["600000.SH"])
    assert set(preds["stock_code"].astype(str)) == {"000001.SZ"}


# ---------------------------------------------------------------------------
# B.2 — deal_size_maps / read_deal_sizes_parquet tests (TDD: written before impl)
# ---------------------------------------------------------------------------

def test_deal_size_maps_keeps_genuine_prints(tmp_path):
    """Side in {0,1} kept; other Side excluded; per-secu volume lists returned.

    Fixture deal rows for SecuCode 1:
      Side=1, Volume=100   -> genuine
      Side=-1, Volume=999999 -> cancel -> excluded
      Side=0, Volume=20000 -> genuine
    Expected genuine volumes for secu 1: [100.0, 20000.0] (order may vary)
    """
    from src.ingest_parquet import _deal_size_maps
    root = write_tiny_parquet(str(tmp_path))
    maps = _deal_size_maps(root, _DATE, [1])
    assert 1 in maps
    assert sorted(maps[1]) == [100.0, 20000.0]


def test_read_deal_sizes_parquet_returns_lookup(tmp_path):
    """read_deal_sizes_parquet returns {(code, date): [volumes]} for genuine prints."""
    from src.ingest_parquet import read_deal_sizes_parquet
    root = write_tiny_parquet(str(tmp_path))
    lk = read_deal_sizes_parquet(root, _DATE, ["000001.SZ"])
    assert ("000001.SZ", _DATE) in lk
    assert all(v > 0 for v in lk[("000001.SZ", _DATE)])


def test_read_deal_sizes_parquet_missing_stock_is_empty(tmp_path):
    """A stock with no genuine prints maps to an empty list."""
    from src.ingest_parquet import read_deal_sizes_parquet
    root = write_tiny_parquet(str(tmp_path))
    # 000002.SZ has no deal rows with Side in {0,1} in the fixture
    lk = read_deal_sizes_parquet(root, _DATE, ["000002.SZ"])
    assert lk[("000002.SZ", _DATE)] == []


# ---------------------------------------------------------------------------
# P3.3 — read_deal_times_parquet / read_order_times_parquet (TDD: before impl)
# ---------------------------------------------------------------------------

def test_read_deal_times_parquet_returns_genuine_times(tmp_path):
    """Genuine deal prints (Side∈{0,1}, vol>0) → their DealTime ints; cancels excluded.

    Fixture deal rows for SecuCode 1:
      Side=1,  Volume=100,    DealTime=93000500 -> genuine
      Side=-1, Volume=999999, DealTime=93000600 -> cancel -> excluded
      Side=0,  Volume=20000,  DealTime=93001500 -> genuine
    """
    from src.ingest_parquet import read_deal_times_parquet
    root = write_tiny_parquet(str(tmp_path))
    lk = read_deal_times_parquet(root, _DATE, ["000001.SZ"])
    assert sorted(lk[("000001.SZ", _DATE)]) == [93000500, 93001500]


def test_read_deal_times_parquet_missing_stock_is_empty(tmp_path):
    """A stock with no genuine deal prints maps to an empty list."""
    from src.ingest_parquet import read_deal_times_parquet
    root = write_tiny_parquet(str(tmp_path))
    lk = read_deal_times_parquet(root, _DATE, ["000002.SZ"])
    assert lk[("000002.SZ", _DATE)] == []


def test_read_order_times_parquet_returns_event_times(tmp_path):
    """All order events for a stock → their OrderTime ints (adds + cancels).

    SecuCode 1 order rows (OrderTime): 93000000, 93000100, 93000500, 93000800,
    93001000, 93001050.
    """
    from src.ingest_parquet import read_order_times_parquet
    root = write_tiny_parquet(str(tmp_path))
    lk = read_order_times_parquet(root, _DATE, ["000001.SZ"])
    assert sorted(lk[("000001.SZ", _DATE)]) == [
        93000000, 93000100, 93000500, 93000800, 93001000, 93001050,
    ]


def test_read_order_times_parquet_missing_stock_is_empty(tmp_path):
    """A stock with no order rows maps to an empty list."""
    from src.ingest_parquet import read_order_times_parquet
    root = write_tiny_parquet(str(tmp_path))
    lk = read_order_times_parquet(root, _DATE, ["000003.SZ"])   # not in fixture
    assert lk[("000003.SZ", _DATE)] == []


# ---------------------------------------------------------------------------
# Slice 5C — read_cancel_frames_parquet: ONE batch `order` read for all keys,
# per-stock slices byte-identical to per-stock read_cancel_frame_parquet.
# (gate perf: kills the 91%-of-runtime per-stock order rescans.)
# ---------------------------------------------------------------------------

def test_read_cancel_frames_parquet_matches_single(tmp_path):
    """The batch cancel lookup is byte-identical, per stock, to the per-stock read.

    This is the parity contract the whole slice rests on: capital/intention gates
    must be unchanged, so every frame the batch path returns must .equals() the
    frame the existing single-stock read_cancel_frame_parquet returns.
    """
    from src.ingest_parquet import (
        read_cancel_frame_parquet,
        read_cancel_frames_parquet,
    )
    root = write_tiny_parquet(str(tmp_path))
    codes = ["000001.SZ", "000002.SZ", "600000.SH"]

    batch = read_cancel_frames_parquet(root, _DATE, codes)

    for code in codes:
        single = read_cancel_frame_parquet(root, _DATE, code)
        assert (code, _DATE) in batch, f"missing {code} in batch lookup"
        got = batch[(code, _DATE)]
        assert got.equals(single), (
            f"batch cancel frame for {code} differs from single read\n"
            f"batch=\n{got}\nsingle=\n{single}"
        )


def test_read_cancel_frames_parquet_missing_stock_is_empty(tmp_path):
    """A requested stock with no cancels (or no order rows) maps to an empty frame
    carrying the cancel-frame column contract — same as the single read."""
    from src.ingest_parquet import (
        _CANCEL_EMPTY_COLS,
        read_cancel_frame_parquet,
        read_cancel_frames_parquet,
    )
    root = write_tiny_parquet(str(tmp_path))
    lk = read_cancel_frames_parquet(root, _DATE, ["000003.SZ"])  # not in fixture
    got = lk[("000003.SZ", _DATE)]
    assert got.empty
    assert list(got.columns) == _CANCEL_EMPTY_COLS
    assert got.equals(read_cancel_frame_parquet(root, _DATE, "000003.SZ"))


# ---------------------------------------------------------------------------
# Slice 5C.1 — capital-gate harness (_build_parquet_matrix) wires the batch
# cancel read: ONE read_cancel_frames_parquet call replaces the per-stock loop,
# byte-identical to the old per-stock read_cancel_frame_parquet loop.
# ---------------------------------------------------------------------------

def test_build_parquet_matrix_batches_cancel_reads(tmp_path, monkeypatch):
    """The gate harness builds cancel_lookup with ONE batch order read, and the
    lookup it wires into aggregate.build_feature_matrix is byte-identical to the
    old per-stock read_cancel_frame_parquet loop (frozen-gate parity contract).
    """
    harness = _import_harness()
    root = write_tiny_parquet(str(tmp_path))
    labeled, universe = ["000001.SZ"], ["000001.SZ", "600000.SH"]
    panel = harness._panel_keys(labeled, universe)

    from src import aggregate, ingest_parquet

    # Spy 1: count batch cancel reads (0 before the slice, exactly 1 after).
    calls = {"batch": 0}
    real_batch = ingest_parquet.read_cancel_frames_parquet

    def spy_batch(*a, **k):
        calls["batch"] += 1
        return real_batch(*a, **k)

    monkeypatch.setattr(ingest_parquet, "read_cancel_frames_parquet", spy_batch)

    # Spy 2: capture the cancel_lookup actually wired into the feature matrix.
    captured = {}
    real_bfm = aggregate.build_feature_matrix

    def spy_bfm(df, **kwargs):
        captured["cancel_lookup"] = kwargs.get("cancel_lookup")
        return real_bfm(df, **kwargs)

    monkeypatch.setattr(aggregate, "build_feature_matrix", spy_bfm)

    harness._build_parquet_matrix(root, _DATE, labeled, universe)

    # Wiring: exactly one batch order read replaces the per-stock rescan loop.
    assert calls["batch"] == 1, f"expected 1 batch cancel read, got {calls['batch']}"

    # Byte parity: harness cancel_lookup == old per-stock read_cancel_frame_parquet loop.
    reference = {
        (code, _DATE): ingest_parquet.read_cancel_frame_parquet(root, _DATE, code)
        for code in panel
    }
    got = captured["cancel_lookup"]
    assert set(got) == set(reference), f"key set differs: {set(got) ^ set(reference)}"
    for key in reference:
        assert got[key].equals(reference[key]), f"cancel frame mismatch for {key}"
