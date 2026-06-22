# Sonnet execution prompt — Feature B slice B.2 (deal-stream `trd_size_entropy`)

> **Status:** Ready to run.
> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates.*
> **Spec:** `docs/superpowers/specs/2026-06-22-retail-dispersion-feature-design.md` §B.2, §2, §5
> **Plan:** `docs/superpowers/plans/2026-06-22-retail-dispersion-feature.md` — **Task B.2 only**
> **Prior slice (shipped):** B.0 (`bcc97f9`) — `DIMS_RETAIL` rewired to diffuseness priors + relative win margin.
> **Out of scope:** B.1 composite, RS-on-逐笔, Track L-c, label edits, threshold fitting, `main.py`, committing.

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **Feature B slice B.2 only** — add a deal-stream
feature **`trd_size_entropy`** that measures the **size-VALUE heterogeneity** of genuine-trade prints (散户 =
many heterogeneous human sizes → HIGH; 量化 = a few repeated algo clip sizes → LOW; 游资 = mega-skewed → low),
plumb the per-print deal sizes from the `逐笔成交` parquet stream into `compute_daily_features` (mirroring the
existing `cancel_lookup` seam), and wire `trd_size_entropy` into `DIMS_RETAIL`.

**Read (minimal — do NOT re-read the whole repo or LIS end-to-end):**
- `docs/superpowers/plans/2026-06-22-retail-dispersion-feature.md` — **Task B.2** (the four scoped tasks)
- `docs/superpowers/specs/...retail-dispersion-feature-design.md` — **§B.2** (the size-VALUE-not-volume lock), §2 (compliance), §5 (gate)
- `src/ingest_parquet.py` — `_bigorder_maps` (the existing `deal` read you extend), `read_cancel_frame_parquet`, `load_parquet`
- `src/aggregate.py` — `build_feature_matrix` (`cancel_lookup` threading — you mirror it with `deal_lookup`)
- `src/features.py` — `_oss_features` / `_cb_features` (wrapper style), `compute_daily_features` (the integration point)
- `src/rules.py` — `DIMS_RETAIL`
- `scripts/validate_offline.py` — `_build_parquet_matrix` (lines ~222-251; you thread `deal_lookup` here)

Do **not** read `main.py`, `label.py`, `normalize.py`, or any Phase 3+ code.

---

# LIS context (trust these locks; do not re-derive)

| Item | Status |
|---|---|
| **Eval class set** | 3-class `{游资, 量化, 散户}`; 散户 scores in weighted F1. |
| **Active gate (to beat)** | `parquet:data/202606`, n=24: `weighted_f1 = 0.6094`, 散户 R = **4/10 (0.40)**. This is **B.0's shipped number** — the B.2 prior, NOT 0.3371. |
| **Scorer mechanics** | `_class_score(feat, dims, cb_available)` = mean over dims of each dim's vote. `(key, high_supports, is_cb)`: votes `clip01(feat[key])` if `high_supports` else `1 - clip01`; an **absent** dim (missing/NaN, or `is_cb=True` while `cb_available` false) votes **0.5 (NEUTRAL)**. 游资/量化 dim sets are **unchanged** in B.2. |
| **Current `DIMS_RETAIL`** | `[("oss_small_count_pct", True, False), ("oss_mega_count_pct", False, False), ("cb_fast_cancel_ratio", False, True)]` — 3 dims. B.2 **appends** `("trd_size_entropy", True, False)` → 4 dims. |
| **Deal stream** | `逐笔成交` (`_STREAM_DIR["deal"]`). Genuine trades = `Side ∈ {0,1}`; `Volume` = print size in **shares**. Cancels are NOT in this stream (they live in `order.OrderType ∈ {-1,-11}`), so "exclude cancels" here = keep `Side ∈ {0,1}` only. `_bigorder_maps` already reads this stream. |
| **Plumbing seam** | The deal sizes are NOT in the cleaned snapshot frame. Thread them as a `deal_lookup` dict `(stock_code, date_str) -> [print volumes]`, exactly mirroring `cancel_lookup`: built in `validate_offline._build_parquet_matrix`, passed through `aggregate.build_feature_matrix` → `compute_daily_features(deal_volumes=...)`. The xlsx/snapshot path passes `deal_volumes=None` → feature `0.0`. |

---

# Hard rules (auto-DQ if broken)

1. **Intraday-only, no label feedback** — do **not** read or edit `tests/fixtures/validation_labels.csv`. The
   feature is computed offline in the gate harness, never in `main.py`'s inference path.
2. **No threshold/bin fitting to labels** — `TRD_SIZE_BINS` is a **global constant chosen from A-share lot
   structure** (board lot = 100 shares; doubling edges), documented as **NOT** fitted to the 24 labels. Do not
   sweep bins or the entropy normalization against proxy-F1.
3. **Measure SIZE-VALUE heterogeneity, NOT volume concentration** (spec §B.2). 量化 and 散户 both make many
   small prints — a volume-HHI does **not** separate them. The axis is the **distribution of print size
   values**: few repeated clip sizes → LOW; many distinct human sizes → HIGH.
4. **游资/量化 dim sets unchanged** — only `DIMS_RETAIL` gains the entropy dim.
5. **TDD** — write the failing test first, watch it fail, then implement.
6. **Do not commit** (the Opus lead commits after the gate). Do not implement B.1 / RS-on-逐笔.

---

# Design lock — entropy normalization (READ THIS; the spec phrasing is ambiguous)

The spec writes `H = -Σ p_i ln p_i / ln(B)`. **Normalize by `ln(total bins)` — a FIXED denominator — NOT
`ln(non-empty bins)`.** Under non-empty normalization a 量化 name repeating exactly **two** clip sizes would
score `ln2/ln2 = 1.0` (maximally "heterogeneous"), which inverts the signal. With the fixed total-bins
denominator, a 2-clip distribution stays LOW (`ln2/ln(B_total)`), which is the whole point. A **design-lock
test** must pin this (a 2-clip input scores low, not 1.0). Document this resolution in your report.

---

# What to build (TDD — concrete code below)

## Step 1 — `config.py`: add `TRD_SIZE_BINS`

```python
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
```

## Step 2 — `src/features.py`: the feature (red-first)

First add failing tests to `tests/test_features.py`, run them, watch them fail, then implement.

**Tests (hand-computed; `B_total = len(TRD_SIZE_BINS)+1 = 11`, `ln 11 ≈ 2.398`):**

```python
from src.features import _trd_size_entropy_features, compute_daily_features

def test_trd_size_entropy_repeated_clip_is_zero():
    # One repeated clip size -> a single occupied bin -> H = 0 -> entropy 0.0.
    out = _trd_size_entropy_features([100.0] * 20)
    assert out["trd_size_entropy"] == 0.0

def test_trd_size_entropy_two_clips_stays_low():
    # DESIGN LOCK: two repeated clip sizes (量化) must stay LOW, NOT 1.0.
    # H = ln2 / ln11 ~= 0.693 / 2.398 ~= 0.289.
    out = _trd_size_entropy_features([100.0] * 10 + [200.0] * 10)
    assert 0.0 < out["trd_size_entropy"] < 0.35

def test_trd_size_entropy_heterogeneous_is_high():
    # Six distinct sizes across six bins (散户) -> H = ln6 / ln11 ~= 0.747.
    out = _trd_size_entropy_features([150.0, 300.0, 600.0, 1200.0, 2400.0, 4800.0])
    assert out["trd_size_entropy"] > 0.6

def test_trd_size_entropy_heterogeneous_beats_two_clip():
    lo = _trd_size_entropy_features([100.0] * 10 + [200.0] * 10)["trd_size_entropy"]
    hi = _trd_size_entropy_features([150.0, 300.0, 600.0, 1200.0, 2400.0, 4800.0])["trd_size_entropy"]
    assert hi > lo

def test_trd_size_entropy_mega_skewed_is_low():
    # 游资: a wall of mega prints + a couple of small ones -> skewed -> low.
    out = _trd_size_entropy_features([80000.0] * 18 + [100.0, 200.0])
    assert out["trd_size_entropy"] < 0.30

def test_trd_size_entropy_empty_and_degenerate_are_zero():
    assert _trd_size_entropy_features([])["trd_size_entropy"] == 0.0
    assert _trd_size_entropy_features(None)["trd_size_entropy"] == 0.0
    assert _trd_size_entropy_features([500.0])["trd_size_entropy"] == 0.0   # < 2 prints

def test_trd_size_entropy_excludes_nonpositive():
    # Non-positive / non-finite sizes are dropped before binning.
    a = _trd_size_entropy_features([150.0, 300.0, 600.0, 1200.0, 2400.0, 4800.0])["trd_size_entropy"]
    b = _trd_size_entropy_features([0.0, -5.0, 150.0, 300.0, 600.0, 1200.0, 2400.0, 4800.0])["trd_size_entropy"]
    assert a == b

def test_compute_daily_features_no_deal_volumes_is_zero(snapshot_group):
    # Backward-compat: snapshot/xlsx path (deal_volumes=None) -> trd_size_entropy 0.0.
    feat = compute_daily_features(snapshot_group)            # no deal_volumes kwarg
    assert feat["trd_size_entropy"] == 0.0
```

> For `snapshot_group`, reuse whatever minimal cleaned-group fixture the existing `test_features.py` already
> uses for `compute_daily_features` (do not invent a new heavy fixture).

**Implementation in `src/features.py`** (place near `_oss_features`; import `TRD_SIZE_BINS` from `config`):

```python
def _trd_size_entropy(volumes) -> float:
    """Normalized Shannon entropy of genuine-trade print SIZES over the log-spaced
    ``TRD_SIZE_BINS`` ladder, in [0, 1].

    Measures size-VALUE heterogeneity (spec §B.2): 散户 = many distinct human sizes
    (HIGH); 量化 = a few repeated algo clip sizes (LOW); 游资 = mega-skewed (low).
    The denominator is ``ln(total_bins)`` FIXED — NOT ``ln(non-empty bins)`` — so a
    2-clip distribution stays low (it would be 1.0 under non-empty normalisation).
    Empty / single-print / degenerate input -> 0.0.
    """
    if volumes is None:
        return 0.0
    v = np.asarray(list(volumes), dtype=float)
    v = v[np.isfinite(v) & (v > 0.0)]
    if v.size < 2:
        return 0.0
    n_bins = len(TRD_SIZE_BINS) + 1
    idx = np.digitize(v, TRD_SIZE_BINS)                  # 0 .. n_bins-1
    counts = np.bincount(idx, minlength=n_bins).astype(float)
    p = counts[counts > 0]
    p = p / p.sum()
    h = float(-(p * np.log(p)).sum())
    denom = np.log(n_bins)
    return 0.0 if denom <= 0 else float(min(1.0, max(0.0, h / denom)))


def _trd_size_entropy_features(volumes) -> dict:
    """Wrapper mirroring the ``_x_features`` family."""
    return {"trd_size_entropy": _trd_size_entropy(volumes)}
```

Wire it into `compute_daily_features` — add the parameter and the update:

```python
def compute_daily_features(
    group: pd.DataFrame,
    has_cancel_table: bool = False,
    cancel_df: "pd.DataFrame | None" = None,
    deal_volumes=None,                      # NEW: per-print genuine-trade sizes (B.2)
) -> dict:
    ...
    feat.update(_cb_features(group, has_cancel_table, cancel_df=cancel_df))
    feat.update(_trd_size_entropy_features(deal_volumes))    # NEW
    ...
```

(The existing inf/nan scrub at the end keeps the value a finite float.)

## Step 3 — `src/ingest_parquet.py`: surface per-print deal sizes (red-first)

Add tests to `tests/test_ingest_parquet.py` using a tiny synthetic `deal` parquet (mirror however the existing
`test_ingest_parquet.py` builds fixture parquet frames — reuse its helper if present):

```python
def test_deal_size_maps_keeps_genuine_prints(tmp_deal_corpus):
    # Side in {0,1} kept; other Side excluded; per-secu volume lists returned.
    maps = _deal_size_maps(root, date, [secu])
    assert sorted(maps[secu]) == [100.0, 200.0, 300.0]      # only the 3 genuine trades

def test_read_deal_sizes_parquet_returns_lookup(tmp_deal_corpus):
    lk = read_deal_sizes_parquet(root, date, [code])
    assert (code, date) in lk
    assert all(v > 0 for v in lk[(code, date)])

def test_read_deal_sizes_parquet_missing_stock_is_empty(tmp_deal_corpus):
    lk = read_deal_sizes_parquet(root, date, ["000001.SZ"])  # no prints
    assert lk[("000001.SZ", date)] == []
```

Implementation (place near `_bigorder_maps`; reuse `_read_stream`, `stock_code_to_secu`):

```python
def _deal_size_maps(
    root: str, date: str, secu_codes: Optional[list[int]]
) -> dict[int, list[float]]:
    """``{secu: [genuine-trade print volumes]}`` from the ``deal`` stream.

    Mirrors :func:`_bigorder_maps`' read of the same ``逐笔成交`` stream, but keeps
    EVERY genuine print's size (no BIG_ORDER threshold, no time-binning) — the raw
    size distribution feeds :func:`features._trd_size_entropy`. Cancels/auction
    (``Side ∉ {0,1}``) and non-positive volumes are excluded.
    """
    df = _read_stream(root, date, "deal", secu_codes, columns=["SecuCode", "Side", "Volume"])
    if df is None or df.empty:
        return {}
    side = pd.to_numeric(df["Side"], errors="coerce")
    vol = pd.to_numeric(df["Volume"], errors="coerce")
    keep = df[side.isin((0, 1)) & (vol > 0)].copy()
    if keep.empty:
        return {}
    keep["_v"] = pd.to_numeric(keep["Volume"], errors="coerce")
    out: dict[int, list[float]] = {}
    for secu, grp in keep.groupby("SecuCode"):
        out[int(secu)] = grp["_v"].dropna().astype(float).tolist()
    return out


def read_deal_sizes_parquet(root: str, date: str, keys: list[str]) -> dict:
    """Public ``deal_lookup`` builder — ``{(stock_code, date_str): [print volumes]}``.

    The deal-stream mirror of the cancel_lookup pattern: ONE batch ``deal`` read for
    all *keys*. Stocks with no genuine prints map to an empty list (backward-safe).
    """
    secus = [stock_code_to_secu(k) for k in keys] if keys else None
    maps = _deal_size_maps(root, date, secus)
    out: dict = {}
    for k in (keys or []):
        out[(k, str(date))] = maps.get(stock_code_to_secu(k), [])
    return out
```

## Step 4 — `src/aggregate.py`: thread `deal_lookup` (mirror `cancel_lookup`)

```python
def build_feature_matrix(
    df: pd.DataFrame,
    has_cancel_table: bool = False,
    cancel_lookup: Optional[dict] = None,
    deal_lookup: Optional[dict] = None,        # NEW (B.2): {(code, date): [print volumes]}
) -> pd.DataFrame:
    ...
    for (code, date), group in df.groupby(["stock_code", "transaction_date"], sort=True):
        cancel_df = None
        if cancel_lookup is not None:
            cancel_df = cancel_lookup.get((code, str(date)))
        deal_volumes = None
        if deal_lookup is not None:
            deal_volumes = deal_lookup.get((code, str(date)))
        feat = compute_daily_features(
            group,
            has_cancel_table=has_cancel_table,
            cancel_df=cancel_df,
            deal_volumes=deal_volumes,         # NEW
        )
```

Update the docstring's "Cancel data plumbing" note to mention `deal_lookup` analogously (one or two lines).

## Step 5 — `scripts/validate_offline.py`: build & thread `deal_lookup` in `_build_parquet_matrix`

> **NOTE TO LEAD (do not silently skip):** this file is REQUIRED for B.2 even though the orchestrator's scope
> table omitted it — without it, `deal_volumes` is `None` on the gated path and `trd_size_entropy` is `0.0`
> everywhere, so the gate cannot move. This is the offline-gate analogue of the `cancel_lookup` wiring already
> present here. `main.py` inference wiring of `deal_lookup` is **deferred** (out of B.2 scope).

In `_build_parquet_matrix` (around lines 230-251):

```python
    from src.ingest_parquet import (
        load_parquet,
        read_cancel_frame_parquet,
        read_deal_sizes_parquet,           # NEW
    )
    ...
    deal_lookup = read_deal_sizes_parquet(root, date, panel)     # NEW (one batch deal read)

    return aggregate.build_feature_matrix(
        df, has_cancel_table=True, cancel_lookup=cancel_lookup, deal_lookup=deal_lookup
    )
```

## Step 6 — `src/rules.py`: wire the dim into `DIMS_RETAIL`

```python
DIMS_RETAIL = [
    ("oss_small_count_pct", True, False),     # many small orders by count
    ("oss_mega_count_pct", False, False),     # few mega prints
    ("cb_fast_cancel_ratio", False, True),    # retail rarely fast-cancels [CB]
    ("trd_size_entropy", True, False),        # heterogeneous human print sizes (B.2)
]
```

Update the module docstring 散户 bullet to add "heterogeneous (non-clipped) trade-size distribution".

## Step 7 — `tests/test_rules.py`: absorb the 4th retail dim (CAREFUL — B.0 boundary tests)

Adding a 4th `high_supports=True` retail dim changes `score_rt = mean(4 dims)`. You MUST:

1. Add `"trd_size_entropy": 0.2` to `_base()` (neutral-ish, matching the other baseline dims).
2. **Re-derive the precise-margin B.0 tests** so their semantic intent survives. The clean technique: in each
   test that pins an exact retail score / margin
   (`test_retail_max_but_within_margin_yields_runner_up`, `test_retail_wins_at_exact_win_margin`, and the
   limit-down win), set `"trd_size_entropy"` equal to the **old intended 3-dim `score_rt`** for that test, so
   the new 4-dim mean equals the old 3-dim mean and the boundary is preserved. Recompute by hand and keep the
   SAME assertions (label outcome + margin band). Do **not** weaken an assertion to make it pass — re-pin it.
3. Run the FULL `tests/test_rules.py` and confirm green. If a boundary test is now genuinely off by float
   noise, nudge the relevant input by ≤0.001 (as the B.0 comments already license) — do not delete or
   neuter the test.

Keep `test_absent_cb_dims_vote_neutral`, `test_youzi_wins_on_size_and_aggression`,
`test_quant_wins_on_machine_rhythm`, `test_returns_three_scores`, `test_confidence_*`,
`test_intention_gate_unchanged` green (adjust `_base()` only as needed).

---

# Gate (run BEFORE and AFTER)

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
conda run -n base --no-capture-output pytest tests/ -q
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 --verbose-scores
```

- **Before (B.0 baseline):** `weighted_f1 = 0.6094`, n=24, 散户 R = 0.40.
- On this Windows/GBK box ALWAYS use `--no-capture-output`; console Chinese may mojibake — trust on-disk
  UTF-8 / `config.CAPITAL_TYPES` membership, not console glyphs.

**Diagnostic you MUST produce (B.2-specific):** the **per-class mean `trd_size_entropy`** over the 24 labeled
rows (group the built parquet matrix by truth class). 散户 mean **must exceed** 量化 mean before a small F1
bump can be trusted. Compute it with a short inline script (you may reuse/extend the untracked
`scripts/_diag_retail_features.py` as scratch — do NOT commit it), e.g. build the matrix via
`_build_parquet_matrix` for each labeled date, join to the labels, and print `groupby(truth)` means of
`trd_size_entropy`.

---

# Fallback (only if the entropy diagnostic fails to separate)

If per-class means show 散户 mean ≤ 量化 mean (entropy does not separate), **switch the feature body** to the
ladder-free `1 - modal_size_share` (keep the same key `trd_size_entropy`, same wrapper, same wiring), with its
own hand-computed tests, and document the swap:

```python
def _trd_size_entropy(volumes) -> float:
    """Fallback: 1 - share of prints at the single most common size value.
    量化 repeats one clip -> high modal share -> low; 散户 heterogeneous -> high."""
    if volumes is None:
        return 0.0
    v = [float(x) for x in volumes if x is not None and np.isfinite(x) and x > 0]
    if len(v) < 2:
        return 0.0
    from collections import Counter
    modal = max(Counter(round(x) for x in v).values())
    return float(1.0 - modal / len(v))
```

Pick entropy vs modal-share by whichever **both** (a) gives 散户 mean > 量化 mean on the diagnostic AND (b)
moves proxy-F1. Document the choice and the per-class means in the report.

---

# Ship gate (the LEAD decides — you only report)

Report whether ALL hold after:
- `weighted_f1 > 0.6094`
- 散户 recall `>= 0.40` (do not regress below B.0's 4/10)
- `pytest tests/` green
- 散户 mean `trd_size_entropy` > 量化 mean (per-class diagnostic)

---

# Files

| Action | Path |
|---|---|
| Modify | `config.py` (`TRD_SIZE_BINS`) |
| Modify | `src/features.py` (`_trd_size_entropy`, `_trd_size_entropy_features`, `compute_daily_features` param) |
| Modify | `src/ingest_parquet.py` (`_deal_size_maps`, `read_deal_sizes_parquet`) |
| Modify | `src/aggregate.py` (`deal_lookup` threading) |
| Modify | `scripts/validate_offline.py` (`_build_parquet_matrix` builds + threads `deal_lookup`) |
| Modify | `src/rules.py` (`DIMS_RETAIL` += entropy dim, docstring) |
| Modify | `tests/test_features.py`, `tests/test_ingest_parquet.py`, `tests/test_rules.py` |
| **Do NOT touch** | `tests/fixtures/validation_labels.csv`, `main.py`, `src/label.py`, `src/normalize.py`, B.1 composite, RS-on-逐笔, Track L-c |

---

# When done, report (for the Opus gate review — do NOT commit)

1. Commands run + pass/fail counts (`pytest tests/ -q` before & after).
2. **Before/after** `weighted_f1` + per-class P/R/F1 (paste the harness output).
3. The full **per-row score table** (24 keys) from `--verbose-scores`.
4. **Per-class mean `trd_size_entropy`** (游资 / 量化 / 散户) — state explicitly whether 散户 > 量化.
5. Which (if any) 散户 names newly flipped to 散户, and attribution: did `trd_size_entropy` raise `score_rt`
   above the others?
6. Whether you used **entropy** (primary) or **modal-share** (fallback) and why.
7. Confirm `pytest tests/` green; confirm `scripts/validate_offline.py` still not imported by `main.py` /
   `src/` inference (grep).
8. Anything that contradicted the spec/plan (if none, say so) — propose a one-line fix, do not diverge silently.

Begin with the first failing test (Step 2).
