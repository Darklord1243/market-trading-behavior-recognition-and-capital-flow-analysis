# P4 — 000657.SZ / 20260622 label audit (Slice 5B guard blocker)

**Slice:** Track 1 Slice 5B follow-up · **Parent:** docs/hypotheses/p4-youzi-guard-tightening.md
**Branch:** feat/phase6-parquet-submit · HEAD: 9c5a06d (+ d2aeeb8 5C.1)
**Row:** stock_code=000657.SZ, transaction_date=20260622, truth=游资, capital_intention=买入, confidence=0.55
**Scope:** LHB-only re-read. No code/CSV changes made.

---

## 1. Scorer replay (Step 3) — blocker confirmed unchanged

`score_rows` must be built against the **full per-date universe matrix**, not a single-stock
matrix (cross-sectional rank/percentile features depend on the whole day's panel; a
single-stock replay gives a materially different, wrong result — 0.59/0.554/0.192, gap=0.036
— because it silently drops the panel context). Re-run against the correct per-date matrix
(all codes traded 2026-06-22) reproduces the documented blocker exactly:

```
000657.SZ 20260622  scores=[0.573, 0.570, 0.201]  truth=游资  pred=游资 (bare arg-max)
gap (score_yz − score_qt) = 0.0030
```

Confirmed lowest-margin row across the entire through-0624 subset (77 rows, 6 dates) — the
single blocker for Slice 5B at any `YOUZI_WIN_MARGIN ≥ 0.005`. Matches
docs/hypotheses/p4-youzi-guard-tightening.md §5 exactly.

## 2. LHB seat pull (East Money datacenter API, single-day, post-market)

`scripts/fetch_lhb_seats.py 000657 2026-06-22`, source:
https://data.eastmoney.com/stock/lhb,2026-06-22,000657.html

**Trigger:** `日涨幅偏离值达到7%的前5只证券` (single-day price-deviation ≥7% list — NOT the
3-day cumulative list). chg=+10.002%, turnover=5.72%. Meta line "3家机构买入，成功率41.90%"
is East Money's historical-stat annotation for this stock/trigger combo, not a same-day seat
count — it does not change the seat arithmetic below.

**BUY TOP5** (raw yuan):

| Seat | buy | sell | net |
|---|---:|---:|---:|
| 深股通专用 (STRIP) | 821,079,275.75 | 566,812,070.91 | 254,267,204.84 |
| 国泰海通·武汉紫阳东路 (游资) | 207,747,471 | 569,067 | **+207,178,404** |
| 机构专用 | 182,894,557.9 | 0 | +182,894,557.9 |
| 机构专用 | 174,340,375.42 | 180,667,913.78 | −6,327,538.36 |
| 机构专用 | 147,502,738.7 | 67,305,714 | +80,197,024.7 |

**SELL TOP5** (raw yuan):

| Seat | buy | sell | net |
|---|---:|---:|---:|
| 深股通专用 (STRIP, dup) | 821,079,275.75 | 566,812,070.91 | 254,267,204.84 |
| 机构专用 (dup of buy-row-4) | 174,340,375.42 | 180,667,913.78 | −6,327,538.36 |
| 开源证券·西安太华路 (游资) | 21,479 | 115,392,774 | **−115,371,295** |
| 机构专用 | 0 | 115,179,742 | −115,179,742 |
| 机构专用 | 0 | 114,530,808 | −114,530,808 |

## 3. Post-strip arithmetic (万元, after removing 深股通专用)

| Actor class | Seat | net (万) |
|---|---|---:|
| 游资 (buy) | 武汉紫阳东路 | **+20,718** |
| 机构 (buy) | seat A | +18,289 |
| 机构 (buy/sell churn) | seat B | −633 |
| 机构 (buy) | seat C | +8,020 |
| 游资 (sell) | 开源西安 | **−11,537** |
| 机构 (sell) | seat D | −11,518 |
| 机构 (sell) | seat E | −11,453 |

- **Named 游资 buy-side net:** +20,718万 — the single largest net position of any seat in
  either top-5 list, larger than any individual institutional seat.
- **机构专用 buy-side block:** +18,289 + (−633) + 8,020 = **+25,676万** net
  (or +26,309万 summing only the two net-positive institutional rows).
- **Ratio (named 游资 buy / institutional buy block):** 20,718 / 25,676 ≈ **80.7%**
  (or 20,718 / 26,309 ≈ 78.7% against the positive-only denominator).
- Per docs/human_guides/track_v_validation_labels.md §4 working hypothesis
  ("named 游资 < ~25% of top-4 机构 net-buy block → lean 量化"): this row sits at **~79–81%**,
  far above the 25% cutoff — the hypothesis's own threshold argues *for* 游资, not against it.
- **Sell-side confounder:** 开源西安, a *different* named 游资-tier seat, is distributing
  −11,537万 the same day. This is not evidence of institutional distribution — it is a second
  hot-money seat rotating out, a pattern consistent with (not contradictory to) a 游资-driven
  print: one 游资 group buys aggressively into the +10% move while another books profit/exits.
- Institutional seats appear on **both** sides (+25,676万 buy vs −22,971 to −23,604万 sell
  across distinct seats, plus one seat that round-trips both buy and sell same day for a net
  of only −633万). This is inconsistent with a single coordinated institutional accumulation
  or distribution story — it reads as index/quant-adjacent liquidity flow crossing a hot-money
  driven spike, not the primary directional driver.

## 4. Cross-check vs existing CSV notes

CSV notes (tests/fixtures/validation_labels.csv, row ~44): "buy-top1 国泰海通武汉紫阳东路
+20718万; buy-side also 机构专用 +8020/+18289万 confounds … LHB 游资 read; microstructure
may score 量化."

| Claim | Independent re-read | Match |
|---|---|---|
| 武汉紫阳东路 +20718万 | +20,718万 (207,178,404 / 1万) | **Exact match** |
| 机构专用 +8020万 | +8,020万 (80,197,024.7 / 1万) | **Exact match** |
| 机构专用 +18289万 | +18,289万 (182,894,557.9 / 1万) | **Exact match** |
| "microstructure may score 量化" | Confirmed — gap=0.003, near-tie | Confirmed as scorer note, not LHB evidence |

Seat-level arithmetic reproduces the CSV author's numbers exactly (no rounding drift). The
CSV's characterization of this row as "confounded but 游资-led" is independently corroborated:
the raw LHB seat data itself skews toward 游资 dominance (~80% of the institutional block),
not toward institutions. The original notes did not have the ratio computed against the guide's
25% threshold — doing so here removes the ambiguity the BORDERLINE flag implied.

## 5. Verdict

**KEEP 游资.**

- Single largest net-buy actor is a named 游资-tier seat, exceeding any individual
  institutional seat.
- Named 游资 buy-side dominance (~79–81% of the institutional buy block) sits far above the
  guide's own 25% "lean 量化" cutoff — the guide's threshold, applied honestly, argues for
  keeping the label.
- The sell-side institutional/游资 mix is a confounder for the *scorer's microstructure
  features* (explaining the gap=0.003 near-tie), not for the LHB-truth label itself — no
  independent evidence surfaced that institutions drove this print.
- Confidence: original 0.55 is defensible as-is (still a near-tie under the scorer, and two
  large institutional seats are genuinely present). Given the seat arithmetic is unambiguous
  in identifying the largest single actor as 游资, a case exists for nudging confidence upward,
  but that judgment call is left to the human — not made here (no CSV edit performed).

## 6. Gate implication

- Slice 5B (YOUZI_WIN_MARGIN) stays **falsified as documented**. This row is *correctly*
  labeled 游资 by LHB evidence — softening the through-0624 floor to "spare" it would be
  fitting the gate to a row that is not actually mislabeled. Do not revisit margin=0.03 on the
  strength of this audit.
- No CSV edit recommended. No feature/threshold change recommended.

---

**Recommended human action:** No action needed — label confirmed correct as-is; close this
audit without a CSV change.

**Slice 5B′ re-probe warranted?** No. The blocker is not a label error; re-probing the margin
sweep would not change the through-0624 floor outcome. Slice 5B remains closed per
[[slice5b-youzi-guard-falsified]] until a genuine label defect or a different gate-floor
decision is raised by the human lead.
