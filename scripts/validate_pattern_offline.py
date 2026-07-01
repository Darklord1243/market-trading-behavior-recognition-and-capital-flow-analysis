"""Offline Task-1 clustering-quality harness (P5 Slice-1).

**Offline / label-free / post-hoc only.**  MUST NOT be imported by main.py or any
src/ inference-path module.  It recomputes the production feature matrix + Task-1
clustering from ``parquet:data/202606`` and reports the board's Task-1 scoring
*components* per day — silhouette, CH, Wasserstein separation, DTW separation —
using only our own data + our own clustering.  No labels, no answer files, no
board feedback (LIS §3.3; docs/hypotheses/p5-task1-metric-alignment.md §5/§6).

It reports COMPONENTS only.  It never fabricates a blended "Task-1 score", because
the board's exact 4-metric blend is unknown and inventing one invites tuning to a
wrong target.

Usage
-----
python scripts/validate_pattern_offline.py --input parquet:data/202606 --date 20260626
python scripts/validate_pattern_offline.py --input parquet:data/202606 --all-dates

Exit codes
----------
0 — ran and scored at least one date.
1 — real failure: requested data missing / malformed / no dates found.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import statistics
import sys

# Ensure repo root is importable regardless of cwd (scripts/ is not a package).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

log = logging.getLogger(__name__)

_DEFAULT_ROOT = "data/202606"
_DEFAULT_UNIVERSE = os.path.join(_ROOT, "samples", "stock-samples.xlsx")
_DATE_RE = re.compile(r"^\d{8}$")

# Audit D1.b baseline silhouette per labeled day (competitive-gap-audit-20260701.md),
# printed alongside our recomputed daily-only silhouette for an explicit comparison.
_AUDIT_D1B = {
    "20260616": 0.1685, "20260617": 0.1445, "20260618": 0.1355, "20260622": 0.1596,
    "20260623": 0.1426, "20260624": 0.1564, "20260625": 0.1583, "20260626": 0.1509,
    "20260629": 0.1437,
}


def _resolve_root(input_source: str) -> str:
    src = input_source.strip()
    if src.lower().startswith("parquet"):
        return (src.split(":", 1)[1].strip() or _DEFAULT_ROOT) if ":" in src else _DEFAULT_ROOT
    return src  # treat as a raw corpus root


def _discover_dates(root: str) -> list[str]:
    """Trading days (YYYYMMDD) in the corpus, sorted ascending.

    The corpus layout is ``root/<stream>/YYYYMMDD/`` (streams are Chinese folder
    names), so dates live one level below the snapshot stream — not directly under
    *root*.  Falls back to scanning any immediate subfolder if the canonical
    snapshot stream dir is absent.
    """
    if not os.path.isdir(root):
        return []
    from src.ingest_parquet import _STREAM_DIR

    snap_dir = os.path.join(root, _STREAM_DIR["snapshot"])
    search_dirs = [snap_dir] if os.path.isdir(snap_dir) else [
        os.path.join(root, d) for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d))
    ]
    dates: set[str] = set()
    for d in search_dirs:
        for name in os.listdir(d):
            if _DATE_RE.match(name) and os.path.isdir(os.path.join(d, name)):
                dates.add(name)
    return sorted(dates)


def _load_universe(path: str) -> list[str]:
    from src.pipeline_parquet import load_universe_codes
    return load_universe_codes(path)


def score_one_date(root: str, universe_codes: list[str], date: str) -> dict | None:
    """Recompute the production matrix + intraday trajectories for *date* and
    return the Task-1 clustering-quality components (or None if no data).

    Uses ONE extra batched snapshot read for trajectories; the per-stock cancel
    loop is not repeated (docs/hypotheses/p5-task1-metric-alignment.md §3).
    """
    from src.cluster import score_day
    from src.intraday_trajectory import build_trajectories
    from src.ingest_parquet import load_parquet
    from src.pipeline_parquet import build_feature_matrix_for_panel

    matrix = build_feature_matrix_for_panel(root, date, universe_codes)
    if matrix is None or matrix.empty:
        return None

    present = sorted({str(c) for c in matrix.index.get_level_values("stock_code")})
    snap = load_parquet(root, date, keys=present)
    traj_by_key = build_trajectories(snap) if snap is not None and not snap.empty else {}
    trajectories = {
        idx: traj_by_key.get((str(idx[0]), str(idx[1])))
        for idx in matrix.index
    }
    # If nothing resolved (no snapshot), fall back to daily-only scoring.
    if not any(v is not None for v in trajectories.values()):
        trajectories = None

    d = score_day(matrix, trajectories=trajectories)
    d["date"] = str(date)
    d["panel_n"] = int(len(matrix))
    return d


def _print_report(rows: list[dict]) -> None:
    print("Task-1 offline clustering quality — components only (no blended score).")
    print(f"{'date':<10}{'panel_n':>8}{'best_K':>7}{'sil':>9}{'sil_daily':>10}"
          f"{'audit_D1b':>10}{'CH':>8}{'wass_sep':>10}{'dtw_sep':>9}{'nclust':>7}  flags")
    for r in rows:
        audit = _AUDIT_D1B.get(r["date"])
        audit_s = f"{audit:.4f}" if audit is not None else "   -  "
        flag = "DEGENERATE" if r["degenerate"] else ""
        up = "↑" if audit is not None and r["silhouette"] > audit else ""
        print(f"{r['date']:<10}{r['panel_n']:>8}{r['best_k']:>7}{r['silhouette']:>9.4f}"
              f"{r['silhouette_daily']:>10.4f}{audit_s:>10}{r['ch']:>8.1f}"
              f"{r['wasserstein_sep']:>10.4f}{r['dtw_sep']:>9.4f}{r['n_clusters']:>7}  {flag}{up}")

    if len(rows) >= 1:
        sils = [r["silhouette"] for r in rows]
        sils_daily = [r["silhouette_daily"] for r in rows]
        chs = [r["ch"] for r in rows]
        improved = sum(
            1 for r in rows
            if _AUDIT_D1B.get(r["date"]) is not None and r["silhouette"] > _AUDIT_D1B[r["date"]]
        )
        n_audit = sum(1 for r in rows if _AUDIT_D1B.get(r["date"]) is not None)
        print("-" * 96)
        print(f"median silhouette (enriched) = {statistics.median(sils):.4f}   "
              f"median silhouette (daily-only) = {statistics.median(sils_daily):.4f}   "
              f"median CH = {statistics.median(chs):.1f}")
        print(f"days silhouette > audit D1.b baseline: {improved}/{n_audit}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline Task-1 clustering-quality harness (label-free, §3.3-safe)."
    )
    parser.add_argument("--input", required=True,
                        help="Corpus source, e.g. 'parquet:data/202606'.")
    parser.add_argument("--date", default=None, help="Single trading date YYYYMMDD.")
    parser.add_argument("--all-dates", action="store_true", dest="all_dates",
                        help="Score every trading-day subdirectory under the corpus root.")
    parser.add_argument("--universe", default=None,
                        help="CSV/xlsx of universe codes (default: samples/stock-samples.xlsx).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = _resolve_root(args.input)
    if not os.path.isdir(root):
        print(f"ERROR: corpus root not found: {root}", file=sys.stderr)
        return 1

    universe_path = args.universe or _DEFAULT_UNIVERSE
    if not os.path.isfile(universe_path):
        print(f"ERROR: universe file not found: {universe_path}", file=sys.stderr)
        return 1
    try:
        universe_codes = _load_universe(universe_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to load universe: {exc}", file=sys.stderr)
        return 1

    if args.date:
        dates = [str(args.date)]
    elif args.all_dates:
        dates = _discover_dates(root)
        if not dates:
            print(f"ERROR: no YYYYMMDD trading-day dirs under {root}", file=sys.stderr)
            return 1
    else:
        print("ERROR: pass --date YYYYMMDD or --all-dates", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for date in dates:
        try:
            d = score_one_date(root, universe_codes, date)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: scoring failed for {date}: {exc}", file=sys.stderr)
            return 1
        if d is None:
            print(f"WARNING: no parquet data for {date} — skipped", file=sys.stderr)
            continue
        rows.append(d)

    if not rows:
        print("ERROR: no dates produced a feature matrix (data missing?)", file=sys.stderr)
        return 1

    _print_report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
