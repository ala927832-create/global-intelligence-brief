# Global Intelligence Brief — consolidated execution contract

## Scope lock

This is NOT Zinc Intelligence V2.8, is not a market-trading dashboard, and does not inherit Zinc rankings. There is exactly one independent `global-intelligence-brief` repository, one ingest+editorial pipeline, two daily news editions, and an optional strictly read-only public Zinc Research Watch.

## Four fixed Taiwan schedules

| Schedule | App | Output | Inter-system input |
|---|---|---|---|
| 07:30 DAILY | Global Intelligence | Morning essential/deep | Latest previously completed *public* Zinc snapshot, dated explicitly |
| 10:30 WEEKDAYS | Zinc Intelligence | Market research | None from this project |
| 17:30 WEEKDAYS | Zinc Intelligence | Conditional market alert | None from this project |
| 17:30 DAILY | Global Intelligence | Evening essential/deep, material new evidence | Latest completed Zinc snapshot; does **not** await concurrent 17:30 Zinc alert |

GitHub Actions scheduling is best effort and may start late. Timestamp actual report generation. Independent jobs and repositories mean parallel triggering is intentional; notifications carry unambiguous labels to avoid conflation. Zinc runs retain original 10:30 and 17:30 settings and are not modified.

## One consolidated run, not fragmented agents

```
Collection (FreeNewsApi / RSS / GDELT)
 -> Canonical evidence / timestamps / URL cleanup
 -> Event dedup / topic diversification / importance ranking
 -> Morning-vs-evening incremental check (evening only)
 -> Optional latest public Zinc Research Watch (strict field allowlist)
 -> Optional explicitly-free Gemini commentary (one bounded request)
 -> Shared source-backed editorial packet (only after verifiable primary evidence)
 -> Structured XHTML -> Essential HTML+EPUB
 -> Structured XHTML -> Deep HTML+EPUB (strict evidence and length gate)
 -> Archive / LINE only after formal release approval
```

The same evidence and AI research packet is used for Essential and Deep editions. No second market price feed, no additional TradingView API, no new n8n service, and no hidden paid fallback.

## Editor's contract

- **Morning:** what happened overnight? what matters today? what primary document confirms it? what to watch?
- **Evening:** what's new since the morning? what new evidence changes earlier understanding? what's coming next? do not resend the morning article list.
- **No narrative inflation:** Inadequate source material -> shorter deep edition with conspicuous evidence limit; 30–45 min is an editorial target, not a fabricated time claim.
- **Cross-market bridge:** A technical Zinc state is labelled "research only", never placed as a verified global news item or trade signal. Only the two most relevant non-neutral observations are shown; their date must be printed.
- **Economic causal claims:** A news title is not evidence that an event caused a price change. No derivative trade instructions.
- **Provenance:** Every item has a date if available and link to the publisher. Unconfirmed details remain attributed or explicitly unknown.
- **No source-body publication:** Never republish licensed full text or save secrets/private procurement metadata.

## Operational gates before enabling unattended distribution

1. Verify actual FreeNewsApi.io response fields, 401, 429, and quotas with a personally obtained free API key. Its `/news` search is `in_title` only.
2. Check at least 10 days of real-source coverage across official RSS, FreeNews and GDELT; manually review event clustering and false duplicates.
3. Verify public Zinc bridge never includes `procurement`, personal holdings, inventory or token data, including archive, logs and AI input.
4. Confirm morning and evening are distinct; if 07:30 failed, evening must say it cannot compare reliably.
5. Set Gemini `ENABLE_GEMINI=1` ONLY if the specific Google project is confirmed **free without billing**; run outputs through source/reference check before automatic publication.
6. Confirm HTML, EPUB, link and publication timestamp integrity. No invented headline, quote, number or source.
7. If using LINE, confirm free combined quota and recipient, and prevent manual test runs from sending.

## Limitations of this first complete starter

- It contains source-backed offline editorial sample tests and a MANUAL-ONLY QA workflow. **The new independent morning/evening schedules are reserved but NOT enabled; live API and editorial accuracy remain unvalidated.**
- Event similarity is heuristic (titles and publisher URLs) and is not an entity/semantic event database.
- Detailed background evidence/long-form financial learning and the 30–45 minute reading target require richer primary documents and editorial review, not simply more AI tokens.
- Source RSS endpoints and free-tier availability can change. Do not represent availability or compliance as guaranteed.
- Creating the new repository and configuring keys/Pages is a one-time manual action because the linked GitHub connector has no repository creation or secret-write endpoint.

## BOOX colour EPUB design lock (2026-10-23)

- PRODUCTION TARGET ONLY: four distinct EPUB 3 outputs/day (morning/evening × essential/deep). CURRENT QA SAMPLE: morning essential and deep only; no fake evening delta.
- Device target: BOOX Note Air4 C, 10.3-inch Kaleido 3, 150ppi color / 300ppi black-and-white. White background, graphite text, selective blue/teal/amber accents, grayscale redundant structural emphasis, no full-page colored fill.
- Reflowable body, no embedded proprietary fonts, size in `em`, EPUB 3 NAV, natural section flow without forced H2 page breaks, user-adjustable typesetting in NeoReader. Cover uses illustration-free design and bundled PNG. Do not turn long-form text into an image.
- HTML preview and BOOX EPUB download link coexist; optional LINE sends direct EPUB URLs after checks. Zinc workflows and timing remain unchanged.
- Validate with structural checks in CI and real NeoReader device before declaring device-certified. EPUBCheck is recommended final external validation.


## Layout 01 design decision

The approved editorial direction uses the 3:4 illustration as a visual reference,
with magazine masthead, four topic tiles, navy headlines, warm ivory paper tone,
restrained teal and amber, and evidence-aware reading cards. Actual EPUB content
is reflowable with substantive evidence cards, inline sourced charts, and no fixed two-column sidebar or unverified quote.
