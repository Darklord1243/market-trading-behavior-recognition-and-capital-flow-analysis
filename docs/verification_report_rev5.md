> ⚠️ **SUPERSEDED (2026-06-14) — capital_type is now 3 classes.**
> A direct organizer answer (DingTalk) confirmed `capital_type` = **`{游资, 量化, 散户}`**
> (bare `量化`, not `量化机构`; `散户` is a real modelled class). Any 2-class
> `{游资, 量化机构}` assertion in this report is overturned by that answer, which
> overrides the baseline guide. Current code/tests/brief Rev. 7 carry the fix.
> Kept for audit history only.

# Verification Report — Project Brief **Rev. 5** vs repo materials (re-adjudication)

**Role:** Fact-checker only. No brief edits, no code. Findings only.
**Date:** 2026-06-13.
**Predecessor:** `docs/verification_report.md` (Rev. 4 pass) — historical, not treated as source of truth.
**Trigger:** Brief bumped to **Rev. 5**; official Tianchi spec added under `docs/competition-spec/`.
**Question:** Are the four substantive gaps (U1, U2–U5, X1, O1) resolved, and did Rev. 5 / the new
spec introduce anything new?

---

## Sources inspected this pass (opened, not assumed)

| Source | Inspected | Key facts pulled |
|--------|-----------|------------------|
| `docs/AFAC2026_Track1_Project_Brief.docx` (**Rev. 5**, 108 blocks) | full text + tables via `python-docx` | changelog P4; provenance table (after P18); P11/P57/P85 Case-1 wording; P131/P142 submit.zip |
| `docs/competition-spec/topic-specifications-and-data.en.md` | full read | §4.2 dataset table; §5.1 A/B logistics; §5.3 F1 components; §7.2 Case 1 |
| `docs/competition-spec/topic-specifications-and-data.zh.md` | byte-grep | §7.2 (案例/缩量/24/70%/恒工) present — bilingual parity confirmed |
| `docs/competition-spec/competition-introduction.en.md` | full read | team ≤3; real-name auth **Jul 20 12:00**; phases/calendar |
| `docs/competition-spec/reference-feature-set.md` | full read + row count | **exactly 89 field rows**; families oss12/rs8/cb8/ap8/obp8/pd23/pi8 + metadata |
| `docs/competition-spec/README.md` | full read | cross-reference notes #1–6 (incl. "market phase" resolution) |
| `docs/competition-spec/assets/7.2-case-1.png` | stat | present, 738,307 bytes (恒工精密 intraday chart, 2026-04-28) |
| `docs/official_guidance/*` + `samples/*` | re-checked vs Rev.4 pass | label asserts, format rules, byte facts unchanged |

---

## Per-gap verdicts

### U1 — Case 1 / 24 ms CV / ~70 % cancel  →  **RESOLVED** (with one stale-text caveat)

**Case 1 is now repo-citeable.** `topic-specifications-and-data.en.md` **§7.2 "Shrinking Volume Game"**
(L192–213) carries every figure the brief leans on, and the `.zh.md` twin + the official screenshot
(`assets/7.2-case-1.png`) corroborate it:

| Brief claim (P57/P85) | Spec §7.2 location | Match |
|-----------------------|--------------------|-------|
| ~70 % cancellation | L208 "**~70% of orders cancelled**" | ✅ |
| CV ~24 ms (machine rhythm) | L209 "intervals **CV ~24ms** (machine/algorithmic)" | ✅ |
| iceberg split → `rs_split_similarity` | L211 "**Iceberg splitting**" | ✅ |
| bid-sweeping → `ap_unilateral_intensity` | L211 "**aggressive selling** (wiping multiple bid levels)" | ✅ |
| open/close >70 % concentration | L212 "**>70% of orders** at open and close" | ✅ |
| fixture ≠ Case-1 stock | L198 "stock codes in §7 are **not** the repo fixture (603997.SH)"; Case stock = 恒工精密, 2026-04-28 | ✅ brief P85 says exactly this |

The remediation the original finding asked for is **fully present in Rev. 5**:
- Brief P57 now cites "**competition spec §7.2**"; P85 reframes unit tests into **(1) internal-consistency
  backbone** (active_buy+active_sell≈1, diff≥0, hh∈8–16, OSS shares sum) **+ (2) Case-1 directional
  sanity**, explicitly noting the 24 ms/70 % figures describe a **different stock** → directional, not
  exact asserts on the fixture. ✅
- Tutorial **51 %/71 %/32 %** numbers are **demoted** in P76: "from the tutorial's example **PROMPT, not
  ground truth**; use each cluster's ACTUAL centroid." ✅
- Bonus: every Case-1 signal the brief maps (`rs_interval_cv`, `rs_split_similarity`,
  `ap_unilateral_intensity`, `pi_open_30min/close_10min_amount_pct`, `cb_cancel_order_ratio`) **exists
  verbatim** in `reference-feature-set.md` — the anchor and the feature spec now line up.

**Caveat (new minor ⚠️ — see N1):** three places in the brief still say the spec is *missing* and must
be *added* ("ensure that spec PDF is in docs/" P11; "It was referenced but is **missing from docs/**…
add to repo" provenance table; "ensure the spec is in docs/" P57). That is now **factually stale** — the
spec **is** in `docs/competition-spec/` (as reorganized Markdown + the §7.2 PNG, not a PDF). Substance is
resolved; the TODO scaffolding text simply wasn't deleted after the spec landed.

### U2–U5 — logistics facts (T+5/3-day, 3/day, ≥8 B-board days, calendar, team)  →  **RESOLVED** (provenance note now over-cautious)

Every one is now citeable from the added spec:

| ID | Brief claim | Now citeable at | Status |
|----|-------------|-----------------|--------|
| U2 | "next **3 trading days**, ranked **~T+5**, **moving weighted average**" (P12) | topic-spec §5.1 L65–66 — verbatim ("next 3 trading days; rankings published around T+5"; "moving weighted average of daily scores") | ✅ |
| U3 | "**3 submissions/day**" (P94, P119) | topic-spec §5.1 A-board L75 "Up to 3 per day"; competition-intro L55 | ✅ |
| U4 | "**≥8 B-board days** (fewer = excluded)" (P170, P173) | topic-spec §5.1 B-board L88 "Fewer than 8 trading days → excluded from final ranking" | ✅ |
| U5a | July calendar (A→Jul 10, B Jul 13–24, report Jul 28–Aug 5) | topic-spec §4.2/§5.1; competition-intro Phase 1–3 | ✅ |
| U5b | "Real-name auth **by Jul 20, 12:00**" (header) | competition-intro L43/L47 "by July 20, 2026, 12:00" | ✅ exact |
| U5c | "**2–3 members**" (header) | competition-intro L16 "individually or a team of **up to 3**" | ⚠️ minor: spec allows **solo (1)**; brief's "2–3" excludes the individual case |

Rev. 5 also added the requested **provenance callout** (table after P18) separating repo-verified facts
from "live-page facts — CONFIRM before relying." Good practice — but it now lists U2/U3/U4/U5 calendar as
"**not in repo files**," which is **no longer true** (they are in `competition-spec/`). The advice to
double-check the DQ-critical ones (≥8 days, submission caps) on the live Tianchi page remains prudent
because the spec is a reorganized copy-paste — but the "not in repo" framing is stale. Net: **substance
resolved; the provenance note is now over-cautious rather than wrong-direction.**

### X1 — P22 "reverse-engineer class balance" vs "ZERO signal"  →  **RESOLVED**

Rev. 5 data-inventory row for `predict_result.csv` now reads: *"labels are RANDOM (official FAQ)… **Use
for FORMAT ONLY** (column names/order, date format, encoding). **Read no signal from label values or their
distribution** (see §3)."* This matches §3 (P52, "Read ZERO signal… drop even the 'classes may be
balanced' prior"). The internal contradiction is gone. ✅

### O1 — `submit.zip` no-nested-folders guard  →  **RESOLVED**

Present in **both** required places:
- §8 output guard (P131): *"packs **submit.zip** with the two CSVs at the **ROOT (no nested folders —
  official format rule)**."* ✅
- §9 audit table (P142): dedicated row *"submit.zip | Both CSVs at the archive **ROOT — no nested
  folders** (official format rule)."* ✅

Backed by official text: baseline-guide L126 ("no nested folders") and topic-spec §5.4. ✅

---

## Findings table (Rev. 5 status — including A–D regression re-check + new items)

| # | Item | Status | Source (file + loc) | Brief § | Note |
|---|------|--------|---------------------|---------|------|
| A1 | `capital_type` = {游资, 量化机构} only; 散户 = placeholder | ✅ | baseline-guide L78/L424; sample bytes (散户/游资/**量化** present) | P23–25 | Unchanged from Rev.4; still correct & byte-verified |
| A2 | `capital_intention` = 买入/卖出/T0交易; "neutral" = loose English | ✅ **(now spec-backed)** | topic-spec §2 L30–31 + README #3 ("English spec uses 'neutral'… baseline code use `T0交易`") | P27 | Prior Rev.4 footnote ("'neutral' appears nowhere in repo") is **now closed** — the spec contains it |
| A3 | CSV format: 4 cols fixed order, YYYYMMDD, UTF-8-sig, no nulls/blank lines | ✅ | baseline-guide L126–131; topic-spec §5.4 L128–141 | P18, P131 | Spec §5.4 shows the exact 4-col layouts; consistent |
| A4 | `pattern_type` open/free-form | ✅ | clarifications Q3/A3; topic-spec §5.2 | P30, P69 | Unchanged; correct |
| B5 | `AFAC2026.xlsx` = raw L2 (4937×65, 603997.SH, dt=20260507, nested JSON) | ✅ | byte check (Rev.4 pass) | P24, P17 | Unchanged; byte-verified |
| B6 | "~89-col reference feature set… NOT a downloadable file" | ✅ **(now exact + spec-backed)** | `reference-feature-set.md` (**exactly 89 rows**, L3–4 "not shipped as downloadable"); topic-spec §3.1 L41 | P17 | "~89" is now **precisely 89**; all cited prefixes (rs_interval_cv, oss_*, cb_*, ap_*) present; negative claim confirmed |
| B7 | Official sample labels random → no signal | ✅ | clarifications L51 | P22, P52 | Now consistently stated (X1 fixed) |
| C8 | Cumulative → `diff()` | ✅ | baseline-guide L217/L335; byte: volume monotonic 0→30,193,038 | P41 | Unchanged |
| C9 | `hh` Beijing vs `date` UTC trap | ✅ | baseline-guide L218/L322; byte: hh∈[8..16], date epoch-ms | P37–39, P43 | Unchanged |
| C10 | CB zero in snapshot-only; need tick-cancel table | ✅ | baseline-guide L114; reference-feature-set L40–47 (cb_* incl. `cb_cancel_order_ratio`); byte: no cancel col, bidaskrate/diff≡0 | P44, P49 | Spec's 89-set now shows the cb_* fields the snapshot can't fill — reinforces the gap |
| C11 | OSS thresholds 50k/10k/1k | ✅ | baseline-guide L341–344 | P42 | Unchanged |
| D12 | DQ hard rules (intraday-only, no hard-coding, no eval-labels-in-training, reproducibility) | ✅ | baseline-guide L159–164; topic-spec §5.5 L162–169 | P11/P17/P129/P135–142 | Spec §5.5 adds an explicit audit row — brief matches |
| D13 | Nightly 18:00→08:00; transaction_date=yesterday | ✅ | clarifications L10–23; topic-spec §5.1 L80 ops note | P88–92 | Unchanged; spec cross-references the FAQ window |
| **N1** | Brief says the competition spec is **missing / must be added** ("spec PDF in docs/", "missing from docs/", "ensure the spec is in docs/") | ⚠️ **new (stale text)** | brief P11, provenance table, P57 vs actual `docs/competition-spec/` (present) | P11, P19, P57 | Substance of U1 is resolved, but these three TODO lines now **contradict the repo state**. Also mislabels the Markdown spec as a "PDF." Recommend updating to cite `docs/competition-spec/topic-specifications-and-data §7.2` |
| **N2** | Spec §5.3 lists a **third F1 component "market-phase recognition" (行情阶段)**; brief models only type + intention | ⚠️ **new (omission)** | topic-spec §5.3 L114 + README #4 (resolves it as "not a third CSV — rolled into Task 2 / legacy phrase") | (absent) | Low risk — README already resolves it and the brief's 2-head Task 2 aligns with that resolution — but the brief never acknowledges the "market phase" wording. Worth a one-line note so a reader who hits §5.3 isn't surprised |
| **N3** | Spec §4.2 "Sample set 1 = **20 stocks**, 2026/05/07" doesn't match shipped sample bytes | ⚠️ **new (spec-vs-bytes; brief is byte-accurate)** | topic-spec §4.2 L55 vs bytes: predict_result=198 stocks/19 dates, pattern_reco=20 rows, AFAC2026=1 stock/20260507 | P22, P24 | This is an **official spec** vagueness, not a brief error — the brief's inventory is byte-correct. Noting only so it isn't mistaken for a brief defect; the spec's "20 stocks/1 day" line loosely matches pattern_reco's 20 rows + the fixture's dt, not predict_result |
| **N4** | Team size "2–3" vs spec "up to 3 (incl. individual)" | ⚠️ **new (very minor)** | competition-intro L16/L45 | header | Brief excludes the solo case the spec permits; immaterial to a 2–3 person team but technically narrower |
| **N5** | A-board start one-day offset (spec §4.2 06/08 vs §5.1 06/09) | ✅ (not a brief issue) | topic-spec §4.2 vs §5.1; README #5 | — | Internal spec offset; README says follow §5.1; brief only cites the Jul 10 end, so unaffected |

---

## Is Case 1 now repo-citeable via `docs/competition-spec/`?

**Yes — unambiguously.** `docs/competition-spec/topic-specifications-and-data.en.md` **§7.2 "Shrinking
Volume Game"** (and its `.zh.md` twin "案例一", plus `assets/7.2-case-1.png`) contains, in repo, the exact
anchor figures the brief cites: **~70 % order cancellation**, rhythm intervals at **CV ~24 ms**, **iceberg
splitting**, **bid-level-sweeping aggressive selling**, and **>70 % of orders concentrated at open/close**.
A grep for these now hits the repo (it did not in the Rev. 4 pass). The §7.2 stock is **恒工精密
(2026-04-28)** — explicitly **not** the `603997.SH` fixture, exactly as the brief's P85 now states. The
only residual issue is **stale brief text (N1)** that still claims the spec is missing.

---

## VERDICT

**Sound to build from — yes.** All four originally-flagged substantive gaps are **RESOLVED**: U1 (Case 1
now cited to spec §7.2, tutorial numbers demoted, unit tests reframed to internal-consistency + directional
sanity, fixture≠Case-1 stock acknowledged), U2–U5 (all logistics now citeable from `competition-spec/`),
X1 (inventory row is format-only), O1 (no-nested-folders guard in both §8 and §9). The high-stakes core
(locked label vocabularies, byte-accurate data inventory, engineering traps, DQ red lines, nightly cadence)
remains correct and is now **more strongly cited** than in Rev. 4 — the 89-field set and the "neutral"→
`T0交易` mapping that were previously unverifiable are now in the repo. **No ❌ contradictions remain.**

Remaining amendments — all minor, none blocking:

1. **N1 (housekeeping, do first):** Delete/replace the three stale "spec is missing / add the spec PDF"
   notes (P11, provenance table, P57). Repoint them to `docs/competition-spec/topic-specifications-and-data §7.2`
   and call it the Markdown spec, not a PDF. As written, the brief contradicts the repo it ships in.
2. **N2:** Add one line acknowledging the spec §5.3 "market-phase recognition" F1 wording and that we
   (per spec README #4) fold it into Task 2 rather than emitting a third CSV — so the 2-head design is a
   stated decision, not an apparent miss.
3. **N4 (trivial):** "2–3 members" → "1–3 members" (or "up to 3") to match `competition-introduction`.
4. **Keep** the provenance table's advice to re-confirm the DQ-critical logistics (≥8 B-board days,
   submission caps, exact dates) on the live Tianchi page — but update its "not in repo files" framing,
   since these now ARE in `competition-spec/` (the live page is now a *second* check, not the *only* source).

N3/N5 are official-spec inconsistencies, not brief defects — no brief action required beyond optional notes.

**Recommendation: proceed to build.** Apply N1–N4 as a quick documentation cleanup pass; none of them
affect the architecture, the label design, the feature spec, or compliance. The brief is internally
consistent with the repo it now sits in, save for the stale "spec missing" lines (N1), which are a
delete-three-sentences fix.

*— End of Rev. 5 re-adjudication. No code written, no brief modified. Awaiting human review.*
