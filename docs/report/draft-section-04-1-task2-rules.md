# §4.1 — Modeling: Task-2 as a transparent rule scorer (+ a declared stub head)

> **Draft status:** report-ready prose, Phase 3b. Inline **[CLAIM]** / **[ADMIT]** tags map 1:1 to
> `docs/report/code-parity-ledger.md` (Rows 8, 9, 22, 23). Gate evidence for these rules lives in
> §5.1–5.2 and is cross-referenced, not repeated.

Task 2 predicts two fields per stock-day: **capital type** (3-class `{游资, 量化, 散户}`) and
**capital intention** (net-direction). We score both with a **transparent, inspectable rule engine**
rather than a gradient-boosted model — a choice we make deliberately and defend openly.

**Capital type** is assigned by `src/rules.py::score_capital_type` (L141): a small set of global,
per-class dimension scores over the day's features, producing one of the three required labels. **[CLAIM]**
There is no per-stock logic and no random fill — thresholds are global constants in `config.py`
(§7; Row 23). **[CLAIM]** **Intention** is a **banded net-direction gate on raw rows** —
`get_intention` (L204) with `_intent_confidence` — reading the *raw* feature matrix with **absolute**
thresholds, not panel-relative quantiles (the rank-relative variant was falsified as Slice 3, §5.3). **[CLAIM]**
The 3-class output is guarded loudly: `postprocess.validate_predict` rejects the old 2-class
`量化机构` string and requires bare `量化` / `散户` / `游资`, so a malformed label fails the run rather
than reaching the board (Row 22). **[CLAIM]**

The pointed choice is **rules over GBDT**. `src/model.py` (`CapitalTypeHead.fit/predict`) is a
**declared pass-through STUB**: it returns the weak labels unchanged, and the seam is documented so a
LightGBM head could be dropped in later without disturbing the rest of the pipeline. **[CLAIM]** We
did not ship a trained head for one honest reason: under the partially-observable objective (§5), any
GBDT lift is **offline-unmeasurable** — our proxy is a small, class-imbalanced smoke detector (§5.2),
not a leaderboard simulator, so a model that "improves" the proxy could easily be overfitting its
noise. **[ADMIT: a trained head might add real lift we cannot verify — we forgo unverifiable lift in
favor of an auditable scorer.]** This is simultaneously a compliance win (fully inspectable, no hidden
state, §5.5 code audit) and a stated limitation (§8).

The rules are not asserted to be good in the abstract; their credibility is the **gate trail** in
§5.1–5.2 — the frozen ship gate of 0.6773 / n=77 on the capital-type proxy and the 0.6750 / n=115
intent floor, with 游资 the openly-weakest class. Those numbers, and the falsification record that
shaped the thresholds (§5.3), are the evidence for this section.
