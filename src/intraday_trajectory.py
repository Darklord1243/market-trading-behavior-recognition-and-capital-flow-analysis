"""Intraday trajectory builder — Slice-1 Task-1 metric alignment (P5).

Turns one stock-day snapshot frame into a fixed-length ``(N_BINS, 3)`` trajectory
of ``[tick_amount_share, book_imbalance, price_return]`` via equal-count binning,
plus a small set of shape-summary features used to enrich the Task-1 clustering
matrix (see docs/hypotheses/p5-task1-metric-alignment.md §2).

Intraday-only: uses only same-day snapshot ticks, in arrival order — no
look-ahead, no external lookup (compliance #1).  Pure numpy/pandas, no new deps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N_SERIES = 3
_EPS = 1e-12

# Shape-summary feature names (fixed order).  These enrich the clustering matrix.
SUMMARY_COLS: list[str] = [
    "traj_turnover_front_load",
    "traj_turnover_back_load",
    "traj_turnover_concentration",
    "traj_imbalance_mean",
    "traj_imbalance_trend",
    "traj_return_amplitude",
]


def build_trajectory(group: pd.DataFrame, n_bins: int = 30) -> np.ndarray:
    """Build a ``(n_bins, 3)`` intraday trajectory for one stock-day.

    Series (columns):
      0. ``tick_amount_share`` — per-bin Σ tick_amount / day total (sums to 1).
      1. ``book_imbalance``    — per-bin mean (bid−ask)/(bid+ask), in [-1, 1].
      2. ``price_return``      — per-bin Σ price_change / first-tick price.

    Binning is **equal-count** over the arrival-ordered ticks (illiquid names
    still fill all bins).  Edge cases: empty group → zeros; single tick →
    that tick repeated across every bin.
    """
    if group is None or len(group) == 0:
        return np.zeros((n_bins, N_SERIES), dtype=float)

    amt = pd.to_numeric(group.get("tick_amount", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    bid = pd.to_numeric(group.get("totalbidvolume", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    ask = pd.to_numeric(group.get("totalaskvolume", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    price = pd.to_numeric(group.get("price", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
    pchg = pd.to_numeric(group.get("price_change", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)

    n = len(amt)
    # Sparse day (fewer ticks than bins): upsample by repeating ticks in arrival
    # order so every bin fills.  A single tick → identical across all bins.
    if n < n_bins:
        reps = int(np.ceil(n_bins / n))
        take = np.repeat(np.arange(n), reps)
        amt, bid, ask, price, pchg = amt[take], bid[take], ask[take], price[take], pchg[take]
        n = len(amt)

    per_tick_imb = (bid - ask) / (bid + ask + _EPS)
    first_price = float(price[0]) if price[0] > 0 else 0.0
    per_tick_ret = pchg / first_price if first_price > 0 else np.zeros(n)

    # Equal-count bin index for each tick.
    bin_idx = np.array_split(np.arange(n), n_bins)

    total_amt = float(amt.sum())
    traj = np.zeros((n_bins, N_SERIES), dtype=float)
    for b, idx in enumerate(bin_idx):
        if len(idx) == 0:
            continue
        traj[b, 0] = amt[idx].sum() / total_amt if total_amt > 0 else 0.0
        traj[b, 1] = float(per_tick_imb[idx].mean())
        traj[b, 2] = float(per_tick_ret[idx].sum())
    return traj


def summary_features(traj: np.ndarray) -> dict[str, float]:
    """Shape-summary features of a ``(n_bins, 3)`` trajectory (see SUMMARY_COLS)."""
    n_bins = traj.shape[0]
    third = max(1, n_bins // 3)
    share = traj[:, 0]
    imb = traj[:, 1]
    ret = traj[:, 2]
    cum_ret = np.cumsum(ret)
    return {
        "traj_turnover_front_load": float(share[:third].sum()),
        "traj_turnover_back_load": float(share[-third:].sum()),
        "traj_turnover_concentration": float(share.max()) if n_bins else 0.0,
        "traj_imbalance_mean": float(imb.mean()) if n_bins else 0.0,
        "traj_imbalance_trend": float(imb[-third:].mean() - imb[:third].mean()),
        "traj_return_amplitude": float(cum_ret.max() - cum_ret.min()) if n_bins else 0.0,
    }


def build_trajectories(df: pd.DataFrame, n_bins: int = 30) -> dict[tuple, np.ndarray]:
    """Build trajectories for every ``(stock_code, transaction_date)`` group.

    Returns ``{(stock_code, date): (n_bins, 3) ndarray}``.  Groups are formed
    from the cleaned snapshot frame the parquet pipeline already loads, so no
    additional reads are incurred.
    """
    if df is None or df.empty:
        return {}
    out: dict[tuple, np.ndarray] = {}
    for key, g in df.groupby(["stock_code", "transaction_date"], sort=False):
        out[(str(key[0]), str(key[1]))] = build_trajectory(g, n_bins=n_bins)
    return out
