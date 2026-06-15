"""Output-contract guard tests: the writer/validator must reject malformed output.

Covers brief §9 asserts: exact 4-col order, allowed label vocabularies, expected
transaction_date, and no nulls/blanks. A deliberately malformed frame must raise.
"""

import pandas as pd
import pytest

from src.postprocess import (
    OutputContractError,
    validate_pattern,
    validate_predict,
)


def _good_predict():
    return pd.DataFrame({
        "stock_code": ["603997.SH"],
        "transaction_date": ["20260507"],
        "capital_type": ["游资"],
        "capital_intention": ["T0交易"],
    })


def test_valid_predict_passes():
    validate_predict(_good_predict(), expected_date="20260507")


def test_wrong_column_order_rejected():
    df = _good_predict()[["transaction_date", "stock_code", "capital_type", "capital_intention"]]
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_extra_column_rejected():
    df = _good_predict()
    df["extra"] = 1
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_old_long_form_quant_rejected():
    # INVERTED guard: 量化机构 is the old 2-class string and is now forbidden.
    df = _good_predict()
    df.loc[0, "capital_type"] = "量化机构"
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_bare_quant_accepted():
    # INVERTED guard: bare 量化 is now the correct, accepted quant string.
    df = _good_predict()
    df.loc[0, "capital_type"] = "量化"
    validate_predict(df, expected_date="20260507")


def test_retail_accepted():
    # 散户 is now a valid, modelled class — must pass validation.
    df = _good_predict()
    df.loc[0, "capital_type"] = "散户"
    validate_predict(df, expected_date="20260507")


def test_bad_intention_rejected():
    df = _good_predict()
    df.loc[0, "capital_intention"] = "neutral"
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_null_rejected():
    df = _good_predict()
    df.loc[0, "capital_intention"] = None
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_blank_cell_rejected():
    df = _good_predict()
    df.loc[0, "stock_code"] = "   "
    with pytest.raises(OutputContractError):
        validate_predict(df)


def test_wrong_date_rejected():
    with pytest.raises(OutputContractError):
        validate_predict(_good_predict(), expected_date="20260508")


def test_pattern_open_vocabulary_ok():
    df = pd.DataFrame({
        "stock_code": ["603997.SH"],
        "transaction_date": ["20260507"],
        "pattern_type": ["任意自定义模式名"],          # open vocabulary
        "pattern_explanation": ["对应的业务解释"],
    })
    validate_pattern(df, expected_date="20260507")
