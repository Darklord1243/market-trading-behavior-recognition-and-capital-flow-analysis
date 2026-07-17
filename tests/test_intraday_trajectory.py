"""Tests for src/intraday_trajectory.py — Slice-1 intraday trajectory builder.

The builder turns one stock-day snapshot frame into a fixed-length
(N_BINS, 3) trajectory of [tick_amount_share, book_imbalance, price_return]
using equal-count binning, plus a small set of shape-summary features used to
enrich the Task-1 clustering matrix.

All tests use synthetic frames with the exact cleaned-snapshot column contract
(tick_amount, totalbidvolume, totalaskvolume, price, price_change, stock_code,
transaction_date).  A stub returning zeros must FAIL the discriminating tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.intraday_trajectory import (
    N_SERIES,
    SUMMARY_COLS,
    build_trajectory,
    build_trajectories,
    summary_features,
)


def _make_group(
    tick_amount: list[float],
    bid: list[float] | None = None,
    ask: list[float] | None = None,
    price: list[float] | None = None,
    stock_code: str = "000001.SZ",
    date: str = "20260616",
) -> pd.DataFrame:
    """Build a cleaned-snapshot-style frame for one stock-day."""
    n = len(tick_amount)
    if bid is None:
        bid = [100.0] * n
    if ask is None:
        ask = [100.0] * n
    if price is None:
        price = [10.0 + 0.01 * i for i in range(n)]
    px = pd.Series(price, dtype=float)
    return pd.DataFrame(
        {
            "stock_code": stock_code,
            "transaction_date": date,
            "tick_amount": tick_amount,
            "totalbidvolume": bid,
            "totalaskvolume": ask,
            "price": px,
            "price_change": px.diff().fillna(0.0),
        }
    )


# ---------------------------------------------------------------------------
# Shape + edge cases
# ---------------------------------------------------------------------------

def test_shape_is_nbins_by_nseries():
    g = _make_group(tick_amount=[1.0] * 100)
    traj = build_trajectory(g, n_bins=30)
    assert traj.shape == (30, N_SERIES)
    assert np.isfinite(traj).all()


def test_empty_group_returns_zeros():
    g = _make_group(tick_amount=[])
    traj = build_trajectory(g, n_bins=30)
    assert traj.shape == (30, N_SERIES)
    assert np.allclose(traj, 0.0)


def test_single_tick_repeats_no_nan():
    g = _make_group(tick_amount=[5.0], bid=[200.0], ask=[100.0], price=[10.0])
    traj = build_trajectory(g, n_bins=30)
    assert traj.shape == (30, N_SERIES)
    assert np.isfinite(traj).all()
    # A single tick repeated across bins → every bin identical.
    assert np.allclose(traj, traj[0], atol=1e-9)


def test_amount_share_sums_to_one():
    rng = np.random.default_rng(0)
    g = _make_group(tick_amount=list(rng.uniform(1.0, 10.0, 120)))
    traj = build_trajectory(g, n_bins=30)
    # Column 0 is the per-bin turnover share; over a session it must sum to ~1.
    assert abs(traj[:, 0].sum() - 1.0) < 1e-9


def test_book_imbalance_sign():
    # Bid >> ask everywhere → imbalance strictly positive.
    g = _make_group(tick_amount=[1.0] * 60, bid=[300.0] * 60, ask=[100.0] * 60)
    traj = build_trajectory(g, n_bins=30)
    assert (traj[:, 1] > 0).all()


# ---------------------------------------------------------------------------
# Summary features (the clustering-enrichment axes)
# ---------------------------------------------------------------------------

def test_front_vs_back_load_discriminates_shape():
    n = 120
    third = n // 3
    front = [10.0] * third + [0.1] * (n - third)      # turnover front-loaded
    back = [0.1] * (n - third) + [10.0] * third        # turnover back-loaded
    tf = build_trajectory(_make_group(tick_amount=front), n_bins=30)
    tb = build_trajectory(_make_group(tick_amount=back), n_bins=30)
    sf = summary_features(tf)
    sb = summary_features(tb)
    assert sf["traj_turnover_front_load"] > sf["traj_turnover_back_load"]
    assert sb["traj_turnover_back_load"] > sb["traj_turnover_front_load"]


def test_summary_features_have_all_columns():
    g = _make_group(tick_amount=[1.0] * 90)
    feats = summary_features(build_trajectory(g, n_bins=30))
    assert set(feats.keys()) == set(SUMMARY_COLS)
    assert all(np.isfinite(v) for v in feats.values())


# ---------------------------------------------------------------------------
# Batch builder groups by (stock_code, transaction_date)
# ---------------------------------------------------------------------------

def test_build_trajectories_groups_by_stock_day():
    g1 = _make_group(tick_amount=[1.0] * 40, stock_code="000001.SZ")
    g2 = _make_group(tick_amount=[2.0] * 40, stock_code="600000.SH")
    df = pd.concat([g1, g2], ignore_index=True)
    traj = build_trajectories(df, n_bins=30)
    assert set(traj.keys()) == {
        ("000001.SZ", "20260616"),
        ("600000.SH", "20260616"),
    }
    for arr in traj.values():
        assert arr.shape == (30, N_SERIES)
