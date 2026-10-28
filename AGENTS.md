# GIB Project Operating Rules — editorial and QA release gates

These rules are binding for all GIB changes and reviews.

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

A source gate passes only on real public RSS items: valid title, original URL, timezone-aware timestamp, bounded freshness and adequate coverage. If the gate is partial, preserve the status/artifact and identify missing source groups. Do not use synthetic data to satisfy coverage. Do not auto publish. The uploaded OPML preserves the user's folder assignment, but folder name does not prove relevance: Taiwan policy and zinc/steel/HDG coverage are currently research gaps.

## 6. Secret-access reality
Repository code, GitHub API and CI logs cannot expose the four private Secret **values**. A safe CI probe can test their shape and live feed responses when running in the main-branch GitHub Actions context. When reviewing the retired Pro-only path, note that GitHub never reveals Secret values. It is not needed for the accepted free OPML integration. Never ask the owner to paste account passwords, private export URLs or token-bearing links into chat.
