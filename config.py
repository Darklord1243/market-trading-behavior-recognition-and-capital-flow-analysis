"""Single source of truth for locked competition facts and pipeline constants.

Every other module imports the locked vocabularies and thresholds from here so a
mis-typed label or threshold can never enter the pipeline in two places. These
strings are the *exact* submission values required by the official spec
(baseline-guide.md L78/L129/L424); do not "normalise" or translate them.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Locked label vocabularies (exact submission strings)
# ---------------------------------------------------------------------------
# Task 2 capital_type: exactly THREE classes. Confirmed by a direct organizer
# answer in DingTalk, which OVERRIDES the baseline guide (the guide was wrong on
# both the count — it said 2 — and the string — it said "量化机构"). The correct
# quant string is the bare "量化", NOT "量化机构"; 散户 (retail) is a real,
# modelled class — not a placeholder. Ordering: 量化 takes the slot the old
# "量化机构" held; 散户 is appended (rules.py maps scores by these indices).
CAPITAL_TYPES = ["游资", "量化", "散户"]  # 3 classes, exact strings

# Task 2 capital_intention: exactly three classes. The third slot is "T0交易".
INTENTION_CLASSES = ["买入", "卖出", "T0交易"]  # 3 classes

# "量化机构" is the OLD (wrong) 2-class quant string. It must never be emitted now
# that the organizer confirmed the bare "量化". Kept here only to assert-against.
FORBIDDEN_CAPITAL_TYPES = ["量化机构"]  # old 2-class string — now invalid

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
# CB (Cancel-Behaviour) thresholds
# ---------------------------------------------------------------------------
# Fast-cancel interval threshold (milliseconds).
# NOTE: this is an **inter-cancel interval proxy** — the time between consecutive
# cancel events in the cancel stream — NOT the true order→cancel latency (which
# requires matching each cancel to its originating order via ref columns such as
# 叫买序号/叫卖序号/交易所委托号 that read_cancel_frame does not currently expose).
# True order→cancel latency is deferred until read_cancel_frame is extended to
# carry order-ref columns (Track L-b stretch goal).
CB_FAST_CANCEL_MS: int = 500  # cancel pairs with inter-cancel interval < 500ms

# ---------------------------------------------------------------------------
# RS (Rhythm/Sequence) thresholds
# ---------------------------------------------------------------------------
# Absolute burst threshold (milliseconds).  Intervals shorter than this count
# as "burst" (rapid-fire) submissions.  Using an absolute threshold avoids the
# scale-free saturation problem of the old 0.25×mean definition (which collapses
# to 1.0 when mean≈0, i.e. the dtype-bug state).  Baseline reference: 100 ms.
RS_BURST_THRESHOLD_MS: int = 100

# ---------------------------------------------------------------------------
# TRD — deal-stream print-size heterogeneity (Feature B.2)
# ---------------------------------------------------------------------------
# Log-spaced size-bin EDGES (SHARES) for trd_size_entropy. Chosen from A-share lot
# structure — board lot = 100 shares; edges double each step (powers of 2 ×100) so
# each bin spans roughly one octave of order size. A GLOBAL constant from
# microstructure reasoning (the lot ladder), NOT fitted to the 24 labels (LIS §3 #3).
# np.digitize maps each genuine-trade print into one of len(TRD_SIZE_BINS)+1 bins; the
# entropy denominator is ln(total bins) FIXED, so a few repeated clip sizes stay LOW.
TRD_SIZE_BINS = [100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600, 51200]

# ---------------------------------------------------------------------------
# Intent gate thresholds (baseline get_intention(), verbatim)
# ---------------------------------------------------------------------------
INTENT_BUY_PCT = 0.6
INTENT_SELL_PCT = 0.6
INTENT_IMBALANCE = 0.08
# Dual-source imbalance blend: 0.4 * first-snapshot + 0.6 * full-day mean.
IMBALANCE_SNAPSHOT_WEIGHT = 0.4
IMBALANCE_FULLDAY_WEIGHT = 0.6
