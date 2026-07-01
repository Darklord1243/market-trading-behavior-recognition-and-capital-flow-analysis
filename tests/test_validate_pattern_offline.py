"""Smoke tests for scripts/validate_pattern_offline.py — Slice-1 Task-1 gate.

Offline / label-free clustering-quality harness.  Reuses the tiny real-schema
parquet fixture writer from test_ingest_parquet.py so the smoke test runs without
the ~13 GB corpus.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).parent.parent
_HARNESS_PATH = _ROOT / "scripts" / "validate_pattern_offline.py"
_DATE = "20260618"  # matches write_tiny_parquet


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ingest_test():
    return _import_module("test_ingest_parquet", _ROOT / "tests" / "test_ingest_parquet.py")


def _harness():
    return _import_module("validate_pattern_offline", _HARNESS_PATH)


def _write_universe(tmp_path, codes):
    p = tmp_path / "universe.csv"
    pd.DataFrame({"stock_code": codes}).to_csv(p, index=False, encoding="utf-8")
    return str(p)


def test_score_one_date_returns_components(tmp_path):
    """The per-date scorer runs on a real-schema tiny corpus and returns every
    board-component the report needs — no fabricated blended score."""
    ingest = _ingest_test()
    root = ingest.write_tiny_parquet(str(tmp_path))
    harness = _harness()
    codes = ["000001.SZ", "600000.SH"]

    d = harness.score_one_date(root, codes, _DATE)
    assert d is not None
    for key in ("date", "panel_n", "best_k", "silhouette", "silhouette_daily",
                "ch", "wasserstein_sep", "dtw_sep", "n_clusters", "degenerate"):
        assert key in d, f"missing component {key!r}"
    assert d["date"] == _DATE
    assert d["panel_n"] >= 1


def test_run_exit_zero_on_valid_date(tmp_path):
    """CLI returns 0 on a valid single date."""
    ingest = _ingest_test()
    root = ingest.write_tiny_parquet(str(tmp_path))
    harness = _harness()
    universe = _write_universe(tmp_path, ["000001.SZ", "600000.SH"])

    rc = harness.run([
        "--input", f"parquet:{root}",
        "--date", _DATE,
        "--universe", universe,
    ])
    assert rc == 0


def test_discover_dates_finds_real_layout(tmp_path):
    """_discover_dates reads dates from the real root/<stream>/YYYYMMDD layout."""
    ingest = _ingest_test()
    root = ingest.write_tiny_parquet(str(tmp_path))
    harness = _harness()
    assert _DATE in harness._discover_dates(root)


def test_run_all_dates_smoke(tmp_path):
    """--all-dates discovers the fixture date and scores it (exit 0)."""
    ingest = _ingest_test()
    root = ingest.write_tiny_parquet(str(tmp_path))
    harness = _harness()
    universe = _write_universe(tmp_path, ["000001.SZ", "600000.SH"])
    rc = harness.run(["--input", f"parquet:{root}", "--all-dates", "--universe", universe])
    assert rc == 0


def test_run_fails_loud_on_missing_data(tmp_path):
    """CLI returns 1 (fail loud) when the requested date has no parquet data."""
    ingest = _ingest_test()
    root = ingest.write_tiny_parquet(str(tmp_path))
    harness = _harness()
    universe = _write_universe(tmp_path, ["000001.SZ"])

    rc = harness.run([
        "--input", f"parquet:{root}",
        "--date", "20991231",  # no data for this date
        "--universe", universe,
    ])
    assert rc == 1
