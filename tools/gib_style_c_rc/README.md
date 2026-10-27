# GIB Style C — HTML-first QA integration (2026-10-27)

This is a **manual QA-only** newsroom adapter that works with the existing `gib.collect` and `gib.newsroom_v16` canonical evidence objects. It does not enable GitHub Pages, EPUB, LINE, Gemini, paid APIs or automatic publishing.

## Strict content / timing controls

- Morning news window: **previous calendar day 17:00 → current day 07:00**, Asia/Taipei; designed for a 07:30 QA delivery.
- Evening news window: **current day 07:00 → 17:00**, Asia/Taipei; designed for a 17:30 QA delivery.
- Actual `capture_started_utc` and `capture_finished_utc` are recorded. Running late or early is **not** proof of a successful scheduled issue; result remains HOLD.
- Evening requires an actual **same-date** morning artifact (provide morning workflow run ID when manually dispatching). Never compare against the 2026-10-24 historical fixture.
- The collector's syndication clustering and `event_id` are reused. Evening outputs flag new reported items or new-source signals; **a new source alone does not prove a material factual update**.
- Indexed article titles and snippets are **attributed, not verified**. No invented facts, reconstructed paid articles or synthesized quotes.
- Eight-desk coverage counts show missing areas; they are **not** a recall score against independent sources.

## Build-time offline photographs

Three previously selected historical Wikimedia Commons image references are attempted by the GitHub runner. Only successfully downloaded and Pillow-verified JPEG/PNG/WebP content is embedded as a `data:image` payload. The report includes original/embedded SHA-256 and a source/attribution record. Missing photos remain missing, not decorated or inferred. Context photos must not be described as imagery from the reported event. Image licensing and appropriateness need independent human signoff.

## Artefacts from manual Actions run

`morning.html` or `evening.html`, `issue.json`, `source_packet.json`, `qa_report.json`. Browser links to original reporting require connectivity. A generated HTML is not a published issue.

## Acceptance gates

1. Real source-fetch logs, correct cutoff and edition window.
2. Independent global-news coverage audit and material-event delta review.
3. Claim-level editor verification with recorded original sources.
4. Photo attribution and image embedding checked offline in a browser.
5. Desktop / mobile / **BOOX Note Air4 C colour** real device and real-reader testing.
6. Owner approval to start (not claim completion of) 10 trading days of morning/evening QA.
7. Ten trading days with **20 independently recorded runs**, no prefilled PASS.
8. Formal publishing, EPUB and LINE require a separate explicit go-live decision.

## Status

**SOURCE QA INTEGRATION CANDIDATE · RELEASE HOLD.** Existing `.github/workflows/morning_evening.yml` is untouched. Existing `ten_day_live_qa.yml` is untouched and must not be armed by this integration.

This folder is intentionally isolated from `zinc-intelligence-v26`.

## Consolidated editorial/offline gate (2026-10-27)
**Do not create another design version.** Frozen Style C remains the layout contract. This PR adds a single operational QA gate:
- Select source candidates **inside the edition cutoff window before ranking**, so older high-scoring headlines cannot use up the 16-story quota.
- A lead photograph is displayed only when its documented *historical context subject* matches the story's desk; otherwise a clearly labelled photo-unavailable treatment appears.
- Use the provider-attributed news snippet where it exists, never generic fabricated article copy. All feed excerpts remain **unverified until claim-level human review**.
- GitHub PR/Manual integration QA downloads three Commons photographs (only original licensed image bytes, no AI imagery), verifies them through Pillow, embeds them in a colour/BOOX-friendly standalone HTML proof and records SHA-256, licence and source.
- The **photo proof does not certify** the entire publication: independent global-news completeness, licensed newsroom reporting and BOOX *real-device timed reading* remain release blockers.
- The new integration workflow never publishes, schedules a daily issue, calls Gemini, accesses Zinc, generates an EPUB or sends LINE. A red photo gate is an actionable HOLD, not a faux PASS.
