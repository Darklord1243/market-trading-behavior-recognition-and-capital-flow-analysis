# 机构 (institutional) LHB adjudication ledger

> Populated by the labeling **guide** (`docs/prompts/fable5-guide-lhb-labeling.md` §3b). Purpose: `capital_type` has no 机构 class, so institutional LHB cases are HELD here — not forced into {游资, 量化, 散户} and **not** added to `tests/fixtures/validation_labels.csv` — until enough cases reveal a defensible treatment rule.
>
> **Compliance:** these are reasoned priors from PUBLIC LHB only. The true mapping (platform T+5 truth) is DQ-forbidden to use. Nothing here is a confirmed label.

## Held cases

| stock_code | date | seat | 上榜原因 | direction | turnover note | why unresolved |
|------------|------|------|----------|-----------|---------------|----------------|
| _(append rows here)_ | | | | | | |

## Derived rule (fill once ≥ ~15 held cases show a stable pattern)

- **Status:** UNRESOLVED — no rule yet.
- When resolved: state the rule + the evidence pattern, then propagate to `fable5-guide-lhb-labeling.md` §3b and `sonnet-lhb-labeling-dig.md` §4 step 2, and record the change below.

### Change log
| date | change | by |
|------|--------|----|
| 2026-07-16 | Executor prompt `sonnet-lhb-labeling-dig.md` §4 step-2 aligned with §3b: 机构专用-dominant cases now SURFACED as `机构-unresolved` (were silently SKIPPED, starving this ledger). No treatment rule derived yet — 0 held cases. Same edit activated the §4 step-3 non-LHB name-prior 量化 channel (separate concern, logged here for prompt-version audit). | Fable 5 (guide session) |
