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
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import random
import sys

import numpy as np

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AFAC2026 Track-1 pipeline")
    parser.add_argument("--input", default="samples/AFAC2026.xlsx",
                        help="raw L2 xlsx path or glob (relative)")
    parser.add_argument("-o", "--output", default="outputs/",
                        help="output directory (relative)")
    parser.add_argument("--date", default=None,
                        help="expected transaction_date YYYYMMDD; default = data's date / yesterday")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = run(args.input, args.output, args.date)
    log.info("outputs: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
