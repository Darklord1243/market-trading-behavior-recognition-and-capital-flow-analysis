# Frozen offline gate baseline — HEAD `dade0d7`

**Date measured:** 2026-06-30
**HEAD:** `dade0d7` — *feat(features): P3.3 RS cadence plumbing — config-gated deal/order clock (default snapshot)*
**Config:** `RS_CADENCE_SOURCE = "snapshot"` (config.py:96) — committed default
**Corpus:** `parquet:data/202606`
**Labels:** `tests/fixtures/validation_labels.csv` (107 rows, 8 trading days 20260616–20260626)
**Python:** `C:/Users/ASUS/anaconda3/python.exe` · `PYTHONIOENCODING=utf-8`

Read-only baseline. No code / config / label / threshold / submission changes.
Subset rows produced with **temporary** date-filtered copies of the fixture
(scratchpad only — not committed); the committed fixture is untouched.

---

## Gate table

| Subset | Date filter | Metric | n | weighted_F1 |
|--------|-------------|--------|---:|------------:|
| **Full CSV** (8 days) | none | capital   | 107 | **0.6413** |
| **Full CSV** (8 days) | none | intention | 102 | **0.6728** |
| **through-0624** | `transaction_date <= 20260624` | capital   | 77 | **0.6773** |
| **through-0625** | `transaction_date <= 20260625` | capital   | 93 | **0.6500** |
| **P2-intent-b** (0616–0623) | `20260616 <= transaction_date <= 20260623` | intention | 64 | **0.6271** |

All three subset gates reproduce the historical frozen floors **exactly**
(0.6773 / 0.6500 / 0.6271). The floors are date-windowed subsets — the default
full-file harness scores all 107/102 rows and so reports the full-CSV numbers,
not the subset floors. The harness has no built-in date-window flag; subsets are
obtained by pre-filtering the label CSV (method below).

---

## Per-class breakdown

**Full CSV — capital (n=107, F1=0.6413)**

| class | P | R | F1 | support |
|-------|---:|---:|---:|---:|
| 游资 | 0.50 | 0.69 | 0.58 | 35 |
| 量化 | 0.72 | 0.61 | 0.66 | 38 |
| 散户 | 0.78 | 0.62 | 0.69 | 34 |

**Full CSV — intention (n=102, F1=0.6728)**

| class | P | R | F1 | support |
|-------|---:|---:|---:|---:|
| 买入 | 0.829 | 0.654 | 0.731 | 52 |
| 卖出 | 0.462 | 0.545 | 0.500 | 11 |
| T0交易 | 0.583 | 0.718 | 0.644 | 39 |

**through-0624 — capital (n=77, F1=0.6773)**

| class | P | R | F1 | support |
|-------|---:|---:|---:|---:|
| 游资 | 0.56 | 0.62 | 0.59 | 24 |
| 量化 | 0.69 | 0.77 | 0.73 | 26 |
| 散户 | 0.81 | 0.63 | 0.71 | 27 |

**through-0625 — capital (n=93, F1=0.6500)**

| class | P | R | F1 | support |
|-------|---:|---:|---:|---:|
| 游资 | 0.51 | 0.63 | 0.57 | 30 |
| 量化 | 0.70 | 0.66 | 0.68 | 32 |
| 散户 | 0.77 | 0.65 | 0.70 | 31 |

**P2-intent-b 0616–0623 — intention (n=64, F1=0.6271)**

| class | P | R | F1 | support |
|-------|---:|---:|---:|---:|
| 买入 | 0.824 | 0.519 | 0.636 | 27 |
| 卖出 | 0.417 | 0.556 | 0.476 | 9 |
| T0交易 | 0.600 | 0.750 | 0.667 | 28 |

---

## Commands / filters used

Full CSV (capital, intention):

```bash
PYTHONIOENCODING=utf-8 python -u scripts/validate_offline.py \
    --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
PYTHONIOENCODING=utf-8 python -u scripts/validate_intent_offline.py \
    --labels tests/fixtures/validation_labels.csv --input parquet:data/202606
```

Subset filters (temp CSV built with awk on field 2 = `transaction_date`, a clean
integer with no embedded commas; header preserved via `NR==1`):

```bash
awk -F, 'NR==1 || $2<=20260624'                  validation_labels.csv > labels_through_0624.csv  # n=77
awk -F, 'NR==1 || $2<=20260625'                  validation_labels.csv > labels_through_0625.csv  # n=93
awk -F, 'NR==1 || ($2>=20260616 && $2<=20260623)' validation_labels.csv > labels_0616_0623.csv    # n=65 → 64 intent
```

Then the same two harness scripts with `--labels <temp.csv>`.

Notes:
- Default `--norm-universe` (none) → rank normalization panel = the labeled keys
  in the (possibly filtered) CSV. Each subset is therefore self-contained: filtering
  the label file also defines its rank panel, matching how the original floors were set.
- intention drops a few rows vs capital (no scorable `capital_intention`):
  full 107→102; 0616–0623 65→64.
- Full-CSV numbers were produced this session at HEAD `dade0d7`'s tree state
  (the commit staged exactly that working tree; code is byte-identical). Subset
  numbers are fresh runs against the same HEAD.

---

## Provenance vs P3.3

`dade0d7` is config-gated plumbing at `RS_CADENCE_SOURCE="snapshot"`; the snapshot
code path in `_rs_features` is byte-identical to the pre-P3.3 parent (`6aa50dc`).
These baselines are therefore the genuine snapshot-path gates and should hold until
a future slice re-derives RS rank directions and flips the config (see
[`p3.3-rs-cadence-resource.md`](./p3.3-rs-cadence-resource.md)).
