# AFAC2026 — Track 1: Market Participant Trading Behavior Recognition & Capital Flow Analysis

> **Private competition repository.** Do not make public — see Compliance below.

## What this is

Our solution for AFAC2026 Challenge Group, Track 1. Two coupled tasks per `(stock, trading-day)`:

- **Task 1 (weight 0.4)** — unsupervised clustering of trading patterns → `pattern_reco.csv`
- **Task 2 (weight 0.6)** — capital type + intent classification → `predict_result.csv`

Total score = `0.4 × Task1 + 0.6 × Task2`. Scored by silhouette/CH/Wasserstein/DTW (Task 1) and weighted F1 against T+5 market backtest (Task 2).

The authoritative plan is **`docs/AFAC2026_Track1_Project_Brief.docx`** (Rev. 7). Read it before writing any code. Official Tianchi spec (incl. §7.2 Case 1): **`docs/competition-spec/`**.

## Hard-locked facts (do not re-litigate)

| Field | Allowed values (emit these exact strings) |
|---|---|
| `capital_type` | `游资`, `量化`, `散户` — **3 classes** (bare `量化`, **not** `量化机构`) |
| `capital_intention` | `买入`, `卖出`, `T0交易` — 3 classes |
| `pattern_type` | **Open** — label freely; scored on interpretability |
| `transaction_date` | `YYYYMMDD` int; must equal **yesterday's trading day** at upload |
| Encoding | UTF-8-sig; no nulls; no blank lines; exactly 4 columns, fixed order |

The 3-class `capital_type` set is confirmed by a **direct organizer answer (DingTalk)**, which
overrides the baseline guide (it said 2 classes and the wrong string `量化机构`). `散户` is a real
modelled residual class — split from `量化` by execution **rhythm**, not order size. The old
`量化机构` is now invalid (rejected by the output validator). See brief Rev. 7.

The official `predict_result.csv` sample uses **random labels** (≈1:1:1 散户/游资/量化) — read zero
signal from its values and balance, only its format.

## Repository layout

```
.
├── docs/
│   ├── AFAC2026_Track1_Project_Brief.docx   # single source of truth — read first
│   ├── competition-spec/                    # official Tianchi spec (intro + track 1 + §7.2 Case 1)
│   ├── official_guidance/                   # baseline guide, FAQ/clarifications, tutorials
│   └── reference/
│       └── official_baseline_main.py        # frozen organizer baseline (2-class, stale) — diff/benchmark only
├── samples/              # small OFFICIAL sample files (force-added past .gitignore)
├── data/                 # sourced raw L2 — GITIGNORED, never committed
├── src/                  # pipeline modules (see brief §9)
├── tests/                # Case-1-anchored feature unit tests
├── main.py               # entry point → emits the two CSVs (audit contract)
├── init_env.sh           # dependency install
└── README.md
```

`docs/reference/official_baseline_main.py` is the organizers' original monolithic
baseline, frozen verbatim — it is **not** wired into our pipeline. Reach for it only
as a reference: regression-diffing our outputs against the baseline on A/B榜 batches,
or checking feature parity against its ~56-dim extractor. Its Task 2 is the stale
2-class `{游资, 量化机构}` scheme (see Hard-locked facts) — read it for the algorithm,
never for the label vocabulary.

## Compliance (auto-DQ if violated)

1. **Intraday-only** — no look-ahead / post-close / future data in features or rules.
2. **No hard-coding** — no per-stock-code label tables, no random fill, no ignoring L2 features.
3. **No answer-feedback** — the nightly instant score is for *verification only*. Never tune rules/thresholds/models on the published backtest answers.
4. **Reproducible** — `main.py` recomputes everything from raw L2; fixed seeds; relative paths; output must reconcile with code for the top-15 audit.
5. **Private repo** — solution sharing is opt-in *after* the competition only.

## Critical engineering gotchas (from the official baseline guide)

- `volume / amount / transactions / bigordervolume` are **cumulative** → `.diff().clip(lower=0)` after sorting.
- Use **`hh`** (Beijing hour, 8–16) for session windows. `date` is UTC epoch-ms → `.dt.hour` gives 0–8 and silently zeroes all PI features.
- `bids` / `asks` are **10-level nested JSON** — parse them.
- CB (cancellation) features need the separate **tick-cancel table**; they are zero in snapshot-only data.

## Nightly operations

Window **18:00 → 08:00** to upload yesterday's predictions for an instant verification score. A rotating on-call owns `source → run → upload → confirm`. See brief §8.

## Setup

```bash
bash init_env.sh
python main.py --input samples/AFAC2026.xlsx -o outputs/   # smoke-test on the official fixture
```
