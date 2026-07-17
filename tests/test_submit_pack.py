"""Tests for submit.zip packager — Phase 6.1.

Verifies that pack_submit_zip produces a zip with exactly two root-level CSV
entries (predict_result.csv + pattern_reco.csv), no nested folders, UTF-8-sig.
"""

from __future__ import annotations

import os
import zipfile

import pandas as pd
import pytest

from config import PREDICT_FILENAME, PATTERN_FILENAME, CSV_ENCODING, PREDICT_COLUMNS, PATTERN_COLUMNS
from src.submit_pack import pack_submit_zip


def _make_predict_csv(tmp_path: str) -> str:
    """Write a minimal valid predict_result.csv to tmp_path and return path."""
    df = pd.DataFrame({
        "stock_code": ["000001.SZ", "600000.SH"],
        "transaction_date": ["20260623", "20260623"],
        "capital_type": ["游资", "量化"],
        "capital_intention": ["买入", "T0交易"],
    })
    path = os.path.join(tmp_path, PREDICT_FILENAME)
    df.to_csv(path, index=False, encoding=CSV_ENCODING, lineterminator="\n")
    return path


def _make_pattern_csv(tmp_path: str) -> str:
    """Write a minimal valid pattern_reco.csv to tmp_path and return path."""
    df = pd.DataFrame({
        "stock_code": ["000001.SZ", "600000.SH"],
        "transaction_date": ["20260623", "20260623"],
        "pattern_type": ["趋势跟踪", "高频T0"],
        "pattern_explanation": ["解释A", "解释B"],
    })
    path = os.path.join(tmp_path, PATTERN_FILENAME)
    df.to_csv(path, index=False, encoding=CSV_ENCODING, lineterminator="\n")
    return path


def test_pack_submit_zip_creates_zip_with_two_root_csvs(tmp_path):
    """pack_submit_zip must produce a zip with exactly 2 root-level CSV entries."""
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir)
    _make_predict_csv(out_dir)
    _make_pattern_csv(out_dir)

    zip_path = str(tmp_path / "submit.zip")
    pack_submit_zip(out_dir, zip_path)

    assert os.path.exists(zip_path), "submit.zip was not created"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    # Exactly two entries, both at root (no "/" in name = no nested folder)
    assert set(names) == {PREDICT_FILENAME, PATTERN_FILENAME}, (
        f"Expected exactly {{{PREDICT_FILENAME}, {PATTERN_FILENAME}}} at root; got {names}"
    )
    # No entry should contain a path separator
    for name in names:
        assert "/" not in name and "\\" not in name, f"Entry {name!r} has nested path"


def test_pack_submit_zip_raises_if_csv_missing(tmp_path):
    """pack_submit_zip raises FileNotFoundError if one of the required CSVs is absent."""
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir)
    _make_predict_csv(out_dir)
    # pattern_reco.csv intentionally NOT created

    zip_path = str(tmp_path / "submit.zip")
    with pytest.raises(FileNotFoundError):
        pack_submit_zip(out_dir, zip_path)


def test_pack_submit_zip_bare_filename_lands_in_out_dir(tmp_path, monkeypatch):
    """A bare filename zip_path (no directory) must resolve relative to out_dir,
    NOT the current working directory."""
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir)
    _make_predict_csv(out_dir)
    _make_pattern_csv(out_dir)

    # Simulate `main.py --pack submit.zip` run from an unrelated CWD.
    cwd = tmp_path / "cwd"
    os.makedirs(cwd)
    monkeypatch.chdir(cwd)

    returned = pack_submit_zip(out_dir, "submit.zip")

    expected = os.path.join(out_dir, "submit.zip")
    assert os.path.exists(expected), "bare filename should land the zip inside out_dir"
    assert os.path.abspath(returned) == os.path.abspath(expected)
    # Must NOT leak into the current working directory.
    assert not os.path.exists(os.path.join(str(cwd), "submit.zip")), (
        "zip leaked into CWD instead of out_dir"
    )


def test_pack_submit_zip_path_with_dir_honored_as_is(tmp_path):
    """A zip_path containing a directory component is honored verbatim (not
    re-rooted under out_dir) — backward-compatible with explicit paths."""
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir)
    _make_predict_csv(out_dir)
    _make_pattern_csv(out_dir)

    explicit = str(tmp_path / "dist" / "submit.zip")
    returned = pack_submit_zip(out_dir, explicit)

    assert os.path.abspath(returned) == os.path.abspath(explicit)
    assert os.path.exists(explicit)


def test_pack_submit_zip_contents_readable(tmp_path):
    """ZIP contents must be readable as UTF-8-sig CSVs with the correct columns."""
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir)
    _make_predict_csv(out_dir)
    _make_pattern_csv(out_dir)

    zip_path = str(tmp_path / "submit.zip")
    pack_submit_zip(out_dir, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(PREDICT_FILENAME) as fh:
            # UTF-8-sig BOM
            raw = fh.read()
            assert raw[:3] == b"\xef\xbb\xbf", "predict_result.csv must have UTF-8-sig BOM"
        with zf.open(PATTERN_FILENAME) as fh:
            raw2 = fh.read()
            assert raw2[:3] == b"\xef\xbb\xbf", "pattern_reco.csv must have UTF-8-sig BOM"
