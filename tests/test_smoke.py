"""End-to-end smoke test on the official fixture.

Runs the whole pipeline on samples/AFAC2026.xlsx and checks both CSVs exist, are
4-col / correctly-labelled, UTF-8-sig (BOM), and carry the fixture's date. On the
1-stock-day fixture clustering degrades to K=1 — expected per the baseline guide.
"""

import os

import pandas as pd
import pytest

import config
import main

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "samples", "AFAC2026.xlsx")


pytestmark = pytest.mark.skipif(not os.path.exists(FIXTURE),
                                reason="official fixture not present")


def test_pipeline_emits_valid_csvs(tmp_path):
    out = str(tmp_path)
    result = main.run(FIXTURE, out, cli_date=None)

    assert result["n_rows"] == 1            # 1 stock x 1 day
    assert result["cb_available"] is False  # snapshot-only fixture

    p2 = os.path.join(out, config.PREDICT_FILENAME)
    p1 = os.path.join(out, config.PATTERN_FILENAME)
    assert os.path.exists(p1) and os.path.exists(p2)

    # UTF-8-sig BOM check (submission requires sig)
    with open(p2, "rb") as fh:
        assert fh.read(3) == b"\xef\xbb\xbf"

    predict = pd.read_csv(p2, encoding="utf-8-sig", dtype=str)
    assert list(predict.columns) == config.PREDICT_COLUMNS
    assert predict["capital_type"].isin(config.CAPITAL_TYPES).all()
    assert predict["capital_intention"].isin(config.INTENTION_CLASSES).all()
    assert (predict["transaction_date"] == "20260507").all()

    pattern = pd.read_csv(p1, encoding="utf-8-sig", dtype=str)
    assert list(pattern.columns) == config.PATTERN_COLUMNS
    assert not pattern.isnull().any().any()
