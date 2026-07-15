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
| _(first entry when a rule is derived)_ | | |
