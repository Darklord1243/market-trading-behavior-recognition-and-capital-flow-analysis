"""Canonical label mapping + CSV writers with audit-contract guards.

The writers FAIL LOUDLY (brief §9): every output is validated for exact column set
and order, allowed label vocabularies, expected transaction_date, UTF-8-sig encoding,
and no nulls/blank lines before a single byte is written. A malformed frame raises
`OutputContractError` rather than producing a silently-invalid submission.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from config import (
    CAPITAL_TYPES,
    CSV_ENCODING,
    FORBIDDEN_CAPITAL_TYPES,
    INTENTION_CLASSES,
    PATTERN_COLUMNS,
    PATTERN_FILENAME,
    PREDICT_COLUMNS,
    PREDICT_FILENAME,
)

log = logging.getLogger(__name__)


class OutputContractError(AssertionError):
    """Raised when an output frame violates the submission contract."""


def _check_common(df: pd.DataFrame, columns: list[str], expected_date: str | None):
    # exact columns, exact order
    if list(df.columns) != columns:
        raise OutputContractError(
            f"columns {list(df.columns)} != required {columns} (order matters)"
        )
    # no nulls anywhere
    if df.isnull().any().any():
        bad = df.columns[df.isnull().any()].tolist()
        raise OutputContractError(f"null values present in columns: {bad}")
    # no blank/empty string cells (would render as blank lines / empty fields)
    for col in df.columns:
        if df[col].astype(str).str.strip().eq("").any():
            raise OutputContractError(f"blank string cell in column: {col}")
    # transaction_date is the expected day
    if expected_date is not None:
        dates = df["transaction_date"].astype(str).unique().tolist()
        if dates != [str(expected_date)]:
            raise OutputContractError(
                f"transaction_date {dates} != expected [{expected_date!r}]"
            )


def validate_predict(df: pd.DataFrame, expected_date: str | None = None):
    """Assert predict_result.csv contract; raise OutputContractError on any breach."""
    _check_common(df, PREDICT_COLUMNS, expected_date)
    bad_type = set(df["capital_type"]) - set(CAPITAL_TYPES)
    if bad_type:
        raise OutputContractError(f"capital_type not in {CAPITAL_TYPES}: {bad_type}")
    leaked = set(df["capital_type"]) & set(FORBIDDEN_CAPITAL_TYPES)
    if leaked:
        raise OutputContractError(
            "量化机构 is the OLD 2-class string; correct value is bare 量化 "
            f"(organizer-confirmed 3-class). Forbidden value(s) present: {leaked}"
        )
    bad_intent = set(df["capital_intention"]) - set(INTENTION_CLASSES)
    if bad_intent:
        raise OutputContractError(
            f"capital_intention not in {INTENTION_CLASSES}: {bad_intent}"
        )


def validate_pattern(df: pd.DataFrame, expected_date: str | None = None):
    """Assert pattern_reco.csv contract (pattern_type is open vocabulary)."""
    _check_common(df, PATTERN_COLUMNS, expected_date)


def _write_csv(df: pd.DataFrame, path: str):
    # index=False -> no extra column; UTF-8-sig BOM; \n line terminator (no blank lines)
    df.to_csv(path, index=False, encoding=CSV_ENCODING, lineterminator="\n")


def write_predict_result(df: pd.DataFrame, out_dir: str, expected_date: str | None = None) -> str:
    validate_predict(df, expected_date)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, PREDICT_FILENAME)
    _write_csv(df[PREDICT_COLUMNS], path)
    log.info("wrote %s (%d rows)", path, len(df))
    return path


def write_pattern_reco(df: pd.DataFrame, out_dir: str, expected_date: str | None = None) -> str:
    validate_pattern(df, expected_date)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, PATTERN_FILENAME)
    _write_csv(df[PATTERN_COLUMNS], path)
    log.info("wrote %s (%d rows)", path, len(df))
    return path


def assemble_predict(labels: pd.DataFrame) -> pd.DataFrame:
    """Flatten a (stock_code, transaction_date)-indexed label frame to the 4-col output."""
    out = labels.reset_index()[["stock_code", "transaction_date"] +
                               ["capital_type", "capital_intention"]]
    return out[PREDICT_COLUMNS]


def assemble_pattern(patterns: pd.DataFrame) -> pd.DataFrame:
    """Flatten a (stock_code, transaction_date)-indexed pattern frame to the 4-col output."""
    out = patterns.reset_index()[["stock_code", "transaction_date"] +
                                 ["pattern_type", "pattern_explanation"]]
    return out[PATTERN_COLUMNS]
