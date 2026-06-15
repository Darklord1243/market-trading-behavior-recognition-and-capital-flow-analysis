"""Lock the competition label vocabularies to their exact submission strings.

These are the highest-stakes constants in the repo: a single wrong byte here
silently disqualifies every submission. capital_type is a 3-class problem
{游资, 量化, 散户}, confirmed by a direct organizer answer in DingTalk that
OVERRIDES the baseline guide (wrong on both the count and the quant string).
"""

import config


def test_capital_types_exact():
    assert config.CAPITAL_TYPES == ["游资", "量化", "散户"]


def test_intention_classes_exact():
    assert config.INTENTION_CLASSES == ["买入", "卖出", "T0交易"]


def test_quant_is_bare_not_long_form():
    # Organizer-confirmed: bare 量化 is correct; 量化机构 is the old (wrong) string.
    assert "量化" in config.CAPITAL_TYPES
    assert "量化机构" not in config.CAPITAL_TYPES
    assert "量化机构" in config.FORBIDDEN_CAPITAL_TYPES


def test_retail_is_a_modelled_class():
    assert "散户" in config.CAPITAL_TYPES
    assert "散户" not in config.FORBIDDEN_CAPITAL_TYPES


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
