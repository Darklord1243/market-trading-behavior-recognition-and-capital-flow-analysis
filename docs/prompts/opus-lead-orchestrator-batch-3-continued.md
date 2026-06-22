# Opus lead orchestrator — Batch 3 CONTINUATION (post–B.2)

> **Paste this block** at the top of a **new Claude Code Opus** session **before** (or instead of re-running)
> `opus-lead-orchestrator-batch-3.md` from item 1. The base orchestrator file is still the operating-model
> reference (DISPATCH → MONITOR → INSPECT → VERIFY-1 → VERIFY-2 → GATE); **this file pins current repo state**
> so you do not re-dispatch V.4 / V.3 / P.1 / B.2.
>
> **Sonnet prompt:** [`sonnet-track-l-c-cb-true-latency.md`](sonnet-track-l-c-cb-true-latency.md) **+**
> [`sonnet-track-l-c-cb-true-latency-addendum.md`](sonnet-track-l-c-cb-true-latency-addendum.md) (mandatory addendum).
> **Map:** [`WORKFLOW.md`](WORKFLOW.md) · **Spec:** [`../LIS.md`](../LIS.md) **v1.6.0** §6

---

## Current baseline (2026-06-22 — trust this, not the base orchestrator "Start now")

| Item | Status | Commit / note |
|------|--------|---------------|
| Head | **`d1fc070`** (LIS v1.6.0) | feature `94ccb90` (B.2) |
| Suite | **`pytest tests/ -q` → 130 passed** | was 101 at batch-3 brief time |
| V.4 harness | ✅ DONE | `737ed5a` — `scripts/validate_offline.py`; grep-clean vs `main.py`/`src/` |
| V.3 labels | ✅ DONE | `0d1263d` + `c8f9f93` (0618 addendum) — 24 scorable keys on combined gate |
| P.1 parquet ingest | ✅ DONE | `d500d60` — `src/ingest_parquet.py`, `parquet:` input scheme |
| Feature B B.0 | ✅ DONE | `bcc97f9` |
| Feature B B.2 | ✅ DONE | `94ccb90` — `trd_size_entropy` retail dim |
| **Active gate** | **`parquet:data/202606` n=24** | **weighted_f1 = 0.6599** (post–B.2); 散户 R **5/10** (P=0.83) |
| Prior gate (pre–B.2) | same corpus n=24 | weighted_f1 = 0.6094; 散户 R 4/10 |
| L-c parquet infra | ✅ EXISTS | `read_cancel_frame_parquet` emits `latency_ms` (OrderID self-join, decoded ms) |
| L-c parquet swap | **EVALUATED — NOT SHIPPED** | swapping true latency into `cb_fast_cancel_ratio` **regressed** proxy-F1 **0.4917 → 0.4381** on n=10 0618 slice (LIS v1.5.7); **inter-cancel proxy kept** |
| L-c local path | **NOT DONE** | `ingest_local.read_cancel_frame` still drops ref columns; no `latency_ms` |
| **`cb_fast_cancel_ratio` today** | **inter-cancel interval proxy** | in `_cb_features` for both local and parquet cancel frames |

**Do NOT re-dispatch:** V.4, V.3, P.1, B.0, B.2.

**Next item only:** **Track L-c re-eval** (Sonnet) — see addendum for scope and gate baseline **0.6599**.

---

## Operating model (unchanged — follow base orchestrator)

For L-c re-eval, run the full loop:

```
DISPATCH  → Sonnet (model Sonnet) with base L-c prompt + mandatory addendum
MONITOR   → collect end-of-session report
INSPECT   → Opus reviews diff vs prompt + addendum acceptance criteria
VERIFY-1  → Opus runs commands independently (never trust report alone)
VERIFY-2  → scope / compliance / non-discriminating-test guard / LIS alignment
GATE      → PASS only if proxy-F1 moved UP vs 0.6599 on parquet:data/202606 n=24
            FAIL if flat/down → no commit; report "L-c not shipped" per LIS §6 disposition
```

**Human checkpoint:** wait for my **"proceed to L-c"** before dispatch. Sonnet **does not commit** — Opus commits after GATE PASS only if I authorize.

---

## L-c re-eval dispatch header (paste above the two prompt files)

**Model:** Sonnet (execution agent — not Opus).
**Role:** Implement **only** what the prompt + addendum specify.
**Read:** `sonnet-track-l-c-cb-true-latency.md` + `sonnet-track-l-c-cb-true-latency-addendum.md` + named `src/` files.
**Out of scope:** re-building V.4; re-implementing parquet `latency_ms`; B.2 / retail dims; `docs/LIS.md` edits (flag only).
**Gate baseline:** weighted_f1 **0.6599** on `parquet:data/202606` n=24 — **not** 0.4917, **not** `local:data`.
**Report back:** commands + counts, files changed, acceptance checklist, proxy-F1 before→after, contradictions.
**Do not commit** — Opus lead commits after GATE PASS (unless I said otherwise).

**Environment:** Python via **Anaconda** (`conda run -n base …` on Windows if needed).

---

## VERIFY-1 commands (Opus runs after Sonnet returns)

```bash
pytest tests/test_features.py -q -k cb
pytest tests/test_ingest_local.py -q
pytest tests/test_rules.py::test_absent_cb_dims_vote_neutral -q
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/
python -c "from src.features import CB_KEYS; print(len(CB_KEYS), CB_KEYS)"   # expect 5 keys

# Proxy-F1 gate — THE win condition (run BEFORE on HEAD, AFTER on Sonnet diff):
conda run -n base --no-capture-output python scripts/validate_offline.py \
  --labels tests/fixtures/validation_labels.csv --input parquet:data/202606

grep -rn "validate_offline" src/ main.py    # expect: no hits
```

Record **weighted_f1 before → after**. **GATE = PASS** only if after **> 0.6599**.

---

## VERIFY-2 (Opus reads — anti-pattern guard)

- Discriminating test **crosses a minute boundary** (decoded ms ≠ raw HHMMSSmmm int diff); **would FAIL** if reverted to proxy.
- **Do not** re-implement parquet `latency_ms` — it already exists in `ingest_parquet.read_cancel_frame_parquet`.
- **Do not** ship a blind re-swap of `cb_fast_cancel_ratio` to true latency without measured F1 gain vs **0.6599** — LIS v1.5.7 already dispositioned this regression on the n=10 slice.
- `CB_KEYS` arity unchanged (5); `cb_cancel_interval_cv` not added.
- xlsx path untouched; `main.py` not wired to local/parquet corpus.
- **Gate is the F1 move, not green unit tests alone.**

---

## Suggested commit message (only on GATE PASS + F1 > 0.6599)

```
feat: true order→cancel latency for cb_fast_cancel_ratio (Track L-c re-eval)
```

If F1 flat/down: **no commit**; changelog note only if I say **"apply LIS update"**:

> Track L-c re-evaluated on n=24 gate (0.6599 baseline); true-latency swap did not beat post–B.2 proxy-F1; kept inter-cancel proxy per §6 Track L disposition.

---

## Start now

1. Confirm baseline: `git log -1 --oneline` → `d1fc070`; `pytest tests/ -q` → **130 passed**.
2. Read addendum + base L-c prompt in full.
3. **Wait for human "proceed to L-c"** → dispatch Sonnet with header + both prompt files.
4. INSPECT → VERIFY-1 → VERIFY-2 → Gate Report → stop for human proceed / commit authorization.
