# Global Intelligence Brief V1.6 — Full editorial pipeline / execution contract

**Status: Engineering QA — not approved for publication.** Two products are independent:
this repo is Global Intelligence Brief; `zinc-intelligence-v26` is unchanged.

## 2026-10-28 owner-approved integrated P2 QA execution rules (v1)

The owner explicitly authorized a **single integrated implementation and QA milestone** and requested **no fragmented manual GitHub runs**. The original `config/frozen_contract.json` (2026-10-23-approved-v1) remains immutable; the existing six sections and dual reading lengths are not renegotiated. These implementation rules are subordinate to the original approved editorial contract.

- **P2 data contract:** use the original 24 Inoreader Free OPML publisher RSS feeds (already proven live in P1); join their original URLs, timestamps, source groups and evidence into `canonical_issue` of `gib/newsroom_v16.py`. Retain existing external free providers only within the approved data-source boundary. Do not invent specialist industry priorities.
- **One newsroom, two reading routes:** the SAME canonical issue and real morning snapshot feed source-attributed Style C internal HTML and V1.6 Essential/Deep editorial QA. Avoid a third disconnected newsroom or duplicated event identities. Both must carry prominent HOLD labels until independently approved.
- **News judgment and evidence:** independently meaningful international significance governs headlines; do not force quotas without sufficient verified news. Highlight three leading developments, world briefs, substantial analysis, source dates, counterevidence and invalidation/monitoring. RSS snippets cannot validate deep causal claims. Facts without primary/source-location proof stay `ATTRIBUTED_UNVERIFIED`.
- **Gemini optional/free-only two-pass:** run through the existing controlled `gib/gemini_editor_v16.py`; report actual status, model, pass outcomes and rejected invented facts, without asserting subscriptions are API keys. Never incur paid fallback, silently loosen validation or promote model prose to VERIFIED.
- **Evening:** use a persisted and completed same-day morning issue. Distinguish factual/material updates from syndication. Absent baseline = marked HOLD, not a delta edition.
- **Self-test, one deliverable:** perform CI, actual publisher RSS run, end-to-end evidence/link/Style C and dual-version QA before asking the owner to do anything. Provide one concise acceptance report with real run IDs, pass/fail evidence, preview artifact links and unresolved human/BOOX limitations.
- **Nonnegotiable change control:** any modification beyond approved P2 integration—contract, sections, source/editorial priority, CSS redesign, costs, new integrations, scheduled publication, LINE, public Pages, BOOX/P3 release—requires separate affirmative owner approval **before** the edit. Keep publication OFF.

This document describes implementation and verification authority, **not** permission to publish. P3 remains genuine BOOX NeoReader review plus 10 trading days/20 issues and explicit owner signoff.

## Decision from the editorial reference review

- **WSJ:** copy the information-hierarchy *principle* — dominant main story, secondary briefs, clearly separated analysis. Do not reuse their layout assets or copyrighted text.
- **The Economist / The World in Brief:** short global update paragraphs and more substantial small articles. Its developer docs describe “Gobbets” and “Chunks”; its content API requires entitlements. Do not scrape or reproduce protected publisher material.
- **Global Intelligence Brief:** original Traditional Chinese synthesis, dated source links, **analysis as distinct from facts**; stop using identically sized colored cards for every article.
- **Layout 01:** cream `#FAF8F2`, navy `#142D46`, teal, amber; 3:4 cover; actual BOOX EPUB body is reflowable, one-column and adjustable, no fixed sidebar. Bookmarks and TOC are device reader controls rather than screenshots.

## Fixed, non-negotiable time contract (Asia/Taipei)

- Global Morning 07:30 daily: previous night through morning latest sources; Essential + Deep. Recent Zinc public snapshot is optional and time-labelled.
- Zinc 10:30 weekdays: unchanged.
- Global Evening 17:30 daily: new items since the *completed* morning issue, no automatic rebroadcast. If morning baseline missing, `has_morning_comparison=false`, hold “delta edition” claim.
- Zinc 17:30 weekdays: independent, unchanged; new Global Evening never assumes concurrently executing Zinc alert has completed.

## New pipeline boundaries

```
FreeNewsApi.io / GDELT / official RSS
    ↓ article candidates with published / retrieved timestamps
Canonical event grouping / ranking / classification
    ↓ source_id + excerpts (ATTRIBUTED_UNVERIFIED by default)
Canonical issue.json (same exact facts for 2 editions)
    ↓ Gemini optional first editorial draft, then revision (2 calls maximum)
AI review checks: known event_id/source_id; reject introduced numeric claims/URLs
    ↓ manual/primary-source fact verification; label status and location
Layout 01 native XHTML  → BOOX colour EPUB 3 + HTML
    ↓ 10-trading-day real-source and real-device acceptance
Only THEN turn on automated schedule, publication and LINE
```

The Gemini step is **not connected to Gemini's web subscription**. Use an eligible **free** Google AI Studio API project and a restricted `GEMINI_API_KEY` stored in the new repo's Secrets. `ENABLE_GEMINI=1` and `GEMINI_FREE_TIER_CONFIRMED=1` are explicit opt-in flags; no paid fallback exists. Google free-model limits are model-/project-specific, and free-tier processing may have different data-use terms. **Never send Zinc inventory, personal holdings or procurement state to the model.**

## What is implemented in V1.6

- `gib/newsroom_v16.py`: candidate sources, stable IDs, dates, event ranking, simple duplicate detection, evening comparison, claim provenance and publication gates.
- `gib/gemini_editor_v16.py`: explicit free Gemini key opt-in; **two calls** (draft then revision), `event_id`/`source_id` checking, rejecting new URLs/numeric claims; all AI explanations remain unverified opinions pending editorial review.
- `gib/publish_v16.py`: compact world-at-a-glance, lead-story hierarchy, research/uncertainty panels, source footnotes and XHTML→EPUB 3; no Markdown-to-book shortcut.
- `run_newsroom_v16.py`: single QA pipeline from real sources or offline fixture, producing two versions from same issue. No push, publishing or scheduling side effects.
- `tests/test_v16_newsroom.py`: guarded publication, audit, evening de-dup, Gemini opt-in and EPUB smoke tests.

## What is deliberately **not** claimed to be finished

1. A full claim-by-claim **external truth check**: the current automated check validates citation *identity*, excerpt availability and easy numeric fabrication; it does **not** prove that a media snippet supports a deep economic inference. Thus every collected item starts as `ATTRIBUTED_UNVERIFIED` and cannot become `VERIFIED` automatically.
2. Complete 2–3 deep stories from arbitrary daily news: a short article headline cannot support a 30–45 minute research edition. The output states when adequate sources are missing, and its release gate stays closed.
3. Live API testing: needs user-owned FreeNewsApi.io key and a Gemini API free-project key for editor tests. No secret should be posted in a chat or committed to a repo.
4. The Economist article 2026-10-23: direct full content was restricted. Only documented editorial structure, not copyrighted content, informs design.
5. BOOX NeoReader hands-on, EPUBCheck and ten trading days of live evaluations remain separate acceptance steps.
6. Direct repo creation, secret configuration, and schedule activation cannot be performed without an appropriate GitHub admin/secret tool and user-supplied credentials configured privately.

## Publication acceptance gates

- 8–12 fresh, unique relevant news items (only when real-world news supports that count); with four+ independent publisher domains.
- At least 3 top stories with **source-location-verified** supporting facts; AI cannot promote a snippet to VERIFIED.
- Deep requires 2 evidence-rich essays, substantive counterevidence, economic mechanism, history and watch conditions. Do not pad.
- Evening comparison requires original morning issue snapshot and identification of **materially new facts**, not just renamed syndicated articles.
- Zero invented headlines, numerical values, quotes, source links or causal explanations presented as facts.
- EPUBCheck, sourced charts if available, readable NeoReader longform at ordinary and enlarged font settings, link and provenance QA.
- Ten trading-day live test with human newsroom review; until then workflow manual-only, LINE/Pages off.

## Setup and test

1. Create new `global-intelligence-brief` repo. Upload this bundle unchanged, do not copy it into Zinc repo.
2. In FreeNewsApi.io get the free key; configure in **this** repo only: `FREENEWS_API_KEY` GitHub Secret. FreeNewsApi title search is `in_title` (not `q` or full body text).
3. Optional Gemini: in Google AI Studio choose supported free-model project, generate restricted Gemini API key; configure `GEMINI_API_KEY` Secret, `GEMINI_FREE_TIER_CONFIRMED=1` variable, `GEMINI_MODEL` variable, manually trigger QA with Gemini enabled. API limits and model availability may change.
4. Manual Actions: `Global Intelligence V1.6 - integrated newsroom QA`, first run `sample`, then `live` morning; inspect source health, lack of false claims and article ranking.
5. For evening QA, provide the completed morning issue JSON (`--morning-issue`), not an arbitrary previous run. The workflow input currently tests standalone evening candidate gathering only; it is **not** production-grade delta scheduling.
6. Run `python -m unittest discover -s tests -v`; review EPUB in BOOX NeoReader; only then consider separate production release controls.

### Local

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_newsroom_v16.py --edition morning --fixture samples/historical_articles_v16.json --as-of 2026-10-15T09:00:00+00:00
# Real-source QA (internet/key access required):
python run_newsroom_v16.py --edition morning
# After free-tier/project confirmed and key configured in environment:
ENABLE_GEMINI=1 GEMINI_FREE_TIER_CONFIRMED=1 python run_newsroom_v16.py --edition morning --gemini
```

The offline historical fixture intentionally has only **three** usable stories. It must fail publication quality gates. This is an anti-misrepresentation test, not a satisfactory sample edition.
