# Opus lead orchestrator — Batch 5 (Phase 6 — parquet main.py + first submit.zip for 20260623)

> **Paste this entire file** into a **new Claude Code Opus** session.
> **Human team lead:** approve each step with **"proceed to …"** between items.
> **Operating model:** `docs/prompts/opus-lead-orchestrator-batch-3.md`
>   (DISPATCH → MONITOR → INSPECT → VERIFY-1 → VERIFY-2 → GATE).
> **Sonnet prompt (P6.1):** `docs/prompts/sonnet-phase-6-parquet-main-submit.md`
> **Spec of record:** `docs/LIS.md` **v1.6.7** §6 Phase 6 + §2–§3 compliance.
> **Map:** `docs/prompts/WORKFLOW.md`

---

## You are the Opus lead orchestrator

Your job is **not** to implement — you **dispatch, monitor, inspect, double-verify, gate, and commit**
one Sonnet subagent at a time. Wait for the human **"proceed to …"** before each dispatch or commit.

**Model rule:** You stay on **Opus**. Dispatch each subagent as **Sonnet**. Every dispatch header must include:
> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do not commit.*

**Environment:** Python via **Anaconda** (`conda run -n base …` on Windows).

> **Runtime caveat:** a full **100-stock × 1-day** parquet run through `main.py` may take **tens of minutes**
> on this box (filtered reads, cancel joins, feature matrix). Redirect stdout to a file and poll — do not
> assume hang on slow progress. Prefer base python directly:
> `PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u main.py … 1>run.out 2>run.err`

> **Gate-run caveat (offline proxy-F1):** `scripts/validate_offline.py` on `parquet:data/202606` takes
> **~7–8 min** and buffers stdout until exit. Use the same redirect pattern as Batch 4.

---

## Mission (today — binding)

**Goal:** connect `main.py` to the parquet corpus for the **competition 100-stock universe** and produce a
**first valid `submit.zip`** for **`transaction_date = 20260623`**.

**Human will upload** the zip to Tianchi after you verify format. This is **not** Track V label work and
**not** a rules/features change — **ops + wiring only**.

**Out of scope today:**
- Phase 4 GBDT / `model.py` training
- P3.1 / P3.2 / B.3c / any `rules.py` or `features.py` scorer change
- Track D label expansion / `validation_labels.csv` edits
- Holiday calendar beyond what P6.1 needs for explicit `--date 20260623` (full calendar can stay stubbed)
- Tuning against instant leaderboard scores (compliance #3)

---

## Current state — trust this handoff

### Git / remote
| Item | Value |
|------|--------|
| Branch | post–PR **#3** merge (confirm with `git log -1` / `git branch --show-current`) |
| LIS state | v1.6.7 — V.3.3 verify ✅; active gate **0.6971/n=65**; P3.1/P3.2/B.3c DEFERRED |
| PR #3 | Merged — Task 2 3-class pipeline + Track V gate 0.6971/n=65 |
| Parquet days in `data/202606/` | `20260616`, `20260617`, `20260618`, `20260622`, **`20260623`** |
| Competition universe | `samples/stock-samples.xlsx` — **100 stocks** (`股票代码` column) |
| `main.py` today | **xlsx-only** via `ingest.load_raw` — **cannot** read parquet yet |
| Parquet pipeline reference | `scripts/validate_offline.py` `_build_parquet_matrix` / `_predict_parquet` (offline-only harness; **do not import the harness from `main.py`**) |

### Active gate (must not regress on any rules change — today should be wiring-only)
| Set | n | weighted_f1 | Notes |
|-----|---|-------------|-------|
| **Active gate** | **65** | **0.6971** | post–V.3.3 20260623 addendum |
| **Continuity reference** | 24 {0617,0618} | **0.6599** | floor |
| Test suite | — | **141 passed, 2 xfailed** | L-c xfails dormant |

**Regression gate command (after P6.1 — wiring-only slice, no rules change expected):**
```bash
conda run -n base pytest tests/ -q
PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 1>gate.out 2>gate.err
```
Expect gate **0.6971/n=65** unchanged. If it moves, STOP — a scorer file changed accidentally.

---

## Batch 5 — sequential order

```
P6.1 (Sonnet)  parquet input in main.py + 100-stock universe + submit.zip packager
       ↓
VERIFY         Opus production run → outputs/20260623/submit.zip
       ↓
HUMAN          upload submit.zip to Tianchi (instant-feedback window optional)
       ↓
COMMIT         only after human "proceed to commit" + GATE PASS
```

**One Sonnet dispatch only** for P6.1 unless it fails scope — do not split unless blocked.

---

## Operating loop (strict — no skips)

```
DISPATCH  → Sonnet (P6.1 prompt; TDD; no commit)
MONITOR   → collect report
INSPECT   → diff vs prompt acceptance
VERIFY-1  → pytest; xlsx smoke; parquet smoke; zip layout; row counts
VERIFY-2  → scope / compliance / no rules.py|features.py drift; regression gate if touched
GATE      → PASS → wait human "proceed to commit" → commit
            FAIL → no commit; re-dispatch or fix
```

---

## Confirm on start (mandatory)

```bash
git log -3 --oneline
git branch --show-current
git status --short
conda run -n base pytest tests/ -q
```

Paste summary. If suite ≠ **141 passed, 2 xfailed**, stop and report delta.

Optional baseline gate (recommended if time allows):
```bash
PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606 1>gate.out 2>gate.err
```
Expect **0.6971/n=65**. Clean up `gate.out`/`gate.err` after.

---

## P6.1 — DISPATCH NOW (after human "proceed to dispatch P6.1")

**Prompt file:** [`sonnet-phase-6-parquet-main-submit.md`](sonnet-phase-6-parquet-main-submit.md)

**Paste the entire Sonnet prompt** into a **Sonnet** subagent. Header:
> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates. Do not commit.*

**Acceptance (Opus verifies — copy from Sonnet prompt):**
- [ ] `main.py` accepts `parquet:<root>` input (default root `data/202606`) **without breaking** xlsx path
- [ ] `--universe` loads `samples/stock-samples.xlsx` (100 codes); panel used for rank-normalization **and** output rows
- [ ] `--date 20260623` pins `transaction_date` in both CSVs (postprocess contract)
- [ ] Full pipeline on parquet: ingest → features → cluster → label → model stub → postprocess
- [ ] `submit.zip` at archive **root** with exactly `pattern_reco.csv` + `predict_result.csv` (no nested folders)
- [ ] CSVs: UTF-8-sig, 4 columns, no nulls; `capital_type` ∈ {游资,量化,散户}; no `量化机构`
- [ ] Output row count documented (~100; log any universe codes missing parquet for 20260623)
- [ ] `pytest tests/ -q` → **141 passed, 2 xfailed** (or higher if new tests added)
- [ ] **No** changes to `rules.py`, `features.py`, `validation_labels.csv`

**Production smoke (Opus runs after Sonnet reports done):**
```bash
conda run -n base pytest tests/ -q
PYTHONIOENCODING=utf-8 "C:/Users/ASUS/anaconda3/python.exe" -u main.py \
  --input parquet:data/202606 \
  --universe samples/stock-samples.xlsx \
  --date 20260623 \
  -o outputs/20260623 \
  --pack submit.zip
```
Adjust CLI flags to match Sonnet's implementation (`--pack` name may differ — read `--help`).

> ⚠️ **`--pack` gotcha (confirmed 20260701 run):** `main.py --pack submit.zip` writes the zip to the
> **current working directory (repo root)**, *not* under `-o outputs/<date>/`. To land it at the
> deliverable path directly, pass the full relative path: `--pack outputs/<date>/submit.zip`.
> Otherwise move it after the run: `mv submit.zip outputs/<date>/submit.zip` (byte-identical).
> Either way, confirm the repo root is clean afterward so a stray `submit.zip` isn't left tracked.

**Verify artifacts:**
```bash
python -c "import zipfile; z=zipfile.ZipFile('outputs/20260623/submit.zip'); print(z.namelist())"
python -c "import pandas as pd; p=pd.read_csv('outputs/20260623/predict_result.csv',encoding='utf-8-sig'); print(len(p), p.transaction_date.unique(), p.capital_type.value_counts().to_dict())"
```

---

## GATE criteria (P6.1)

| Check | Pass condition |
|-------|----------------|
| Suite | 141+ passed, 2 xfailed (unchanged xfails OK) |
| Proxy-F1 regression | **0.6971/n=65** unchanged (if validate_offline re-run) |
| xlsx backward compat | `python main.py --input samples/AFAC2026.xlsx -o outputs/smoke/` still works |
| submit.zip | 2 root entries only; both CSVs validate |
| predict_result.csv | `transaction_date` = **20260623** only; ~100 rows |
| Scope | No `rules.py` / `features.py` / label CSV edits |

**Suggested commit message (after human "proceed to commit"):**
```
feat(ops): Phase 6 — parquet main.py + submit.zip for competition universe
```

---

## What you do NOT do

- Do not edit `validation_labels.csv` (human-only).
- Do not dispatch scorer-moving Sonnet slices (P3.x / B.3c / features).
- Do not start Phase 4 GBDT.
- Do not tune on instant leaderboard answers.
- Do not implement tracks yourself (except read-only verify runs).
- Do not commit without human **"proceed to commit"**.

---

## After GATE PASS — human handoff

Report to human:
1. Path to `outputs/20260623/submit.zip`
2. Row counts + class distribution in `predict_result.csv`
3. Any universe codes missing parquet for 20260623
4. Commands to reproduce
5. Reminder: instant score is **verification only** (compliance #3); A-board deadline **2026-07-10 23:59**
