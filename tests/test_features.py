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

import numpy as np
import pandas as pd
import pytest

from src.features import compute_daily_features


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
