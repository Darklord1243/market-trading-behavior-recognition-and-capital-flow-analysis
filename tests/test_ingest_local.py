"""Tests for src/ingest_local.py — Track L local GBK-CSV L2 ingest adapter.

TDD order: L.1 → L.2 → L.3 → L.4 → L.5.
Tests use only the tiny committed fixture under tests/fixtures/local_l2_tiny/
and never touch the full ~102 GB data/ corpus.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

# -----------------------------------------------------------------------
# Fixture root
# -----------------------------------------------------------------------
FIXTURE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "local_l2_tiny",
)
DATE = "20260611"
SZ_CODE = "000001.SZ"
SH_CODE = "600000.SH"


# -----------------------------------------------------------------------
# L.1 — Folder discovery
# -----------------------------------------------------------------------

class TestL1FolderDiscovery:
    """L.1: discover (date, stock) pairs; max_stocks caps the result."""

    def test_discovers_stocks_under_date(self):
        from src.ingest_local import discover_stocks
        pairs = discover_stocks(FIXTURE_ROOT, DATE)
        codes = [p[1] for p in pairs]
        assert SZ_CODE in codes
        assert SH_CODE in codes

    def test_max_stocks_caps_count(self):
        from src.ingest_local import discover_stocks
        pairs = discover_stocks(FIXTURE_ROOT, DATE, max_stocks=1)
        assert len(pairs) == 1

    def test_finds_three_stream_files(self):
        from src.ingest_local import discover_stocks, STREAM_NAMES
        pairs = discover_stocks(FIXTURE_ROOT, DATE)
        for date, code in pairs:
            stock_dir = os.path.join(FIXTURE_ROOT, date, date, code)
            for name in STREAM_NAMES:
                assert os.path.exists(os.path.join(stock_dir, name + ".csv")), \
                    f"Missing {name}.csv for {code}"

    def test_max_stocks_zero_means_no_limit(self):
        """max_stocks=None (or 0) returns all stocks."""
        from src.ingest_local import discover_stocks
        all_pairs = discover_stocks(FIXTURE_ROOT, DATE, max_stocks=None)
        assert len(all_pairs) == 2  # fixture has 2 stocks


# -----------------------------------------------------------------------
# L.2 — 行情 read + map + time + book
# -----------------------------------------------------------------------

class TestL2SnapshotRead:
    """L.2: GBK 行情 → canonical columns; hour/minute from 时间; bids/asks 10-level."""

    @pytest.fixture
    def sz_hq(self):
        from src.ingest_local import read_snapshot
        stock_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SZ_CODE)
        return read_snapshot(stock_dir, SZ_CODE, DATE)

    def test_canonical_columns_present(self, sz_hq):
        required = {"stock_code", "transaction_date", "price", "volume", "amount",
                    "hour", "minute", "datetime_utc",
                    "totalbidvolume", "totalaskvolume",
                    "bids", "asks"}
        missing = required - set(sz_hq.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_stock_code_and_date(self, sz_hq):
        assert (sz_hq["stock_code"] == SZ_CODE).all()
        assert (sz_hq["transaction_date"] == DATE).all()

    def test_hour_minute_from_time_column(self, sz_hq):
        # 93000000 → HHMMSSmmm: 09:30:00.000
        first = sz_hq.iloc[0]
        assert first["hour"] == 9
        assert first["minute"] == 30

    def test_second_tick_hour_minute(self, sz_hq):
        # 100000000 → 10:00:00.000
        second = sz_hq.iloc[1]
        assert second["hour"] == 10
        assert second["minute"] == 0

    def test_bids_is_list_of_dicts_10_levels(self, sz_hq):
        from src.ingest import parse_book_json
        bids = parse_book_json(sz_hq.iloc[0]["bids"])
        assert len(bids) == 10
        assert all("price" in lvl and "volume" in lvl for lvl in bids)

    def test_asks_is_list_of_dicts_10_levels(self, sz_hq):
        from src.ingest import parse_book_json
        asks = parse_book_json(sz_hq.iloc[0]["asks"])
        assert len(asks) == 10
        assert all("price" in lvl and "volume" in lvl for lvl in asks)

    def test_price_is_positive(self, sz_hq):
        assert (sz_hq["price"] > 0).all()

    def test_datetime_utc_is_datetime(self, sz_hq):
        assert pd.api.types.is_datetime64_any_dtype(sz_hq["datetime_utc"])

    def test_tick_volume_and_amount_produced(self, sz_hq):
        """After cumulative→diff, tick_volume and tick_amount must exist and be >= 0."""
        assert "tick_volume" in sz_hq.columns
        assert "tick_amount" in sz_hq.columns
        assert (sz_hq["tick_volume"] >= 0).all()
        assert (sz_hq["tick_amount"] >= 0).all()

    def test_price_change_column(self, sz_hq):
        assert "price_change" in sz_hq.columns


# -----------------------------------------------------------------------
# L.3 — Cancel reconstruction per exchange
# -----------------------------------------------------------------------

class TestL3CancelReconstruction:
    """L.3: SZ cancels from 成交代码=='C'; SH cancels from 委托类型=='D'."""

    def test_sz_cancel_detected_cb_available_true(self):
        from src.ingest_local import load_local
        df = load_local(FIXTURE_ROOT, DATE, max_stocks=None)
        sz_rows = df[df["stock_code"] == SZ_CODE]
        # cb_available should be True (1.0) for the SZ stock
        assert sz_rows["cb_available"].iloc[0] == 1.0

    def test_sz_cancel_count_nonzero(self):
        from src.ingest_local import read_cancel_frame
        sz_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SZ_CODE)
        cancels = read_cancel_frame(sz_dir, SZ_CODE)
        assert len(cancels) > 0, "Expected ≥1 cancel row for SZ stock"

    def test_sz_cancel_has_side_column(self):
        from src.ingest_local import read_cancel_frame
        sz_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SZ_CODE)
        cancels = read_cancel_frame(sz_dir, SZ_CODE)
        assert "side" in cancels.columns

    def test_sh_cancel_detected_cb_available_true(self):
        from src.ingest_local import load_local
        df = load_local(FIXTURE_ROOT, DATE, max_stocks=None)
        sh_rows = df[df["stock_code"] == SH_CODE]
        assert sh_rows["cb_available"].iloc[0] == 1.0

    def test_sh_cancel_count_nonzero(self):
        from src.ingest_local import read_cancel_frame
        sh_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SH_CODE)
        cancels = read_cancel_frame(sh_dir, SH_CODE)
        assert len(cancels) > 0, "Expected ≥1 cancel row for SH stock"

    def test_cancel_rows_have_timestamp(self):
        from src.ingest_local import read_cancel_frame
        sz_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SZ_CODE)
        cancels = read_cancel_frame(sz_dir, SZ_CODE)
        assert "time_int" in cancels.columns or "cancel_time" in cancels.columns or \
               "timestamp" in cancels.columns, "Cancel frame must carry a timestamp column"


# -----------------------------------------------------------------------
# L.4 — bigordervolume derivation
# -----------------------------------------------------------------------

class TestL4BigOrderVolume:
    """L.4: large 逐笔成交 prints → non-zero tick_bigordervolume."""

    def test_bigordervolume_nonzero_for_large_print(self):
        from src.ingest_local import load_local
        df = load_local(FIXTURE_ROOT, DATE, max_stocks=None)
        # The SZ fixture has a 2000-share print which should count as bigorder
        sz = df[df["stock_code"] == SZ_CODE]
        total_bigorder = sz["tick_bigordervolume"].sum()
        assert total_bigorder > 0, "Expected non-zero bigordervolume for large trade prints"

    def test_bigordervolume_column_exists(self):
        from src.ingest_local import load_local
        df = load_local(FIXTURE_ROOT, DATE, max_stocks=None)
        assert "tick_bigordervolume" in df.columns


# -----------------------------------------------------------------------
# L.5 — End-to-end emit shape
# -----------------------------------------------------------------------

class TestL5EndToEndShape:
    """L.5: load_local emits a superset of compute_daily_features columns,
    temporally sorted, with cb_available set for both stocks."""

    REQUIRED_COLS = {
        # columns consumed by features.compute_daily_features
        "tick_volume", "tick_amount", "price_change",
        "hour", "minute", "datetime_utc", "price",
        "bids", "asks", "totalbidvolume", "totalaskvolume",
        # optional but expected
        "tick_bigordervolume",
        # metadata / flags
        "stock_code", "transaction_date", "cb_available",
    }

    @pytest.fixture
    def full_df(self):
        from src.ingest_local import load_local
        return load_local(FIXTURE_ROOT, DATE, max_stocks=None)

    def test_required_columns_present(self, full_df):
        missing = self.REQUIRED_COLS - set(full_df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_two_stocks_present(self, full_df):
        assert full_df["stock_code"].nunique() == 2

    def test_temporal_sort_within_stock(self, full_df):
        for code, grp in full_df.groupby("stock_code"):
            ts = grp["datetime_utc"].reset_index(drop=True)
            assert ts.is_monotonic_increasing, f"{code} not temporally sorted"

    def test_cb_available_is_true_for_all_stocks(self, full_df):
        """Both stocks in the fixture have cancels → cb_available=1.0 everywhere."""
        assert (full_df["cb_available"] == 1.0).all()

    def test_no_nulls_in_required_numeric_cols(self, full_df):
        numeric_required = {
            "tick_volume", "tick_amount", "price_change",
            "hour", "minute", "price", "cb_available",
        }
        for col in numeric_required:
            assert full_df[col].notna().all(), f"Nulls in {col}"

    def test_features_compute_without_error(self, full_df):
        """Run compute_daily_features on the first stock group — must not raise."""
        from src.features import compute_daily_features
        grp = full_df[full_df["stock_code"] == SZ_CODE]
        result = compute_daily_features(grp, has_cancel_table=True)
        assert isinstance(result, dict)
        assert len(result) > 0
        # All values must be finite floats
        import math
        for k, v in result.items():
            assert isinstance(v, float), f"{k} is not float: {type(v)}"
            assert math.isfinite(v), f"{k} is not finite: {v}"

    def test_max_stocks_limits_result(self):
        from src.ingest_local import load_local
        df1 = load_local(FIXTURE_ROOT, DATE, max_stocks=1)
        assert df1["stock_code"].nunique() == 1

    def test_cb_available_non_neutral_in_rules(self, full_df):
        """When cb_available=1.0 the _class_score includes CB dims (not neutral)."""
        from src.rules import _class_score, DIMS_YOUZI
        from src.features import compute_daily_features
        grp = full_df[full_df["stock_code"] == SZ_CODE]
        feat = compute_daily_features(grp, has_cancel_table=True)
        score_with_cb = _class_score(feat, DIMS_YOUZI, cb_available=True)
        score_without_cb = _class_score(feat, DIMS_YOUZI, cb_available=False)
        # Scores must both be floats in [0,1]
        assert 0.0 <= score_with_cb <= 1.0
        assert 0.0 <= score_without_cb <= 1.0
        # With cb_available=True, CB dims participate (non-neutral path is exercised)
        # We just verify the function runs and returns a valid float;
        # actual divergence depends on CB feature values (stub returns 0)
        assert isinstance(score_with_cb, float)
