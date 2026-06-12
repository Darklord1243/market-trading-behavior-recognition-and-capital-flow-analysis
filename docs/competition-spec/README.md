# Competition Spec (Official — Tianchi)

Original competition materials, reorganized from copy-pasted Tianchi web pages into readable Markdown.

## Files

| File | Language | Content |
|------|----------|---------|
| [`competition-introduction.en.md`](./competition-introduction.en.md) | English | Challenge Group rules, phases, awards, eligibility |
| [`competition-introduction.zh.md`](./competition-introduction.zh.md) | 中文 | 挑战组参赛规则、流程、奖项 |
| [`topic-specifications-and-data.en.md`](./topic-specifications-and-data.en.md) | English | Track 1 task spec, rules, submission, **Case 1 (§7.2)** |
| [`topic-specifications-and-data.zh.md`](./topic-specifications-and-data.zh.md) | 中文 | 赛题一任务说明、规则、提交、**案例一 (§7.2)** |
| [`reference-feature-set.md`](./reference-feature-set.md) | bilingual | §3.1 feature field list (89 columns) |
| [`assets/7.2-case-1.png`](./assets/7.2-case-1.png) | image | Official §7.2 illustration from Tianchi (linked from topic spec) |

## How this relates to other `docs/` files

| Document | Role |
|----------|------|
| [`../AFAC2026_Track1_Project_Brief.docx`](../AFAC2026_Track1_Project_Brief.docx) | **Single source of truth** for our implementation plan |
| `competition-spec/` (this folder) | Verbatim-ish official spec from Tianchi — citeable ground truth for logistics & Case 1 |
| [`../official_guidance/`](../official_guidance/) | Baseline guide, FAQ/clarifications, score-improvement tutorial (reorganized by organizers/community) |

## Cross-reference notes (resolved tensions)

These came up when cleaning the pasted specs against [`../official_guidance/competition-clarifications.md`](../official_guidance/competition-clarifications.md) and the project brief:

1. **Submission window** — §5.1 states results must be submitted before **23:59** on the trading day. The platform FAQ adds an **18:00 → 08:00** instant-feedback window (answers post ~18:00; upload yesterday's file before 08:00 next day). Treat both as official; the FAQ governs nightly ops.
2. **Label strings** — English spec examples use English words (`Hot Money`, `Buy`, `Neutral`). **Submitted CSVs must use Chinese** exactly: `游资` / `量化机构` and `买入` / `卖出` / `T0交易` (see baseline guide asserts).
3. **"Neutral" vs `T0交易`** — Task objectives mention buy/sell/neutral in English and 买/卖/中性 in Chinese; worked examples and baseline code use **`T0交易`** as the third intention class.
4. **"Market phase recognition score"** — §5.3 mentions a third F1 component (行情阶段) alongside participant type and direction intent. Track 1's scored outputs in §5.2 are only Task 1 (clustering) and Task 2 (type + intent). Treat the phase score as either rolled into Task 2 evaluation or a legacy spec phrase — not a third CSV we submit.
5. **A-board data period** — §4.2 lists Test Set A as `2026/06/08–07/10`; §5.1 A-board runs `2026/06/09–07/10`. One-day offset at the start; follow §5.1 for submission calendar.
6. **B-board entry** — Chinese §5.1 adds: teams need a **valid A-board result** to enter B-board (not stated in the English paste).
