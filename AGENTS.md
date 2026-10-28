# GIB Project Operating Rules — editorial and QA release gates

These rules are binding for all GIB changes and reviews.

## 0. Non-negotiable original editorial charter (2026-10-23-approved-v1)

**Authoritative owner-approved specification:** `config/frozen_contract.json`. This governs GLOBAL INTELLIGENCE BRIEF; no later assistant-created source list, ranking priority, vertical watchlist or OPML folder label may override it.

**Publication mission:** a global affairs and economic intelligence newspaper, drawing only the **editorial hierarchy principles** (not copyrighted text/layout) of WSJ and the analytical rigor of The Economist. Answer **what happened worldwide, why it matters, what changes, and what to watch**. International significance, cross-border spillovers and verified novelty govern the lead story—not the owner's manufacturing, zinc procurement, or Taiwan regulatory interests.

**Owner-approved six sections, in order:**
1. `Executive Brief` — 3 genuinely most important global developments.
2. `The World in Brief` — 8–12 selected globally relevant developments, adjusted to verified material.
3. `Essential Analysis` — 3–5 major events with mechanisms, context, evidence.
4. `Deep Research` — only deep edition, 2–3 evidence-rich studies with history, competing perspectives and falsification criteria.
5. `What Changed & What to Watch` — factual differences, coming week's catalysts, optional concise **public verified** Zinc Research Watch.
6. `Sources & Evidence` — dated primary links, observation periods, data limitations and unverified claims.

**Two editions:** Essential 10–15 minutes and Deep Research 30–45 minutes; rigorous substance rather than padding. Morning 07:30 Taipei; evening 17:30 Taipei, covering actual new developments since the completed morning (no duplicate syndication). Frozen Style C news home/article and BOOX reading hierarchy; do not redesign. Editorial facts and analysis remain separately labelled. Two-stage Gemini draft/check where free-tier enabled, explicit numeric/date/quote verification and human review before release. No paid fallback, schedule activation or auto-publication before approved QA gates.

**Zinc Intelligence remains a separate repository** and its 10:30 and 17:30 schedules stay untouched. Zinc, steel, HDG, Taiwan subsidies, wastewater and plant-specific procurement/engineering topics are **optional specialist source references**, never a default lead section or front-page quota. Promote such an item **only when its independently evidenced international/public importance warrants selection**, on the same terms as any other topic. Never substitute the owner's unrelated plant projects for the GIB editorial agenda.

**Source groups are NOT editorial desks or importance weights.** The 24 public RSS subscriptions from the user OPML are source intake only; preserve the four folder labels as provenance, not guaranteed coverage or quotas. Any additional government/industry feeds belong in the optional `config/specialist_official_references.json` reference library unless separately approved as daily candidates. The specialist library's former P0/P1 fields were assistant-invented and have been removed. **Do not change `config/frozen_contract.json` without explicit owner approval.**

## 0A. Owner-approved integrated delivery and change-control v1 (2026-10-28)

The owner explicitly approved **GIB integrated plan v1** on 2026-10-28, scoped to writing these implementation rules, combining existing P1 public RSS intake with the existing V1.6 newsroom and frozen Style C in a **single P2 QA-only pipeline**, and performing our own offline/real-source/editorial/evidence tests before submitting **one consolidated acceptance report**. This authorizes implementation/refactoring and nonpublishing QA in that scope only. It does **not** authorize changing the frozen editorial contract, adding new product/subject priorities, paid APIs, long-running schedules, public Pages, LINE alerts, production EPUB distribution or declaring editorial facts verified.

1. **Original contract is immutable without separate owner consent.** Preserve the six approved global-news sections, Essential 10–15 and Deep Research 30–45 intent, 07:30/17:30 timing target (not enabled), original Style C hierarchy, editorial rigor, separate Zinc repository, and explicit OFF publication gate. Before any modification *outside* this approved work scope, obtain affirmative owner approval.
2. **One shared, provenance-rich canonical issue.** Join the validated 24 original OPML RSS feeds and optional existing free public sources into the existing newsroom pipeline; never create a third rival editorial product. Both Essential/Deep and Style C internal QA must derive from the same issue and event/source IDs. Keep original source URL, UTC timestamp, OPML group and retrieval/verification status; tag news-index extracts as unverified.
3. **Meaningful editorial gate.** Rank by independently justified global newsworthiness, never by folder names, user's industry, popularity or raw feed counts. Top three, 8–12 world briefs, 3–5 substantive analyses and 2–3 evidence-rich deep studies are *quality targets*, not commands to invent or pad content. Distinguish source claim, independently checked fact, mechanism, counterargument, uncertainty and watch/invalidation conditions. Failure remains a visible HOLD.
4. **Real morning → evening comparison.** Evening must consume a *completed same-day morning source snapshot*, show only demonstrably new facts, corrections or independently relevant developments and never claim a true delta based on title or a newly syndicated URL alone. Missing morning snapshot means no qualified evening delta.
5. **Self-test before owner handoff.** Within a single integrated milestone, run reproducible fixtures + GitHub CI + available real publisher feed QA + permitted model/API QA + link and offline formatting QA. Collect run IDs, artifacts, failures and factual limitations. Do not ask the owner to repeatedly press Run; fix failures within approved scope. Mock/green CI ≠ journalist-verified claims ≠ BOOX real-device signoff.
6. **One report and minimal user actions.** Deliver a consolidated acceptance table, exact tested revision/run, sample Essential/Deep and morning/evening output locations, unresolved blockers, and *at most one truly necessary owner action*. P3 BOOX/human test and ten real trading days (20 editions) follow only after P2 acceptance; external publication remains owner-locked.
7. **Scope change requires permission first.** If a change affects subject priorities, frozen contract, costs/keys, audience, output design, future delivery, connected accounts or release settings, stop and present the proposed difference for owner approval. PRs and change logs must make all deviations reviewable.

## 1. One integrated milestone, no fragmented user testing
Do not repeatedly ask the owner to run GitHub Actions after small changes. Diagnose reported failure from the **actual job logs** first. Fix identified code issues and run both fixture tests and available real GitHub Actions checks **ourselves**, then report evidence. The owner performs one consolidated configuration action only when GitHub Secrets or connected account privileges make it unavoidable.

Never claim "tested and ready" merely because static tests pass. A simulator passing is not genuine Inoreader ingestion.

## 2. Evidence-first gates
For the FREE OPML-based P1: (a) confirm the uploaded OPML's original publisher RSS URLs and their four folder assignments, (b) GitHub directly retrieves public publisher RSS/Atom XML without Inoreader Pro Output Feed Secrets, (c) confirm genuine original article links and timezone-aware publication timestamps, (d) preserve source names, source IDs, group attribution, feed health and deduplication, (e) report source/group coverage gaps and failed feeds transparently. The optional old Pro-only export workflow remains available only as a separate legacy path and is not a prerequisite. If any gate fails, mark P1 **BLOCKED**, name the cause and do not direct the owner into the next phase.

A missing original URL, timestamp or an empty feed is a reportable defect; never invent news or record a mocked article as real. Export URLs and access tokens stay in GitHub Secrets, never in logs, artifacts, code or chat.

**Important:** XML/JSON syntax validity, HTTP 200 and a publication timestamp are **not sufficient**. Inoreader may respond with a syntactically valid RSS item titled "Feed suspended!" containing a Pro-plan requirement. Treat such a response as `INOREADER_EXPORT_SUSPENDED_PRO_PLAN_REQUIRED`, never count it as news or let the P1 gate pass. If the user's paid plan appears active, verify the exact account/subscription and ask Inoreader support rather than guessing, upgrading twice or circumventing export restrictions.

## 3. Frozen release order
P1 Inoreader sources → P2 independently verified AI editorial + frozen Style C HTML → P3 genuine BOOX hardware/human long-read and 10-trading-day / 20-edition acceptance.

Do not change the frozen Style C design, add new paid agents, build additional scrapers, publish EPUB, enable scheduled news delivery/LINE/Pages, or claim editorial approval while P1 is blocked.

## 4. Operational reporting
Report milestones, not each trivial implementation commit. A finished response states: **what was checked**, **actual run ID**, **what passed**, **what is still blocked**, and **the single next action, if truly required**. No repeated request for the same manual QA.

## 5. Free-Inoreader subscription boundary

The user confirmed the Inoreader plan is FREE, and its Output RSS showed `Feed suspended! Pro plan is required`. Therefore **never request four Inoreader Output RSS/JSON URLs or repeat Pro-only manual tests**. The user supplied a valid OPML file (2026-10-28) containing 24 distinct public source URLs in four folders. P1 must use `config/inoreader_free_feeds.json` and `qa/opml_free_p1.py` to fetch them directly with no credentials. OPML is subscription metadata: it cannot synchronize the user's read state, favorite flags, Inoreader rule selection or current folder stream. Make no promises that it does.

A source gate passes only on real public RSS items: valid title, original URL, timezone-aware timestamp, bounded freshness and adequate coverage. If the gate is partial, preserve the status/artifact and identify missing source groups. Do not use synthetic data to satisfy coverage. Do not auto publish. The uploaded OPML preserves the user's source folder assignment only. Taiwan policy and zinc/steel/HDG information can be research references; they are not automatic editorial coverage gaps that must be filled at the expense of globally important news.

## 6. Secret-access reality
Repository code, GitHub API and CI logs cannot expose the four private Secret **values**. A safe CI probe can test their shape and live feed responses when running in the main-branch GitHub Actions context. When reviewing the retired Pro-only path, note that GitHub never reveals Secret values. It is not needed for the accepted free OPML integration. Never ask the owner to paste account passwords, private export URLs or token-bearing links into chat.
