# GIB Project Operating Rules — editorial and QA release gates

These rules are binding for all GIB changes and reviews.

## 1. One integrated milestone, no fragmented user testing
Do not repeatedly ask the owner to run GitHub Actions after small changes. Diagnose reported failure from the **actual job logs** first. Fix identified code issues and run both fixture tests and available real GitHub Actions checks **ourselves**, then report evidence. The owner performs one consolidated configuration action only when GitHub Secrets or connected account privileges make it unavoidable.

Never claim "tested and ready" merely because static tests pass. A simulator passing is not genuine Inoreader ingestion.

## 2. Evidence-first gates
For Inoreader P1: (a) four secret values exist, (b) each is a safely validated real Inoreader RSS/JSON Export URL, (c) GitHub Actions retrieves each live feed with real original publisher links and timestamps, (d) no lane silently falls back to FreeNewsApi/GDELT, (e) article count, rejected reasons and feed-hash provenance are reported. If any gate fails, mark P1 **BLOCKED**, name the cause and do not direct the owner into the next phase.

A missing original URL, timestamp or an empty feed is a reportable defect; never invent news or record a mocked article as real. Export URLs and access tokens stay in GitHub Secrets, never in logs, artifacts, code or chat.

**Important:** XML/JSON syntax validity, HTTP 200 and a publication timestamp are **not sufficient**. Inoreader may respond with a syntactically valid RSS item titled "Feed suspended!" containing a Pro-plan requirement. Treat such a response as `INOREADER_EXPORT_SUSPENDED_PRO_PLAN_REQUIRED`, never count it as news or let the P1 gate pass. If the user's paid plan appears active, verify the exact account/subscription and ask Inoreader support rather than guessing, upgrading twice or circumventing export restrictions.

## 3. Frozen release order
P1 Inoreader sources → P2 independently verified AI editorial + frozen Style C HTML → P3 genuine BOOX hardware/human long-read and 10-trading-day / 20-edition acceptance.

Do not change the frozen Style C design, add new paid agents, build additional scrapers, publish EPUB, enable scheduled news delivery/LINE/Pages, or claim editorial approval while P1 is blocked.

## 4. Operational reporting
Report milestones, not each trivial implementation commit. A finished response states: **what was checked**, **actual run ID**, **what passed**, **what is still blocked**, and **the single next action, if truly required**. No repeated request for the same manual QA.

## 5. Secret-access reality
Repository code, GitHub API and CI logs cannot expose the four private Secret **values**. A safe CI probe can test their shape and live feed responses when running in the main-branch GitHub Actions context. When all four stored values are placeholders or malformed, no code can manufacture valid private Export links: the owner must copy four real links once into Secrets. Do not ask the owner to reveal them in chat.
