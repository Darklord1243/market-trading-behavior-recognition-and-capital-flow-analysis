# Sonnet execution prompt — Phase 2 (RS resolution fix + rhythm features)

> **Status:** Ready to run. **LIS v1.5.2** §6 **Phase 2**.
> **Prerequisite:** Phase 1b wired (recommended) so RS ranks are meaningful in scoring — but Phase 2 is **code-independent** of 1b.
>
> **Sequential context:** Run **after Track L-b** (or after Phase 1b if L-b deferred — prefer full order: 1b → L-b → Phase 2).

---

# Role

You are an **execution agent** on AFAC2026 Track 1. Implement **LIS Phase 2 only** — fix the RS dtype bug and make rhythm features real.

**Read (minimal):**
- `docs/LIS.md` §6 **Phase 2** + §7 **R1** (resolution-dependent RS)
- `src/features.py` (`_rs_features`, lines ~103–115), `tests/test_features.py`
- This prompt

**Out of scope:** Phase 3 feature batches, `normalize.py` changes, Track L-b (unless already done), `main.py` changes, LIS edits (flag only).

---

# LIS v1.5.2 context (trust these)

| Item | Note |
|---|---|
| **Root cause** | `datetime_utc.astype("int64") // 1_000_000` assumes **ns**; on `datetime64[ms]` (pandas 3.0.x) intervals collapse → `rs_interval_cv≈13.48`, `rs_burst_ratio≈0.99`. |
| **Fix** | `intervals_ms = group["datetime_utc"].diff().dropna().dt.total_seconds() * 1000` (drop negatives). **Dtype-portable.** |
| **Burst definition** | Share of intervals **< 100ms** (baseline/ref), **not** `< 0.25 * mean` (saturates when mean≈0). |
| **Fixture expectation** | After fix on real fixture: `rs_interval_cv ≈ 1.34` (not 13.48), `rs_burst_ratio ≈ 0` (~30s cadence). |
| **Label impact** | Fix does **not** fix n=1 fixture label (散户 on raw); that's H1/1b. Document before/after in report. |
| **Optional** | `rs_split_similarity = max(0, 1 - rs_interval_cv)` — add if LIS Phase 2 task 4 applies; buy/sell interval CV only if `side` exists. |

---

# Hard rules

1. **Intraday-only** — intervals from same tick group only.
2. **No hard-coding** — burst threshold as named constant in `config.py` if not already (e.g. `RS_BURST_THRESHOLD_MS = 100`).
3. **No answer-feedback**.
4. **PI unaffected** — uses `hour`/`minute`, not `datetime_utc` int cast.

---

# What to build

## Goal

Replace `_rs_features` interval computation; update `rs_burst_ratio` definition; add tests with hand-computed expectations.

## Files

| Action | Path |
|--------|------|
| Modify | `src/features.py` — `_rs_features` |
| Modify | `tests/test_features.py` — RS tests |
| Optional | `config.py` — `RS_BURST_THRESHOLD_MS` |

---

# TDD workflow

1. **2.1** Write `test_rs_intervals_dtype_portable` (**fail first**): synthetic group with `datetime_utc` at **30s** spacing (`pd.to_datetime` with `unit="ms"` or explicit `datetime64[ms]`) → assert mean interval ≈ 30000 ms, **not** 0.
2. **2.2** Run → **FAIL** on current code.
3. **2.3** Implement resolution-robust diff per LIS.
4. **2.4** Add `test_rs_uniform_cadence_low_cv` and `test_rs_burst_sub_100ms` per LIS tasks 2–3.
5. **2.5** Optional: `test_rs_fixture_sane` on `samples/AFAC2026.xlsx` ingest path — document cv/burst before/after (may skip if ingest-heavy; prefer unit synthetic tests).
6. **2.6** Full suite + smoke:
   ```bash
   pytest tests/test_features.py -q -k rs
   pytest tests/ -q
   python main.py --input samples/AFAC2026.xlsx -o outputs/
   ```

**Commit message:** `fix: RS interval computation dtype-portable (Phase 2)`

---

# Acceptance criteria (Phase 2 only)

- [ ] Intervals use `.diff().dt.total_seconds() * 1000` (or equivalent dtype-safe method)
- [ ] 30s synthetic group → intervals ≈ 30000 ms
- [ ] Uniform cadence → low `rs_interval_cv`; irregular → higher CV (hand-checked)
- [ ] `rs_burst_ratio` = share of intervals < 100ms (config constant OK)
- [ ] Full suite green
- [ ] xlsx smoke valid CSVs
- [ ] Document fixture before/after cv/burst in session report

**Not required:** multi-stock scoring panel (Phase 1b), proxy-F1 delta.

---

# When done, report

1. Commands + counts
2. Files changed
3. Acceptance checklist
4. Fixture rs_interval_cv / rs_burst_ratio before → after
5. xlsx emitted capital_type (may still be 散户)
6. Contradictions with LIS

Begin with 2.1.
