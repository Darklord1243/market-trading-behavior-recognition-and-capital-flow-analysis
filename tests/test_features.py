"""Feature-function sanity tests on a deterministic synthetic tick group.

NOTE on "Case 1": Case 1 ("Shrinking Volume Game") is cited in the repo at
docs/competition-spec/topic-specifications-and-data.*.md §7.2 (恒工精密, 2026-04-28),
but it describes a different stock than the 603997.SH fixture, so its figures cannot
be asserted against the fixture. These tests therefore anchor on a *constructed* tick
group with hand-computed expected values — deterministic, fixture-independent
arithmetic the feature functions must reproduce — by design, not because Case 1 is
missing.
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from src.features import compute_daily_features, _cb_features


def _book(volumes):
    """Build a minimal bids/asks JSON: one level per volume."""
    return json.dumps([{"price": 12.0 - i * 0.01, "volume": float(v), "bigOrderPercent": 0.0}
                       for i, v in enumerate(volumes)])


@pytest.fixture
def synthetic_group():
    # 4 ticks: one per OSS tier (mega/large/mid/small by SHARE volume).
    n = 4
    g = pd.DataFrame({
        "tick_volume": [60000, 20000, 5000, 500],          # mega, large, mid, small
        "tick_amount": [600000.0, 200000.0, 50000.0, 5000.0],
        "price": [12.0, 12.1, 12.0, 12.1],
        "price_change": [0.0, 0.1, -0.1, 0.1],             # buy, buy, sell, buy
        "hour": [9, 10, 13, 14],
        "minute": [30, 0, 0, 55],                          # open30 x2, mid, close10
        "tick_bigordervolume": [600, 0, 0, 0],
        "totalbidvolume": [1000, 1000, 1000, 1000],
        "totalaskvolume": [3000, 3000, 3000, 3000],
        "datetime_utc": pd.to_datetime(
            ["2026-05-07 01:30:00", "2026-05-07 02:00:00",
             "2026-05-07 05:00:00", "2026-05-07 06:55:00"]),
        # first-snapshot book: bid volume 1000 vs ask volume 3000 -> imbalance -0.5
        "bids": [_book([1000])] * n,
        "asks": [_book([3000])] * n,
    })
    return g


def test_oss_amount_and_count_shares(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    total = 855000.0
    assert f["oss_mega_amount_pct"] == pytest.approx(600000 / total, rel=1e-6)
    assert f["oss_large_amount_pct"] == pytest.approx(200000 / total, rel=1e-6)
    assert f["oss_mid_amount_pct"] == pytest.approx(50000 / total, rel=1e-6)
    assert f["oss_small_amount_pct"] == pytest.approx(5000 / total, rel=1e-6)
    # one tick per tier -> each count share is 1/4
    for tier in ("mega", "large", "mid", "small"):
        assert f[f"oss_{tier}_count_pct"] == pytest.approx(0.25)


def test_ap_active_buy_pct(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    # buy amt = 200000 + 5000 = 205000 ; sell amt = 50000 ; denom = 255000
    assert f["ap_active_buy_pct"] == pytest.approx(205000 / 255000, rel=1e-6)
    assert f["ap_active_sell_pct"] == pytest.approx(50000 / 255000, rel=1e-6)


def test_pi_time_concentration(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    # open30 = ticks 0,1 (800000) ; close10 = tick 3 (5000) ; total 855000
    assert f["pi_open_30min_amount_pct"] == pytest.approx(800000 / 855000, rel=1e-6)
    assert f["pi_close_10min_amount_pct"] == pytest.approx(5000 / 855000, rel=1e-6)
    assert f["pi_time_concentration"] == pytest.approx(805000 / 855000, rel=1e-6)


def test_book_imbalance_from_snapshot(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    # first snapshot: bid 1000, ask 3000 -> (1000-3000)/4000 = -0.5
    assert f["book_imbalance"] == pytest.approx(-0.5, rel=1e-6)


def test_cb_graceful_degradation(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    # snapshot-only -> CB sub-vector is zero and flagged unavailable
    assert f["cb_available"] == 0.0
    assert f["cb_cancel_order_ratio"] == 0.0
    f2 = compute_daily_features(synthetic_group, has_cancel_table=True)
    assert f2["cb_available"] == 1.0


def test_all_features_finite(synthetic_group):
    f = compute_daily_features(synthetic_group, has_cancel_table=False)
    assert all(np.isfinite(v) for v in f.values())


def test_pi_windows_use_beijing_clock_and_include_1500_close():
    # Ticks placed at known BEIJING times: 09:35 (open), 11:00 (neither),
    # 14:55 (close), 15:00 (close print). hour/minute are the Beijing clock.
    g = pd.DataFrame({
        "tick_volume": [1000, 1000, 1000, 1000],
        "tick_amount": [100.0, 10.0, 30.0, 60.0],          # total 200
        "price": [12.0, 12.1, 12.0, 12.1],
        "price_change": [0.0, 0.1, -0.1, 0.1],
        "hour": [9, 11, 14, 15],
        "minute": [35, 0, 55, 0],
        "tick_bigordervolume": [0, 0, 0, 0],
        "totalbidvolume": [1000, 1000, 1000, 1000],
        "totalaskvolume": [1000, 1000, 1000, 1000],
        # corresponding UTC stamps (Beijing - 8h), monotonic for RS diffs
        "datetime_utc": pd.to_datetime(
            ["2026-05-07 01:35:00", "2026-05-07 03:00:00",
             "2026-05-07 06:55:00", "2026-05-07 07:00:00"]),
        "bids": [_book([1000])] * 4,
        "asks": [_book([1000])] * 4,
    })
    f = compute_daily_features(g, has_cancel_table=False)
    # open window [09:30,10:00] -> only the 09:35 tick (100/200)
    assert f["pi_open_30min_amount_pct"] == pytest.approx(100 / 200)
    # close window [14:50,15:00] inclusive -> 14:55 AND 15:00 prints ((30+60)/200)
    # if 15:00 were excluded this would be 30/200 = 0.15, so this pins the boundary.
    assert f["pi_close_10min_amount_pct"] == pytest.approx(90 / 200)
    assert f["pi_time_concentration"] == pytest.approx(190 / 200)


# ---------------------------------------------------------------------------
# CB (Cancel-Behaviour) feature tests — Track L-b
# ---------------------------------------------------------------------------

def _synthetic_cancel_frame():
    """Build a deterministic cancel frame for hand-computed CB assertions.

    6 cancel events:
      sides  : B, B, S, B, S, S   → buy_count=3, sell_count=3
      cancel_qty: 100,200,150,300,100,200  → sum=1050
      cancel_times (HHMMSSmmm int, same convention as read_cancel_frame):
          93000000, 93000100, 93000200, 93000500, 93001000, 93002000
        diffs in ms (HHMMSSmmm-integer differences):
          100, 100, 300, 500, 1000
        With CB_FAST_CANCEL_MS=500, intervals < 500: 100, 100, 300 → 3 of 5 pairs
          → cb_fast_cancel_ratio = 3/5 = 0.6

    The tick group carries 10 trades with total tick_volume=5000:
      cb_cancel_order_ratio  = 6 / (6+10) = 0.375
      cb_cancel_volume_ratio = 1050 / (1050+5000) = 1050/6050 ≈ 0.17355
      cb_buy_cancel_ratio    = 3 / 6 = 0.5
      cb_sell_cancel_ratio   = 3 / 6 = 0.5
    """
    cancel_df = pd.DataFrame({
        "side": ["B", "B", "S", "B", "S", "S"],
        "cancel_time": [93000000, 93000100, 93000200, 93000500, 93001000, 93002000],
        "cancel_qty": [100.0, 200.0, 150.0, 300.0, 100.0, 200.0],
    })
    cancel_df["time_int"] = cancel_df["cancel_time"]
    return cancel_df


def _synthetic_tick_group_10():
    """10-tick group with total tick_volume=5000 (used as trade-count proxy)."""
    n = 10
    return pd.DataFrame({
        "tick_volume": [500] * n,
        "tick_amount": [5000.0] * n,
        "price": [12.0] * n,
        "price_change": [0.0] * n,
        "hour": [9] * n,
        "minute": [30] * n,
        "tick_bigordervolume": [0] * n,
        "totalbidvolume": [1000] * n,
        "totalaskvolume": [1000] * n,
        "datetime_utc": pd.date_range("2026-05-07 01:30:00", periods=n, freq="30s"),
        "bids": [json.dumps([{"price": 12.0, "volume": 1000.0}])] * n,
        "asks": [json.dumps([{"price": 12.05, "volume": 1000.0}])] * n,
    })


# --- Lb.1: CB true-branch returns non-zero values ---

def test_cb_features_nonzero_with_cancel_frame():
    """Lb.1 red-first: _cb_features true-branch must return non-zero values
    when a cancel_df is provided (track L-b; fails until implementation)."""
    cancel_df = _synthetic_cancel_frame()
    group = _synthetic_tick_group_10()
    result = _cb_features(group, has_cancel_table=True, cancel_df=cancel_df)
    # All CB values must be non-zero (except possibly some edge case we didn't plant)
    assert result["cb_fast_cancel_ratio"] > 0.0, (
        "cb_fast_cancel_ratio must be >0 on cancel frame with short inter-cancel gaps"
    )
    assert result["cb_buy_cancel_ratio"] > 0.0
    assert result["cb_sell_cancel_ratio"] > 0.0
    assert result["cb_cancel_order_ratio"] > 0.0
    assert result["cb_cancel_volume_ratio"] > 0.0
    assert result["cb_available"] == 1.0


def test_cb_features_hand_computed_values():
    """Hand-computed CB values on the synthetic cancel frame.

    cancel frame: 6 events, sides B/B/S/B/S/S, qty 100/200/150/300/100/200
    tick group: 10 trades, total tick_volume=5000

    cb_cancel_order_ratio  = 6 / (6+10) = 0.375
    cb_cancel_volume_ratio = 1050 / (1050+5000) = 1050/6050 ≈ 0.17355
    cb_buy_cancel_ratio    = 3 / 6 = 0.5
    cb_sell_cancel_ratio   = 3 / 6 = 0.5
    cb_fast_cancel_ratio   = 3/5 = 0.6  (intervals: 100,100,300 of 5 are < 500ms)

    Note: cancel_time is HHMMSSmmm integer. Differences in raw integer are used as
    millisecond proxies (inter-cancel interval in ms units).
    """
    cancel_df = _synthetic_cancel_frame()
    group = _synthetic_tick_group_10()
    result = _cb_features(group, has_cancel_table=True, cancel_df=cancel_df)

    assert result["cb_cancel_order_ratio"] == pytest.approx(6 / 16, rel=1e-6)
    assert result["cb_cancel_volume_ratio"] == pytest.approx(1050 / 6050, rel=1e-6)
    assert result["cb_buy_cancel_ratio"] == pytest.approx(0.5, rel=1e-6)
    assert result["cb_sell_cancel_ratio"] == pytest.approx(0.5, rel=1e-6)
    assert result["cb_fast_cancel_ratio"] == pytest.approx(3 / 5, rel=1e-6)


def test_cb_features_absent_path_unchanged():
    """has_cancel_table=False path (snapshot/xlsx) still returns zeros + cb_available=0."""
    cancel_df = _synthetic_cancel_frame()
    group = _synthetic_tick_group_10()
    result = _cb_features(group, has_cancel_table=False, cancel_df=cancel_df)
    from src.features import CB_KEYS
    for k in CB_KEYS:
        assert result[k] == 0.0, f"{k} must be 0.0 on absent path"
    assert result["cb_available"] == 0.0


def test_cb_features_empty_cancel_frame():
    """An empty cancel frame with has_cancel_table=True returns zeros + cb_available=1."""
    empty_df = pd.DataFrame(columns=["side", "cancel_time", "cancel_qty", "time_int"])
    group = _synthetic_tick_group_10()
    result = _cb_features(group, has_cancel_table=True, cancel_df=empty_df)
    from src.features import CB_KEYS
    for k in CB_KEYS:
        assert result[k] == 0.0, f"{k} must be 0.0 on empty cancel frame"
    assert result["cb_available"] == 1.0


def test_cb_features_all_values_finite_in_unit_interval():
    """All CB output values are finite floats in [0, 1]."""
    import math
    cancel_df = _synthetic_cancel_frame()
    group = _synthetic_tick_group_10()
    result = _cb_features(group, has_cancel_table=True, cancel_df=cancel_df)
    from src.features import CB_KEYS
    for k in CB_KEYS:
        v = result[k]
        assert isinstance(v, float), f"{k} must be float, got {type(v)}"
        assert math.isfinite(v), f"{k} is not finite: {v}"
        assert 0.0 <= v <= 1.0, f"{k}={v} outside [0,1]"


def test_cb_features_fixture_nonzero():
    """Lb.4: read_cancel_frame on the tiny fixture → non-zero CB keys via
    compute_daily_features(..., has_cancel_table=True, cancel_df=...)."""
    from src.ingest_local import read_cancel_frame, load_local

    FIXTURE_ROOT = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests", "fixtures", "local_l2_tiny",
    )
    DATE = "20260611"
    SZ_CODE = "000001.SZ"

    stock_dir = os.path.join(FIXTURE_ROOT, DATE, DATE, SZ_CODE)
    cancel_df = read_cancel_frame(stock_dir, SZ_CODE)
    assert len(cancel_df) > 0, "Fixture must have at least one cancel row"

    # Load the snapshot group for the SZ stock
    df = load_local(FIXTURE_ROOT, DATE, max_stocks=None)
    grp = df[df["stock_code"] == SZ_CODE].copy()

    result = compute_daily_features(grp, has_cancel_table=True, cancel_df=cancel_df)

    # CB values must be non-zero on a fixture that has real cancels
    assert result["cb_available"] == 1.0
    assert result["cb_cancel_order_ratio"] > 0.0 or result["cb_cancel_volume_ratio"] > 0.0, (
        "At least one CB ratio must be non-zero when cancel data is present"
    )


def test_compute_daily_features_no_cancel_df_backward_compat():
    """compute_daily_features without cancel_df arg still works (backward compat).
    has_cancel_table=True without cancel_df → cb_available=1.0, CB values=0.0."""
    group = _synthetic_tick_group_10()
    result = compute_daily_features(group, has_cancel_table=True)
    assert result["cb_available"] == 1.0
    # Without cancel_df, CB values stay 0.0 (no data to compute from)
    from src.features import CB_KEYS
    for k in CB_KEYS:
        assert result[k] == 0.0
