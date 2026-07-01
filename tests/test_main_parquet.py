"""Tests for parquet path in main.py — Phase 6.1.

Covers:
  - Universe loader (load_universe_codes) reads codes from xlsx/csv.
  - build_feature_matrix_for_panel wires ingest_parquet correctly.
  - main.py argparse accepts --input parquet:... and routes to parquet runner.
  - Backward compatibility: xlsx path still works.
  - Missing stock codes are logged and omitted (not fatal).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Universe-loader tests
# ---------------------------------------------------------------------------

from src.pipeline_parquet import load_universe_codes


def _write_universe_csv(tmp_path, col_name: str, codes: list[str]) -> str:
    path = str(tmp_path / "universe.csv")
    pd.DataFrame({col_name: codes}).to_csv(path, index=False, encoding="utf-8")
    return path


def _write_universe_xlsx(tmp_path, col_name: str, codes: list[str]) -> str:
    path = str(tmp_path / "universe.xlsx")
    pd.DataFrame({col_name: codes}).to_excel(path, index=False)
    return path


def test_load_universe_codes_from_csv_stock_code_col(tmp_path):
    codes = ["000001.SZ", "600000.SH", "002856.SZ"]
    path = _write_universe_csv(tmp_path, "stock_code", codes)
    result = load_universe_codes(path)
    assert set(result) == set(codes)


def test_load_universe_codes_from_csv_chinese_col(tmp_path):
    codes = ["000001.SZ", "600000.SH"]
    path = _write_universe_csv(tmp_path, "股票代码", codes)
    result = load_universe_codes(path)
    assert set(result) == set(codes)


def test_load_universe_codes_from_xlsx(tmp_path):
    codes = ["000001.SZ", "600000.SH", "300760.SZ"]
    path = _write_universe_xlsx(tmp_path, "股票代码", codes)
    result = load_universe_codes(path)
    assert set(result) == set(codes)


def test_load_universe_codes_strips_empty_and_deduplicates(tmp_path):
    codes = ["000001.SZ", "", "000001.SZ", "nan", "600000.SH"]
    path = _write_universe_csv(tmp_path, "stock_code", codes)
    result = load_universe_codes(path)
    assert "000001.SZ" in result
    assert "600000.SH" in result
    # no empty string or "nan"
    assert "" not in result
    assert "nan" not in result
    assert len(result) == 2  # deduplicated


def test_load_universe_codes_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_universe_codes(str(tmp_path / "does_not_exist.csv"))


def test_load_universe_codes_raises_if_no_known_col(tmp_path):
    path = _write_universe_csv(tmp_path, "unknown_col", ["000001.SZ"])
    with pytest.raises(ValueError):
        load_universe_codes(path)


# ---------------------------------------------------------------------------
# build_feature_matrix_for_panel — tested via parquet fixture from test_ingest_parquet.py
# ---------------------------------------------------------------------------

# Re-use the fixture writer from test_ingest_parquet — import it directly.
_INGEST_TEST = Path(__file__).parent / "test_ingest_parquet.py"


def _import_ingest_test():
    spec = importlib.util.spec_from_file_location("test_ingest_parquet", _INGEST_TEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_feature_matrix_for_panel_returns_non_empty(tmp_path):
    """build_feature_matrix_for_panel returns a non-empty matrix for valid parquet data."""
    ingest_test = _import_ingest_test()
    root = ingest_test.write_tiny_parquet(str(tmp_path))
    date = ingest_test._DATE  # "20260618"

    from src.pipeline_parquet import build_feature_matrix_for_panel

    # The tiny corpus has SZ 000001 and SH 600000
    codes = ["000001.SZ", "600000.SH"]
    matrix = build_feature_matrix_for_panel(root, date, codes)

    assert not matrix.empty, "Expected non-empty feature matrix"
    assert len(matrix) == len(codes), (
        f"Expected {len(codes)} rows; got {len(matrix)}"
    )


def test_build_feature_matrix_for_panel_missing_code_omitted(tmp_path):
    """Stocks with no parquet data are omitted (not fatal); missing count logged."""
    ingest_test = _import_ingest_test()
    root = ingest_test.write_tiny_parquet(str(tmp_path))
    date = ingest_test._DATE

    from src.pipeline_parquet import build_feature_matrix_for_panel

    # 999999.SH has no data in the tiny corpus
    codes = ["000001.SZ", "999999.SH"]
    matrix = build_feature_matrix_for_panel(root, date, codes)

    # 000001.SZ should produce a row; 999999.SH is silently omitted
    present_codes = set(matrix.index.get_level_values("stock_code"))
    assert "000001.SZ" in present_codes
    assert "999999.SH" not in present_codes


# ---------------------------------------------------------------------------
# main.py argparse routing — no heavy work, mock the runner
# ---------------------------------------------------------------------------

def test_main_argparse_parquet_route(monkeypatch, tmp_path):
    """main() with --input parquet:... calls run_parquet, not the xlsx run."""
    import main as main_mod

    calls = []

    def fake_run_parquet(root, universe_path, date, out_dir, pack_path=None):
        calls.append(("parquet", root, universe_path, date, out_dir, pack_path))
        return {"pattern_reco": "p1", "predict_result": "p2", "n_rows": 0}

    def fake_run(input_glob, out_dir, cli_date):
        calls.append(("xlsx", input_glob, out_dir, cli_date))
        return {"pattern_reco": "p1", "predict_result": "p2",
                "n_rows": 1, "cb_available": False}

    monkeypatch.setattr(main_mod, "run_parquet", fake_run_parquet)
    monkeypatch.setattr(main_mod, "run", fake_run)

    rc = main_mod.main([
        "--input", "parquet:data/202606",
        "--universe", "samples/stock-samples.xlsx",
        "--date", "20260623",
        "-o", str(tmp_path),
        "--pack", "submit.zip",
    ])
    assert rc == 0
    assert len(calls) == 1
    kind, root, universe, date, out_dir, pack = calls[0]
    assert kind == "parquet"
    assert root == "data/202606"
    assert date == "20260623"
    assert pack == "submit.zip"


def test_main_argparse_xlsx_backward_compat(monkeypatch, tmp_path):
    """main() with --input samples/... routes to the original xlsx run()."""
    import main as main_mod

    calls = []

    def fake_run(input_glob, out_dir, cli_date):
        calls.append(("xlsx", input_glob, out_dir, cli_date))
        return {"pattern_reco": "p1", "predict_result": "p2",
                "n_rows": 1, "cb_available": False}

    def fake_run_parquet(root, universe_path, date, out_dir, pack_path=None):
        calls.append(("parquet", root))

    monkeypatch.setattr(main_mod, "run", fake_run)
    monkeypatch.setattr(main_mod, "run_parquet", fake_run_parquet)

    rc = main_mod.main([
        "--input", "samples/AFAC2026.xlsx",
        "-o", str(tmp_path),
    ])
    assert rc == 0
    assert len(calls) == 1
    assert calls[0][0] == "xlsx"
