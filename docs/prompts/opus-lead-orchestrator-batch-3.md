# Opus lead orchestrator — Batch 3 (Track V V.3/V.4 + Track L-c)

> **Paste this entire file** into a **new Claude Code Opus** session to run Batch 3.
> **Human team lead:** approve each dispatch with **"proceed to …"** between items; V.3 has a **human checkpoint**.
> **Sonnet prompts:** [`sonnet-track-v-v4-offline-harness.md`](sonnet-track-v-v4-offline-harness.md) · [`sonnet-track-l-c-cb-true-latency.md`](sonnet-track-l-c-cb-true-latency.md)
> **Human/hybrid spec:** [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) · **Human how-to:** [`../human_guides/track_v_validation_labels.md`](../human_guides/track_v_validation_labels.md)
> **Map:** [`WORKFLOW.md`](WORKFLOW.md) · **Spec:** [`../LIS.md`](../LIS.md) **v1.5.5** §6

---

You are the **Opus lead orchestrator** for AFAC2026 Track 1 in this repo. I am the human team lead. Your job is **not**
to implement these tracks yourself — you **dispatch, monitor, inspect, double-verify, and gate** one Sonnet execution
subagent at a time, with a **human checkpoint** for V.3 (labeling is a human action). You also **verify the V.3 CSV**
(read-only) and **run the V.4 proxy-F1 gate** that decides whether L-c ships.

**Model rule:** You (lead) stay on **Opus**. Dispatch **each subagent with model Sonnet**. If your environment does
not expose model selection for subagents, state in every dispatch header:

> *You are a Sonnet-class execution agent — minimal diff, TDD only, no architecture debates.*

---

## Batch 2 — already DONE (do not re-run)

| Track | Commit | Tests |
|-------|--------|-------|
| Phase 1b (wire normalize) | `18cca42` | 79 → 86 |
| Track L-b (real CB math) | `87a60a8` | 86 → 93 |
| Phase 2 (RS dtype fix) | `f932504` | 93 → 101 |

**Baseline for Batch 3:** `pytest tests/ -q` → **101 passed** (head `cfeae1e`, LIS **v1.5.5**). `src/validate.py` is
offline-only (V.1–V.2). `validation_labels.csv` has **EXAMPLE rows only**. `cb_fast_cancel_ratio` is an **inter-cancel
interval proxy** (L-c not started).

> **Note:** the Batch 3 brief referenced "v1.5.4 / `f932504`"; the actual head is **`cfeae1e` / LIS v1.5.5** (Phase 2
> landed + docs). Use **v1.5.5** as the spec of record.

---

## Operating model (strict)

For **each** item, run this loop — do not skip steps, do not start the next item until gated:

```
DISPATCH  → Sonnet subagent (model Sonnet) runs the filled prompt (TDD, scoped files only)
            [V.3 instead → HUMAN CHECKPOINT: human labels; you verify the CSV read-only]
MONITOR   → wait for completion; collect end-of-session report
INSPECT   → Opus reviews diff + report vs prompt acceptance criteria
VERIFY-1  → Opus independently runs commands and reads code (never trust report alone)
VERIFY-2  → second pass: scope / compliance / LIS alignment + regression check
GATE      → PASS → commit (unless I said "no commit") + Gate Report + stop for my proceed
            FAIL → fix or re-dispatch Sonnet; no commit; do not proceed
```

## Sequential order (with the V.3 human checkpoint)

```
1. V.4 harness (Sonnet)        ── can be BUILT now, in parallel with human V.3 labeling
       │                          (EXAMPLE-only → prints skip; that is the expected pre-V.3 state)
2. V.3 labels (HUMAN)          ── human seeds ≥8 cited rows; you VERIFY the CSV (read-only, no labeling)
       │
3. L-c true latency (Sonnet)   ── ONLY after V.3 verified AND V.4 prints a real baseline proxy-F1
                                  GATE = the proxy-F1 must MOVE UP, else L-c is not shipped
```

**Rationale (LIS §6 Track V / Track L, R1):** V.4 is the instrument; it needs no real labels to *build* but needs V.3
to *report a real number*. V.3 is human and gates *believing* any later win. L-c's proxy→true fast-cancel swap is
**only worth shipping if it moves the real proxy-F1** — so L-c must run **after** V.3+V.4 give a measurable baseline.

> **Parallelism note for the human:** you may start V.3 labeling immediately, concurrently with the Sonnet V.4 build.
> They do not conflict (V.4 touches `scripts/`+tests; V.3 touches the CSV). Only **L-c** needs both complete.

---

## Git commits (after each GATE PASS)

When an item **GATE = PASS**:
1. Stage **only** files for that item (no unrelated docs, `data/`, or secrets).
2. Commit with the **suggested message** (table below).
3. Run `git status`; report a clean tree for that item's scope.

**Do not commit** on GATE FAIL, partial work, or before VERIFY-1 + VERIFY-2 pass. **Do not commit** unless I authorize
that gate (**"commit"** or default proceed after PASS). Never `--no-verify`; never amend unless I ask. Never commit
`data/` or secrets.

| Item | Suggested commit message |
|------|--------------------------|
| V.4 harness | `feat: offline Track V proxy-F1 harness (Track V V.4)` |
| V.3 labels (human; commit the CSV) | `data: seed Track V validation labels (≥8 cited rows, V.3)` |
| Track L-c | `feat: true order→cancel latency for cb_fast_cancel_ratio (Track L-c)` |

**LIS / docs:** draft §4 + changelog lines after each PASS (see *LIS draft lines* below); apply `docs/LIS.md` edits
only if I say **"apply LIS update"**.

---

## How to dispatch each Sonnet subagent

Read the prompt file from disk and include its **full text** in the task, plus this header:

---

**Model:** Sonnet (execution agent — not Opus).
**Role:** Implement **only** what the prompt below specifies.
**Read:** the prompt body + the primary `src/`/`scripts/` files it names (+ their test files).
**Out of scope:** everything the prompt lists; no `docs/LIS.md` edits unless a factual contradiction (flag only).
**Report back:** commands run (with counts), files changed, acceptance checklist, contradictions, what remains.
**Do not commit** — the Opus lead commits after GATE PASS (unless I said otherwise).

---

**Environment:** Python via **Anaconda** (`conda run -n base …` on Windows if needed).

---

## Item 1 — V.4 harness (`sonnet-track-v-v4-offline-harness.md`)

**Expected artifacts:** `scripts/validate_offline.py` (new), `tests/test_validate_offline.py` (new), maybe
`scripts/__init__.py`.

**Must NOT touch:** `src/validate.py`, `main.py`, `validation_labels.csv`, any `src/` inference module.

**Acceptance:**
- [ ] CLI: `--labels`, `--input local:<root>`, `--input <pred_csv>`, optional `--min-confidence`/`--date`
- [ ] EXAMPLE rows (`confidence==0.0` / `source` startswith `EXAMPLE`) dropped
- [ ] Harness **calls** `validate.weighted_f1` (does not re-implement F1); per-class table printed
- [ ] EXAMPLE-only / empty join → skip message + exit **0**
- [ ] Tests use inline frames / temp CSV; local-source test `skipif`-guarded on `local_l2_tiny`
- [ ] `scripts/validate_offline.py` not imported by `main.py` / `src/` inference (grep-clean)
- [ ] Full suite green (101 → may increase); no heavy deps

**VERIFY-1 commands (you run):**
```bash
pytest tests/test_validate_offline.py -q
pytest tests/ -q
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:tests/fixtures/local_l2_tiny
grep -rn "validate_offline" src/ main.py    # expect: no hits
```

**VERIFY-2 (you read):**
- Diff limited to `scripts/` + new test (flag any `src/validate.py` edit)
- Harness reuses `label`/`postprocess` for predictions (does not re-derive scoring or F1)
- EXAMPLE-only run printed the skip message + exit 0
- No board-answer / `outputs/` leaderboard reads

---

## Item 2 — V.3 labels (HUMAN CHECKPOINT — you verify, you do NOT label)

**This is not a Sonnet dispatch.** Hand the human [`track-v-v3-acceptance-spec.md`](track-v-v3-acceptance-spec.md) +
[`../human_guides/track_v_validation_labels.md`](../human_guides/track_v_validation_labels.md). When the human says the
CSV is seeded, **you verify it read-only** (no labeling, no edits to labels — that would be answer-feedback-adjacent):

**VERIFY (read-only) — per `track-v-v3-acceptance-spec.md` §5:**
```bash
python -c "import pandas as pd, config; df=pd.read_csv('tests/fixtures/validation_labels.csv'); \
print('cols ok:', list(df.columns)); \
real=df[(df['confidence']>0) & (~df['source'].astype(str).str.upper().str.startswith('EXAMPLE'))]; \
print('scorable rows:', len(real)); print('classes:', real['capital_type'].value_counts().to_dict()); \
print('illegal labels:', set(real['capital_type']) - set(config.CAPITAL_TYPES))"
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:data
```

**GATE (V.3 done enough):**
- [ ] Header exactly matches the schema lock; `illegal labels: set()`
- [ ] `scorable rows >= 8`; `>= 2` classes present
- [ ] `source` values are public post-market citations (no board answers); no circular (feature-derived) labels in `notes`
- [ ] V.4 harness prints a **real** proxy-F1 (record this baseline number — L-c must beat it)

**On PASS:** commit the CSV (human-authored data) with the V.3 message **only if the human authorizes**; record the
**baseline proxy-F1**. **Stop** and wait for **"proceed to L-c"**.

> If the human is not ready to label, you may still GATE Item 1 (V.4) and **pause** here — L-c stays blocked until V.3
> lands. Do not fabricate labels to unblock yourself.

---

## Item 3 — Track L-c (`sonnet-track-l-c-cb-true-latency.md`)

**Precondition:** V.3 verified (Item 2 GATE PASS) **and** V.4 prints a real baseline proxy-F1. If not, **do not
dispatch** — report "L-c blocked on V.3/V.4".

**Expected artifacts:** `src/ingest_local.py` (`read_cancel_frame` + ref join + `latency_ms`), `src/features.py`
(`_cb_features` true branch), maybe `config.py` (comment only), `tests/test_features.py` / `tests/test_ingest_local.py`,
optionally repaired `local_l2_tiny` fixture rows.

**Must NOT:** change `CB_KEYS` arity; break the xlsx path; wire `main.py --input data/`; import `validate`/`scripts`
into inference.

**Acceptance:**
- [ ] `read_cancel_frame` retains refs (`ask_seq`/`bid_seq` SZ, `exchange_order_no` SH) + finite `latency_ms`
- [ ] `cb_fast_cancel_ratio` = share of **matched** cancels with **decoded-ms** latency `< CB_FAST_CANCEL_MS`
- [ ] Unmatched cancels excluded from numerator **and** denominator
- [ ] `HHMMSSmmm` decoded to real elapsed ms (minute-boundary correct) — discriminating test proves it
- [ ] `CB_KEYS` unchanged (5 keys); other 4 CB keys unchanged; absent path unchanged
- [ ] xlsx smoke green (`cb_available=False`); `load_raw` untouched
- [ ] Full suite green (101 → may increase)
- [ ] **Proxy-F1 before→after** recorded; ships **only** if F1 moved up

**VERIFY-1 commands (you run):**
```bash
pytest tests/test_features.py -q -k cb
pytest tests/test_ingest_local.py -q
pytest tests/test_rules.py::test_absent_cb_dims_vote_neutral -q
pytest tests/ -q
python main.py --input samples/AFAC2026.xlsx -o outputs/
# Proxy-F1 gate (run on the proxy commit AND after):
python scripts/validate_offline.py --labels tests/fixtures/validation_labels.csv --input local:data
python -c "from src.features import CB_KEYS; print(len(CB_KEYS), CB_KEYS)"   # expect 5 keys, unchanged
```

**VERIFY-2 (you read) — anti-pattern guard (Batch 2 lesson):**
- The discriminating test **crosses a minute boundary** (raw-int diff ≠ true ms) and **would FAIL** if reverted to the
  proxy. Reject any test that passes on both proxy and true latency.
- `latency_ms` uses decoded ms, not raw `HHMMSSmmm` subtraction.
- Any fixture rows changed are **documented**; existing `test_ingest_local.py` assertions stay green or are
  deliberately updated with rationale.
- `CB_KEYS` arity unchanged; `cb_cancel_interval_cv` not added.
- **The gate is the proxy-F1 move, not green unit tests.** If F1 did not move on real data, GATE = FAIL → do not ship;
  recommend keeping the proxy (LIS §6 Track L disposition).

---

## Double-verify rule (mandatory) — per item

Produce a short **Gate Report:**
1. **Subagent / human claims** — bullet summary
2. **Lead verification** — what you ran/read; paste the `pytest` summary line + proxy-F1 numbers; note any mismatch
3. **Commit** — if PASS: hash + message; if FAIL: "no commit"
4. **GATE = PASS** only if claims agree, VERIFY-1 + VERIFY-2 clean, and (L-c) the proxy-F1 moved up
5. **GATE = FAIL** → re-dispatch Sonnet with the failing test + `file:line`, or report a blocked precondition; no commit

**Do not trust the subagent report.** Re-run every command yourself. Batch 2 lesson: 2 of 3 tracks shipped a
**non-discriminating** test on the first pass (the panel didn't separate; the RS test only ran on `[ns]`). Read the
test and confirm it fails when the implementation is reverted on the discriminating case.

---

## After each GATE PASS

1. Run the commit (table) unless I said **"no commit"** for that gate.
2. Propose the LIS draft lines below (**draft only** — apply only if I say **"apply LIS update"**).
3. Present the Gate Report + commit hash.
4. **Stop and wait** for my **"proceed to …"** before the next item.

---

## LIS draft lines (apply only on my "apply LIS update")

**V.4 (after PASS):**
- §4 `src/validate.py` row: append *"+ offline harness `scripts/validate_offline.py` (V.4) — runs pipeline on labeled
  keys, prints proxy-F1; offline only, not in `main.py`."*
- Changelog: *"v1.5.6 — Track V V.4 landed (`<hash>`): `scripts/validate_offline.py` offline harness; EXAMPLE-row
  filter; calls `validate.weighted_f1`; not in inference path. Suite 101 → N. Awaits V.3 real labels for a real
  proxy-F1 number."*

**V.3 (after verify PASS):**
- §6 Track V: mark V.3 ✅ (≥8 cited rows; record class counts + baseline proxy-F1).
- Changelog: *"v1.5.x — Track V V.3 seeded (`<hash>`): ≥8 human-labeled cited rows; baseline offline proxy-F1 = X.xxx
  on `<n>` keys. Unblocks L-c proxy-F1 gate."*

**L-c (after PASS — only if F1 moved up):**
- §4 `ingest_local.py` row: change *"fast-cancel is an inter-cancel proxy, Track L-c"* → *"`cb_fast_cancel_ratio` is
  **true order→cancel latency** (ref-join, decoded ms) as of `<hash>`; unmatched cancels excluded."*
- §6 Track L: mark L-c ✅; note matched-fraction + proxy-F1 before→after.
- §7 R1: if L-c (with V.3/V.4) shows a real multi-stock proxy-F1 delta, note progress toward **downgrading R1 to ✅**
  (R1's "remaining" is exactly a real-data proxy-F1 delta).
- Changelog: *"v1.5.x — Track L-c landed (`<hash>`): true order→cancel latency for `cb_fast_cancel_ratio`;
  `read_cancel_frame` carries refs + `latency_ms`; `CB_KEYS` unchanged. Proxy-F1 X→Y. Suite 101 → N."*

> If L-c's F1 did **not** move: changelog a **non-landing** note instead — *"Track L-c evaluated; true latency did not
> move proxy-F1 (X→X) on the seed set; kept the proxy per LIS §6 Track L disposition; revisit with more labels/days."*

---

## What you do NOT do

- Do not implement the tracks yourself in the lead session (delegate to Sonnet).
- Do not run Batch 3 items out of order, or dispatch L-c before V.3 is verified + V.4 baseline exists.
- Do not **label** `validation_labels.csv` yourself, or edit labels to improve F1 (answer-feedback-adjacent).
- Do not skip VERIFY-1 because the subagent said green; do not accept a non-discriminating test.
- Do not ship L-c on green unit tests alone — the gate is the **real proxy-F1 move**.
- Do not start Phase 3+ or `main.py --input data/` wiring unless I ask.
- Do not commit `docs/` unless I authorized a docs commit for that gate.

---

## Start now

1. Confirm baseline: `git log -1 --oneline` shows `cfeae1e`; `pytest tests/ -q` → **101 passed**.
2. Read [`sonnet-track-v-v4-offline-harness.md`](sonnet-track-v-v4-offline-harness.md) in full.
3. Dispatch the **V.4** Sonnet subagent (model Sonnet) with that prompt + dispatch header.
4. When it returns: **INSPECT → VERIFY-1 → VERIFY-2 → Gate Report.** On PASS, commit (V.4 message) → stop for proceed.
5. In parallel, hand the human the **V.3** spec + guide. When the CSV is seeded, **verify it read-only** (Item 2 GATE).
6. On my **"proceed to L-c"** (V.3 verified + V.4 baseline present), dispatch **L-c**, then run the proxy-F1 gate.

**Begin with the V.4 dispatch** (unless I say otherwise).
