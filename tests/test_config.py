"""Lock the competition label vocabularies to their exact submission strings.

These are the highest-stakes constants in the repo: a single wrong byte here
silently disqualifies every submission. The strings are byte-verified against the
official spec in docs/verification_report.md (findings A1, A1b, A2).
"""

import config


def test_capital_types_exact():
    assert config.CAPITAL_TYPES == ["游资", "量化机构"]


def test_intention_classes_exact():
    assert config.INTENTION_CLASSES == ["买入", "卖出", "T0交易"]


def test_quant_is_full_string_not_truncated():
    # Official requires 量化机构; the bare 量化 leaks into the random sample CSV.
    assert "量化机构" in config.CAPITAL_TYPES
    assert "量化" not in config.CAPITAL_TYPES
    assert "量化" in config.FORBIDDEN_CAPITAL_TYPES


def test_retail_is_forbidden_not_modelled():
    assert "散户" in config.FORBIDDEN_CAPITAL_TYPES
    assert "散户" not in config.CAPITAL_TYPES


def test_oss_thresholds_locked():
    assert config.OSS_THRESHOLDS == {"mega": 50000, "large": 10000, "mid": 1000}


def test_k_range_locked():
    assert config.K_RANGE == (6, 12)


def test_csv_contract_columns():
    assert config.PREDICT_COLUMNS == [
        "stock_code", "transaction_date", "capital_type", "capital_intention"]
    assert config.PATTERN_COLUMNS == [
        "stock_code", "transaction_date", "pattern_type", "pattern_explanation"]
    assert config.CSV_ENCODING == "utf-8-sig"
