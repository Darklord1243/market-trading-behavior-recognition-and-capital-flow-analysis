# Track V V.3 — acceptance & verification spec (validation-label seeding)

> **This is NOT a Sonnet implementation prompt.** V.3 is a **human labeling action**. This document bridges the
> human how-to guide to **engineering acceptance + gate criteria**: what locks the CSV must satisfy, how the
> EXAMPLE rows are handled, and **how the Opus lead verifies the CSV** before it unblocks V.4 / L-c proxy-F1 gating.
>
> **Human how-to (do the labeling here):** [`../human_guides/track_v_validation_labels.md`](../human_guides/track_v_validation_labels.md) — sources, recipe, confidence dial.
> **Spec of record:** `docs/LIS.md` **v1.5.5** §6 *Track V* (task V.3) · **Compliance:** LIS §3.3 / §5.1.
> **Output file:** `tests/fixtures/validation_labels.csv` (currently **EXAMPLE rows only**).

This spec **does not duplicate** the human guide — read that for *how/where* to label. This adds only the
**verification contract** the guide does not cover.

---

## 0. Roles

| Who | Does |
|---|---|
| **Human** | Labels ≥8 real `(stock, day)` rows from public post-market sources, per the human guide. The *only* party that may assign a label. |
| **Opus lead** | **Verifies** the CSV against the locks below (read-only, no labeling, no circular labels). Declares V.3 "done enough" to unblock V.4/L-c. |
| **Sonnet** | Never touches `validation_labels.csv`. Consumes it only through the V.4 harness (`sonnet-track-v-v4-offline-harness.md`). |

---

## 1. CSV schema lock (exact columns, exact order)

`tests/fixtures/validation_labels.csv` — header **must** be exactly:

```
stock_code,transaction_date,capital_type,capital_intention,source,confidence,notes
```

| Column | Lock |
|---|---|
| `stock_code` | exchange-suffixed (`000001.SZ`, `600000.SH`). Must match the corpus key format used by `ingest_local`. |
| `transaction_date` | `YYYYMMDD`. **Prefer days we have local data for** (`20260611`/`20260612`) so the V.4 harness can actually run the pipeline on them. |
| `capital_type` | **Exactly one of** `游资` / `量化` / `散户` (the LIS §2 3-class lock — exact bytes, **bare `量化`, never `量化机构`**). |
| `capital_intention` | `买入` / `卖出` / `T0交易` **or blank** (blank preferred over a guess). Not scored by `weighted_f1` (which scores `capital_type`); kept for future use. |
| `source` | **Non-empty** public citation (龙虎榜 URL / news / research note). A row without a real source must be **omitted**, not invented. |
| `confidence` | float in `[0.0, 1.0]`. `0.0` is reserved for **EXAMPLE** rows (see §2). Real rows: per the guide's dial (游资 0.6–0.9, 量化 0.3–0.6, 散户 0.2–0.5). |
| `notes` | one line of human reasoning (the seat name, the narrative). |

**Encoding:** UTF-8 (the file is text labels; not the UTF-8-**sig** submission format — that lock is for
`predict_result.csv`, not this fixture). No trailing blank-cell rows.

---

## 2. EXAMPLE-row contract (how the tooling treats them)

The seed file ships with template rows: `EXAMPLE.SZ` / `EXAMPLE.SH`, `confidence == 0.0`, `source` starting with
`EXAMPLE`. These exist so the schema is self-documenting before any real labeling.

**Rule (enforced by the V.4 harness, not by hand-editing):**
- A row is an **EXAMPLE / non-scorable** row iff `confidence == 0.0` **OR** `source` starts with `EXAMPLE`
  (case-insensitive). The harness **drops** these before scoring.
- The human **may** delete the EXAMPLE rows once real rows exist, or leave them — the harness ignores them either
  way. **Do not** rely on deletion for correctness; rely on the filter.
- An **EXAMPLE-only** CSV is a valid state: the harness prints a "no scorable labels — skipping" message and exits
  **0** (this is the pre-V.3 baseline, not an error).

> This contract is the single source of truth for "what counts as a real label." The V.4 prompt
> (`sonnet-track-v-v4-offline-harness.md`) references it; keep the two consistent if either changes.

---

## 3. Per-row quality gate (each real row must pass all)

A row is **scorable** only if **every** check holds:

- [ ] `capital_type` ∈ `{游资, 量化, 散户}` (exact bytes; reject `量化机构`, English, whitespace-padded variants)
- [ ] `source` is non-empty and **not** an EXAMPLE placeholder
- [ ] `confidence` parses to a float in `(0.0, 1.0]` (real rows are strictly > 0.0)
- [ ] `transaction_date` is 8-digit `YYYYMMDD`; `stock_code` is exchange-suffixed
- [ ] the label is from **independent external evidence** (龙虎榜 seat / news / name prior) — **never** read off our
      own features (cancel rate, burst, CV). *Circular labels silently validate the model against itself* and are
      the one failure the tooling **cannot** detect — only human discipline and the `source`/`notes` review catch it.

---

## 4. Set-level acceptance (V.3 "done enough" to unblock V.4 / L-c)

- [ ] **≥ 8** scorable rows (per LIS §6 V.3).
- [ ] **Class mix honesty** — 游资-heavy is expected and acceptable (龙虎榜 over-represents hot-money big-movers);
      `量化`/`散户` are weakly attributable. Aim for the guide's recipe (4–6 游资, 2–3 量化, 1–2 散户) but **do not
      fabricate** balance. **At least 2 distinct classes** present (a single-class set scores trivially and proves
      nothing). Record the actual class counts.
- [ ] At least some rows on a **locally-available day** (`20260611`/`20260612`) so the V.4 `--input local:` path can
      produce predictions for them; rows on other days are allowed but only score via a precomputed pred CSV.
- [ ] Every row passes the §3 per-row gate.

> **Honest limit (carry into every PR that cites the proxy):** this seed is **tiny, class-imbalanced, and noisy**
> (seat-present ≠ whole-day-dominant). Its class prior ≠ the hidden T+5 truth's. It is a **smoke detector, not a
> leaderboard simulator** — trust a **big regression**, discount a **small win** as noise (LIS §6 Track V honest
> limits). OQ-1/R2 is resolved (3-class); the proxy still cannot simulate the full backtest truth.

---

## 5. How the Opus lead verifies the CSV (read-only — no labeling, no circular labels)

The lead does **not** assign or second-guess labels (that is the human's job and would risk circularity). The lead
verifies **structure, compliance, and scorability**:

1. **Schema/lock check (read-only):** confirm the header matches §1 exactly; every `capital_type` is a valid byte
   string via `config.CAPITAL_TYPES` membership (not by eyeballing — Windows console mojibakes Chinese):
   ```bash
   python -c "import pandas as pd, config; df=pd.read_csv('tests/fixtures/validation_labels.csv'); \
   print('cols ok:', list(df.columns)); \
   real=df[(df['confidence']>0) & (~df['source'].astype(str).str.upper().str.startswith('EXAMPLE'))]; \
   print('scorable rows:', len(real)); \
   print('classes:', real['capital_type'].value_counts().to_dict()); \
   bad=set(real['capital_type']) - set(config.CAPITAL_TYPES); print('illegal labels:', bad)"
   ```
   PASS requires: columns exact, `scorable rows >= 8`, `illegal labels: set()`, `>= 2` classes present.
2. **Compliance read:** spot-check that `source` values are public post-market citations (龙虎榜/news), **never** a
   reference to the platform instant score / backtest answers (§3.3 auto-DQ). Confirm no row's `notes` admits a
   feature-derived (circular) label.
3. **Harness dry-run:** run the V.4 harness against the CSV; it must either print a real proxy-F1 (≥8 rows) or, if the
   lead is verifying *before* labeling, print the EXAMPLE-only skip and exit 0:
   ```bash
   python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:data
   ```
4. **No mutation:** the lead must not edit labels to "improve" the F1 — that is answer-feedback-adjacent. The lead
   only reports structural failures back to the human for re-labeling.

**V.3 is "done enough"** when checks 1–3 pass (≥8 scorable rows, legal labels, ≥2 classes, harness prints a real
number). At that point V.4 has a real baseline and **Track L-c's proxy-F1 gate is unblocked**.

---

## 6. What V.3 unblocks (sequencing)

```
V.3 (human labels, ≥8 scorable rows)
   │  verified by Opus lead (§5)
   ▼
V.4 harness prints a real baseline proxy-F1
   │
   ▼
Track L-c gate: proxy-F1 before→after must MOVE UP, else L-c is not shipped (LIS §6 Track L)
```

- **Before V.3:** V.4 can be **built and tested** (against EXAMPLE rows + inline fixtures) but only prints the skip
  message. L-c is **blocked** (no way to measure its win).
- **After V.3:** both V.4 (real number) and L-c (gated swap) proceed.

---

## 7. Out of scope for V.3

- Building the scorer (`src/validate.py` — done, V.1–V.2) or the harness (`scripts/validate_offline.py` — V.4).
- Any code change. V.3 is **data only** (`tests/fixtures/validation_labels.csv`).
- Wiring labels into features / `main.py` (forbidden — compliance #1/#3).
- Resolving class-set questions (OQ-1 already resolved: 3-class).
