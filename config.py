"""Single source of truth for locked competition facts and pipeline constants.

Every other module imports the locked vocabularies and thresholds from here so a
mis-typed label or threshold can never enter the pipeline in two places. These
strings are the *exact* submission values required by the official spec
(baseline-guide.md L78/L129/L424); do not "normalise" or translate them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Locked label vocabularies (exact submission strings — byte-verified)
# ---------------------------------------------------------------------------
# Task 2 capital_type: exactly two classes. NOTE the official required string is
# "量化机构", NOT the bare "量化" that leaks into the random sample CSV.
CAPITAL_TYPES = ["游资", "量化机构"]  # 2 classes, exact strings

# Task 2 capital_intention: exactly three classes. The third slot is "T0交易".
INTENTION_CLASSES = ["买入", "卖出", "T0交易"]  # 3 classes

# `散户` (retail) is a placeholder that physically appears in the random sample
# labels but must NOT be modelled or emitted. Kept here only to assert-against.
FORBIDDEN_CAPITAL_TYPES = ["散户", "量化"]  # 量化 = truncated form, also forbidden

# ---------------------------------------------------------------------------
# OSS — Order Size Segmentation thresholds (SHARES, not amount)
# baseline-guide.md L341-344: Mega >=50000, Large [10000,50000), Mid [1000,10000), Small <1000
# ---------------------------------------------------------------------------
OSS_THRESHOLDS = {"mega": 50000, "large": 10000, "mid": 1000}  # shares

# ---------------------------------------------------------------------------
# Task 1 — bounded-K clustering range
# ---------------------------------------------------------------------------
K_RANGE = (6, 12)          # (min_k, max_k) inclusive — Task-1 bounded K
DEFAULT_K = 8              # baseline default within K_RANGE; downgrades to n_samples

# ---------------------------------------------------------------------------
# CSV output contracts (fixed column order — never reorder)
# ---------------------------------------------------------------------------
PREDICT_COLUMNS = ["stock_code", "transaction_date", "capital_type", "capital_intention"]
PATTERN_COLUMNS = ["stock_code", "transaction_date", "pattern_type", "pattern_explanation"]
PREDICT_FILENAME = "predict_result.csv"
PATTERN_FILENAME = "pattern_reco.csv"
CSV_ENCODING = "utf-8-sig"   # submission requires UTF-8-sig (BOM)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Raw L2 schema expectations (official sample fixture)
# ---------------------------------------------------------------------------
RAW_L2_N_COLS = 65
# Cumulative-intraday fields that must be diff()'d to per-tick increments.
CUMULATIVE_FIELDS = ["volume", "amount", "transactions", "bigordervolume"]
# Beijing-hour trading session bounds (inclusive) used for PI windows.
BEIJING_SESSION_HOURS = (8, 16)

# ---------------------------------------------------------------------------
# Intent gate thresholds (baseline get_intention(), verbatim)
# ---------------------------------------------------------------------------
INTENT_BUY_PCT = 0.6
INTENT_SELL_PCT = 0.6
INTENT_IMBALANCE = 0.08
# Dual-source imbalance blend: 0.4 * first-snapshot + 0.6 * full-day mean.
IMBALANCE_SNAPSHOT_WEIGHT = 0.4
IMBALANCE_FULLDAY_WEIGHT = 0.6
