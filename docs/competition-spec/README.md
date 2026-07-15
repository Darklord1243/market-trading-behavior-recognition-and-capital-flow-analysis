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
| [`../official_guidance/`](../official_guidance/) | Baseline guide, FAQ/clarifications, score-improvement tutorial |
| [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md) / [`.zh.md`](../official_guidance/b-board-rules.zh.md) | **Board B ops authority** (window, best-of-day, 9-day WMA) — start here for B-board work |
| [`../official_guidance/README.md`](../official_guidance/README.md) | Index for agents into official_guidance |

## Cross-reference notes (resolved tensions)

These came up when cleaning the pasted specs against [`../official_guidance/competition-clarifications.md`](../official_guidance/competition-clarifications.md) and the project brief:

1. **Submission window** — §5.1 A-board paste says before **23:59** same day; A-board FAQ used **18:00 → 08:00**. **Board B (from 2026-07-13)** uses **T+1 15:00 – T+2 14:59** for trading day T — see [`../official_guidance/b-board-rules.en.md`](../official_guidance/b-board-rules.en.md). Do not apply the A-board window to B-board submits.
2. **Daily multi-submit aggregation** — older A paste often “latest wins”; **Board B keeps the day’s highest score**. Final ranking = **9-day WMA** (weights 9…1 / 45), not an unspecified moving average.
3. **Label strings** — English spec examples use English words (`Hot Money`, `Buy`, `Neutral`). **Submitted CSVs must use Chinese** exactly: `游资` / `量化` / `散户` (bare `量化`, never `量化机构`) for `capital_type`. Intention strings are freer on Board B for F1 (see clarifications §6); repo still emits `买入` / `卖出` / `T0交易`.
4. **"Neutral" vs `T0交易`** — Task objectives mention buy/sell/neutral; worked examples and baseline often use **`T0交易`**. Board B Q&A: intention content unrestricted; F1 focuses on `capital_type`.
5. **"Market phase recognition score"** — §5.3 mentions a third F1 component (行情阶段) alongside participant type and direction intent. Track 1's scored outputs in §5.2 are only Task 1 (clustering) and Task 2 (type + intent). Treat the phase score as either rolled into Task 2 evaluation or a legacy spec phrase — not a third CSV we submit. Board B Q&A: Task 1 cohesion/separation use **contestant cluster labels**.
6. **A-board data period** — §4.2 lists Test Set A as `2026/06/08–07/10`; §5.1 A-board runs `2026/06/09–07/10`. One-day offset at the start; follow §5.1 for submission calendar.
7. **B-board entry** — Chinese §5.1 adds: teams need a **valid A-board result** to enter B-board (not stated in the English paste).
8. **`pattern_explanation`** — not scored on A-board; **included in Board B interpretability** (clarifications §6).
