# §7 — Reproducibility & Compliance

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 1, 2, 22, 23, 24). This section is the **attestation for
> the TOP-15 code review** (spec §5.5); its evidence is the readiness audit
> `docs/report/repro-pack-readiness.md` and the frozen exhibits (ledger F1–F5), all re-verified
> 2026-07-06 on HEAD `b26bfed`.

The TOP-15 audit replays the full pipeline and disqualifies on any **code / doc / result mismatch**.
We built the report against a parity ledger precisely so this section can be an attestation, not a
promise. Point by point against the §5.5 requirements:

| §5.5 requirement | Status | Evidence |
|---|---|---|
| Dependencies in `init_env.sh` | ✅ | idempotent, relative-path installer → `requirements.txt` (`pandas>=1.3,<3`, numpy, scikit-learn, openpyxl, **pyarrow**, pytest) |
| Entry point `main.py` → `predict_result.csv` | ✅ | `main.py` writes both CSVs via `postprocess`; clean smoke run exit 0 (G3) |
| Hard-coding ban | ✅ | no per-stock rules (grep: only match is a comment), no random fill, thresholds in `config.py` (Row 23) |
| Timing — producible by market close | ⚠️ | per-`--date` run is intraday-reproducible; the nightly auto-"yesterday" calendar is a stub (§8) |
| Relative paths + comments | ✅ | no absolute paths in `src/`/`main.py`/`config.py`; contract comments in `main.py` + `init_env.sh` |
| Full replication, no mismatch | ✅ | F1–F4 re-froze to exact expected values (below); the one mismatch found was fixed and re-verified |

## 7.1 Frozen replication evidence (2026-07-06, HEAD `b26bfed`)

Every load-bearing number the report prints was reproduced from a timestamped command this cycle: **[CLAIM]**

- **Frozen ship gate** — labels ≤ 20260624 → **0.6773 / n=77** (游资 F1 0.59) (F1).
- **Corpus-split verify** — June **0.6438 / n=122**, July **0.7824 / n=32** (F2, Option A: reported as
  two slices, not averaged).
- **Intent floor** — **0.6750 / n=115** (F3).
- **Test suite** — **234 passed, 2 xfailed** in 120 s (F4).
- **Clean smoke** — `main.py` on the xlsx sample runs green end to end, 35-col matrix, both CSVs (G3).

## 7.2 One mismatch, found and fixed under discipline

The freeze itself surfaced a real defect, which we record rather than hide: on **pandas 3.0.3** the
suite first came back **233 passed / 1 failed**, because pandas 3.0 stopped stringifying `NaN`→`"nan"`
and `_load_universe_codes` then leaked a float into `sorted()`. **[ADMIT]** We fixed it surgically —
`df[col].fillna("").astype(str)` plus a `pandas>=1.3,<3` pin — and re-verified **234 passed,
2 xfailed** (Row 24; ledger flag P1 / freeze F4). The production entry point was never affected (G3
green throughout). We also declared the previously-implicit `pyarrow` runtime dependency, without
which a clean-install auditor could not reproduce our parquet gates (readiness G1). **[CLAIM]** Both
edits are **committed as `b26bfed`.**

## 7.3 Compliance guarantees

The pipeline is byte-deterministic and seed-fixed, carries **no LLM in the inference path**, uses only
same-day cross-sectional information (no look-ahead, §3.4), and validates its own 3-class output
loudly — `postprocess.validate_predict` rejects the legacy `量化机构` string and requires the exact
`{游资, 量化, 散户}` vocabulary (Rows 1, 2, 22). **[CLAIM]** No threshold in the codebase was ever
tuned to a board score; the falsification record (§5.3) is the positive evidence that pre-registered
gates were honored. The residual reproducibility caveat — the stubbed holiday calendar — is stated in
**§8**, not smoothed over here.
