# GIB R1 V4 — Professional editorial benchmark and release gate (2026-10-30)

## Source and frozen contract
- Preserve V3 frozen main release contract, 4-stage workflow, all publishing and LINE OFF; this is a QA-only editorial system change.
- Only genuinely approved Inoreader 24-feed source items are accepted as attributable news; original publisher headline and URL remain untouched. Do not make external claim verification a prerequisite for the source's *eligibility*. Do not treat attribution as an independent truth certification.
- No unlicensed republishing of original full newspaper articles. News summaries must be independently written, traceable to provided source title and RSS excerpt, with uncertainty and speakers retained.

## WSJ / Economist comparative editing principles
- Follow clear, plain factual language and **strong news/opinion separation** (The Wall Street Journal publicly states this as a central newsroom principle).
- Provide a coherent explanatory path: **what happened → where/who → reported consequences and limits → why it matters → plausible mechanism → opposing interpretation → what to watch next**. The Economist describes its mission as explaining what happens, why it matters and what might happen next.
- Apply these principles to *synthesis quality*. Do not falsely claim the project possesses original reporting, direct interviews, investigative verification, publisher approval or equivalence to either newsroom.

## Hard quality gate for each candidate issue
1. 24 distinct attributable publisher news items, 12 main + 12 supplement; each has original title, original HTTPS URL and authoring provenance.
2. All 24 source-news briefs: at least two meaningful sentences, anchored event and location/scope when supported; no source-unsupported numeric tokens; source claim is attributed; no invented inference filling missing facts.
3. All 24 separately identified editorial notes and distinct future monitoring signals; no inference may silently enter the source-news body.
4. Meaningful ranking based on global impact, policy certainty, cross-border effects and new information—not merely rank-score, news volume or repeated headlines.
5. Special-watch section must identify the specific source-reported event, potential channels, an alternative explanation and testable indicators.
6. At least six original *independent analysis essays* in deep edition, each with >=900 Chinese/text characters including specific context, mechanisms, alternatives, source-linked articles and invalidation. No padded repeated caution paragraphs or copyrighted full articles.
7. Deliver an Essential HTML plus Deep HTML; test browser widths 1440/768/390 for BOTH editions, all internal anchors, 24 publisher links and 24 source disclosure widgets.
8. Produce real EPUB3 archives with valid mimetype, OPF, container XML and XHTML. Physical BOOX acceptance is a separate stage and must not be claimed by ZIP validity.
9. A numeric quality score is only an explicit editorial rubric, not Gemini self-rating or external WSJ/Economist endorsement. Fail closed on untested rendered content.
10. DO NOT merge to main, publish Pages, send LINE or enable schedule automatically.

## Completed historical QA run — 2026-10-30
- Historical frozen 2026-10-30 collection; no re-collection of RSS.
- Latest standalone HTML artifacts: `GIB_R1_Essential_Editorial_V4_20261030.html` and `GIB_R1_Editorial_Desk_V4_20261030.html`, packaged to conversation workspace, not automatically committed to this branch.
- 24 original publisher links, 24 eligible source headlines, 24 meaningful separate editorial notes and 24 follow-up signals.
- Six coherent deep research articles with measured text counts all over 900; 19/19 base content checks.
- 6/6 Chromium responsive variants (Deep/Essential x 1440/768/390), zero horizontal overflow, no internal broken anchors, 24 functional source expanders; a broken Essential-to-Deep anchor was caught and fixed before the final result.
- Two real EPUB3 output files structurally checked. No BOOX physical device test.
- Explicit six-part **internal** rubric evaluates source fidelity, news density, importance ranking, explanatory mechanisms, alternative scenarios and reading; 91/100 for source-eligible *editorial synthesis*, NOT a WSJ/Economist professional newsroom equivalency grade; no independent human signoff.
- Formal **release status OFF**. Applying the static finished issue design to future scheduled automatic output must be separately tested before any merge.

## Critical negative tests
- Missing individual publisher source → reject.
- New numeric event claim absent from title/excerpt → reject.
- One-sentence paraphrase, generic low-information watch, unlabelled AI counter-view → reject.
- Any broken internal navigation, mobile horizontal overflow, or missing source disclosure → reject.
- Essays lacking explicit scenario, counterargument or observable followup → reject.
- Source-eligible original article may not be rejected just because independent verification is missing.
