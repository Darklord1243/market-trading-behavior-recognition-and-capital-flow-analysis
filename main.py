"""AFAC2026 Track-1 pipeline entry point.

Recomputes features from raw L2 and emits the two competition CSVs:
  pattern_reco.csv   (Task 1 — trading-pattern clustering)
  predict_result.csv (Task 2 — capital type + intent)

Audit-contract guarantees (brief §9):
  * Features are recomputed from raw L2 every run — never reads a pre-computed file.
  * Relative paths and a fixed random seed (config.RANDOM_SEED) throughout.
  * Output writers fail loudly if any format/label/date check fails.
  * --date / "yesterday" resolution is dynamic and holiday-aware (calendar stubbed).
  * No LLM call anywhere in this inference path.

Usage:
    python main.py --input samples/AFAC2026.xlsx -o outputs/
    python main.py --input "data/*.xlsx" -o outputs/ --date 20260507
    python main.py --input parquet:data/202606 --universe samples/stock-samples.xlsx \\
                   --date 20260623 -o outputs/20260623 --pack submit.zip
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import random
import sys

import numpy as np

import config
from config import RANDOM_SEED
from src import aggregate, cluster, ingest, label, model, postprocess

log = logging.getLogger("afac2026")

# --- Trading-calendar seam -------------------------------------------------
# TODO(holiday-calendar): replace with an exchange holiday calendar (e.g.
# chinese_calendar / a maintained SSE/SZSE holiday table). The seam exists so the
# nightly "yesterday" default is correct on weekends and exchange holidays.
_KNOWN_HOLIDAYS: set[str] = set()  # YYYYMMDD strings; empty stub = weekends-only


def previous_trading_day(today: _dt.date) -> str:
    """Most recent trading day strictly before `today` (weekends + holidays skipped)."""
    d = today - _dt.timedelta(days=1)
    while d.weekday() >= 5 or d.strftime("%Y%m%d") in _KNOWN_HOLIDAYS:
        d -= _dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


def resolve_expected_date(data_dates: list[str], cli_date: str | None) -> str | None:
    """Resolve the transaction_date the output is asserted against.

    Priority: explicit --date > single date present in the data > None (multi-day
    backfill: per-row dates still validated for null/blank, just not pinned to one day).
    The nightly default ("yesterday", holiday-aware) is logged for visibility.
    """
    nightly_default = previous_trading_day(_dt.date.today())
    log.info("nightly 'yesterday' (holiday-aware) would resolve to: %s", nightly_default)

    if cli_date:
        log.info("using explicit --date %s", cli_date)
        return str(cli_date)
    if len(data_dates) == 1:
        only = data_dates[0]
        if only != nightly_default:
            log.warning(
                "data date %s != nightly 'yesterday' %s (expected for fixtures/backfill)",
                only, nightly_default,
            )
        return only
    log.warning("data spans %d dates; skipping single-date pin", len(data_dates))
    return None


def set_seeds(seed: int = RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)


def run(input_glob: str, out_dir: str, cli_date: str | None) -> dict:
    set_seeds()

    log.info("[1/5] ingest raw L2: %s", input_glob)
    df = ingest.load_raw(input_glob)
    has_cancel = ingest.detect_cancel_table(df)
    if not has_cancel:
        log.warning("no tick-cancel table detected -> CB features degrade to zero "
                    "(snapshot-only data); pipeline continues")
    data_dates = sorted(df["transaction_date"].astype(str).unique().tolist())
    expected_date = resolve_expected_date(data_dates, cli_date)

    log.info("[2/5] feature extraction")
    matrix = aggregate.build_feature_matrix(df, has_cancel_table=has_cancel)

    log.info("[3/5] Task-1 pattern clustering")
    patterns = cluster.cluster_patterns(matrix)

    log.info("[4/5] Task-2 weak labels + Stage-3 head (stub)")
    weak = label.weak_label_matrix(matrix)
    final = model.apply_model(matrix, weak)

    log.info("[5/5] assemble + validate + write")
    predict_df = postprocess.assemble_predict(final)
    pattern_df = postprocess.assemble_pattern(patterns)
    p2 = postprocess.write_predict_result(predict_df, out_dir, expected_date)
    p1 = postprocess.write_pattern_reco(pattern_df, out_dir, expected_date)

    log.info("done. capital_type=%s intent=%s",
             predict_df["capital_type"].value_counts().to_dict(),
             predict_df["capital_intention"].value_counts().to_dict())
    return {"pattern_reco": p1, "predict_result": p2,
            "n_rows": len(predict_df), "cb_available": has_cancel}


def run_parquet(
    root: str,
    universe_path: str,
    date: str,
    out_dir: str,
    pack_path: str | None = None,
) -> dict:
    """Run the full pipeline from the parquet corpus for one date + universe.

    Parameters
    ----------
    root          : Parquet corpus root (e.g. ``"data/202606"``).
    universe_path : Path to xlsx/CSV listing competition universe codes.
    date          : Trading date ``YYYYMMDD``.
    out_dir       : Output directory for the two CSVs.
    pack_path     : Optional zip destination; when given, calls pack_submit_zip.

    Returns
    -------
    dict with keys: ``pattern_reco``, ``predict_result``, ``n_rows``,
    ``n_missing`` (stocks with no parquet data), and optionally ``submit_zip``.
    """
    from src.pipeline_parquet import build_feature_matrix_for_panel, load_universe_codes
    from src.submit_pack import pack_submit_zip

    set_seeds()

    log.info("[parquet 1/5] load universe: %s", universe_path)
    stock_codes = load_universe_codes(universe_path)
    log.info("[parquet 1/5] universe = %d codes", len(stock_codes))

    log.info("[parquet 2/5] build feature matrix — root=%s date=%s", root, date)
    matrix = build_feature_matrix_for_panel(root, date, stock_codes)
    if matrix.empty:
        log.error("[parquet] empty feature matrix — no output produced")
        return {"pattern_reco": None, "predict_result": None, "n_rows": 0,
                "n_missing": len(stock_codes)}

    present_codes: set[str] = set(matrix.index.get_level_values("stock_code"))
    n_missing = len([c for c in stock_codes if c not in present_codes])
    if n_missing:
        log.warning("[parquet] %d/%d universe codes had no parquet data (omitted)",
                    n_missing, len(stock_codes))

    log.info("[parquet 3/5] Task-1 pattern clustering (method=%s)", config.TASK1_METHOD)
    task1_trajectories = None
    task1_method = "euclidean"
    if config.TASK1_METHOD == "dtw-complete":
        # P5.7 production path: ONE extra batched snapshot read (mirrors
        # scripts/validate_pattern_offline.py's score_one_date) — the per-stock
        # cancel loop inside build_feature_matrix_for_panel is not repeated.
        from src.ingest_parquet import load_parquet as _load_parquet_snapshot
        from src.intraday_trajectory import build_trajectories

        present = sorted({str(c) for c in matrix.index.get_level_values("stock_code")})
        snap = _load_parquet_snapshot(root, date, keys=present)
        traj_by_key = build_trajectories(snap) if snap is not None and not snap.empty else {}
        task1_trajectories = {
            idx: traj_by_key.get((str(idx[0]), str(idx[1])))
            for idx in matrix.index
        }
        if any(v is not None for v in task1_trajectories.values()):
            task1_method = "dtw-complete"
        else:
            log.error(
                "[parquet] TASK1_METHOD=dtw-complete requested but no trajectories "
                "could be built (no snapshot rows) — falling back to euclidean for %s",
                date,
            )
            task1_trajectories = None
    patterns = cluster.cluster_patterns(matrix, trajectories=task1_trajectories, method=task1_method)

    log.info("[parquet 4/5] Task-2 weak labels + Stage-3 head (stub)")
    weak = label.weak_label_matrix(matrix)
    final = model.apply_model(matrix, weak)

    log.info("[parquet 5/5] assemble + validate + write (date pin=%s)", date)
    predict_df = postprocess.assemble_predict(final)
    pattern_df = postprocess.assemble_pattern(patterns)
    p2 = postprocess.write_predict_result(predict_df, out_dir, expected_date=date)
    p1 = postprocess.write_pattern_reco(pattern_df, out_dir, expected_date=date)

    log.info("parquet done. n_rows=%d capital_type=%s intent=%s",
             len(predict_df),
             predict_df["capital_type"].value_counts().to_dict(),
             predict_df["capital_intention"].value_counts().to_dict())

    result: dict = {
        "pattern_reco": p1,
        "predict_result": p2,
        "n_rows": len(predict_df),
        "n_missing": n_missing,
    }

    if pack_path:
        log.info("[parquet] packaging submit.zip → %s", pack_path)
        zip_abs = pack_submit_zip(out_dir, pack_path)
        result["submit_zip"] = zip_abs
        log.info("[parquet] submit.zip created: %s", zip_abs)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AFAC2026 Track-1 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # xlsx path (backward-compatible):
  python main.py --input samples/AFAC2026.xlsx -o outputs/

  # parquet corpus (competition submission):
  python main.py --input parquet:data/202606 \\
                 --universe samples/stock-samples.xlsx \\
                 --date 20260623 \\
                 -o outputs/20260623 \\
                 --pack submit.zip
""",
    )
    parser.add_argument(
        "--input",
        default="samples/AFAC2026.xlsx",
        help=(
            'Raw L2 input. Either an xlsx path/glob (default) or '
            '"parquet:<root>" to read the parquet corpus (e.g. "parquet:data/202606"). '
            'Bare "parquet" defaults root to data/202606.'
        ),
    )
    parser.add_argument(
        "--universe",
        default=None,
        help=(
            "Path to xlsx/CSV listing competition universe codes "
            "(col 股票代码 or stock_code). "
            "Required (or defaults to samples/stock-samples.xlsx) when --input is parquet."
        ),
    )
    parser.add_argument(
        "-o", "--output",
        default="outputs/",
        help="Output directory (relative). Default: outputs/",
    )
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "Expected transaction_date YYYYMMDD. "
            "Required when --input is parquet. "
            "Default for xlsx: inferred from data / yesterday."
        ),
    )
    parser.add_argument(
        "--pack",
        default=None,
        metavar="ZIP_PATH",
        help=(
            "If given, package the two output CSVs into a submit.zip at this path "
            "(both files at archive root, no nested folders). "
            "A bare filename (e.g. 'submit.zip') is written INTO the -o output dir; "
            "pass a path with a directory to place it elsewhere. "
            "Only valid with --input parquet."
        ),
    )
    parser.add_argument(
        "--rich-explanations",
        action="store_true",
        help=(
            "Board-B interpretability explore (default OFF): keep pattern_type / "
            "clusters / Task-2 identical to the euclidean floor, but rewrite each "
            "pattern_explanation to drop the romanized feature token and cite this "
            "stock's same-day percentile on the cluster's dominant feature. "
            "Use for a best-of-day paired A/B vs the floor; not tuned to any board "
            "score (LIS §3.3)."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.rich_explanations:
        config.TASK1_RICH_EXPLANATIONS = True
        log.info("[cli] --rich-explanations ON (Board-B per-stock explanation upgrade)")

    inp = args.input.strip()

    if inp.lower().startswith("parquet"):
        # Parquet path
        if ":" in inp:
            root = inp.split(":", 1)[1].strip() or "data/202606"
        else:
            root = "data/202606"

        universe = args.universe or "samples/stock-samples.xlsx"
        date = args.date
        if not date:
            # Fall back to nightly yesterday
            date = previous_trading_day(_dt.date.today())
            log.warning("--date not supplied; using yesterday=%s", date)

        result = run_parquet(root, universe, date, args.output, pack_path=args.pack)
    else:
        # xlsx / glob path (original path — backward compatible)
        if args.pack:
            log.warning("--pack is only used with parquet input; ignoring for xlsx path")
        result = run(inp, args.output, args.date)

    log.info("outputs: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
