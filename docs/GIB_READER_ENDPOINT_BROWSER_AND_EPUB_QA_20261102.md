# GIB Reading Endpoint QA — 2026-11-02

**Scope:** Follow up P1+P2 visual assets (A–D) without altering approved publisher content, Style C/Layout 01, the frozen contract, schedules, pricing, LINE or publication switches. **Publishing remains OFF.**

## Chromium browser QA — verified in current session
- Previous `page.goto(file:// / localhost)` was blocked (`ERR_BLOCKED_BY_ADMINISTRATOR`). This is not a rendering pass.
- Workaround: `page.set_content` of full final HTML, replacing the seven local image URLs in-memory with equivalent data URIs. Chromium actually laid out the DOM/images, not a static regex check.
- **12/12 actual Chromium render combinations pass:** Deep + Essential, 1440px desktop + 768px tablet + 390px mobile, color + grayscale. Zero horizontal overflow; seven images decoded in each; zero dead HTML anchors; Deep 30 articles including six studies, Essential 24.
- **Actual visual problem discovered:** original wide charts shrunk to 390px cause tiny axis and footnote text. Do not count original mobile readability as professional PASS.
- Correction: create four portrait-readable mobile chart variants using exactly the original accepted A–D data and four grayscale equivalents. QA-only responsive HTML uses `<picture><source media="(max-width:600px)">`; full-width chart images and frozen CSS remain intact. After correction, **12/12** Chromium combinations pass. Source article text is byte-wise normalized unchanged. Desktop still receives full-size original charts.
- Mobile-source fallback selection verified via naturalWidth 700 in the browser on all four chart figures. Reviewed screenshots include four color + four gray excerpts.
- The 700px mobile images are **NOT YET EMBEDDED IN EPUB**; do not claim BOOX benefits without testing the actual reader.

## Actual EPUB3 navigation defect repaired — QA-only EPUBs
- Original deep EPUB included **20 broken internal target anchors**. Original Essential EPUB included **2**. Ordinary ZIP/manifest tests missed them.
- Fixed **only** by matching titles back to approved HTML and inserting empty XHTML `span id` aliases into the existing EPUB heading. Source text, CSS, chart bytes, OPF, chapter order unchanged.
- Both patched files saved **with new QA names**, not overwriting original EPUBs.
- Custom strict validator: **19/19** each (38/38 total), including EPUB ZIP CRC and mimetype-first, OPF/spine/manifest/nav, XHTML parsing, seven image assets matching source bytes, alt text, full internal/cross-chapter anchor resolution.
- This does **NOT** replace official W3C EPUBCheck. Current official production release is EPUBCheck **v5.4.0** (2026-09-15). Binary was unavailable to download in current runtime, so `EPUBCHECK_PASS` is still **HOLD**.

## Remaining signoffs
| Gate | Result |
|---|---|
| 12 renderer viewport combinations, responsive mobile charts, grayscale tests | PASS |
| QA HTML approved body text and original large figures preserved | PASS |
| New EPUB internal navigation and image/OPF integrity | PASS (custom validator only) |
| Official EPUBCheck 5.4.0 | HOLD |
| BOOX Note Air4 C physical NeoReader zoom, contrast, page turning, full offline operation | HOLD |
| Frozen contract, main, Style C, schedule, LINE, publication controls | UNCHANGED |
| Formal P3/P4 and release | OFF |

## Artifacts
The active conversation deliverable `GIB_Reader_Endpoint_QA_20261102.zip` includes:
- Deep / Essential responsive QA HTML, all source-colored/gray A–D chart assets, three documentary photographs, original numeric provenance and screenshot evidence;
- Deep / Essential QA EPUB navigation repairs;
- Browser test JSON, EPUB structural validation JSON, source vs repaired hashes, rebuild scripts, detailed README.

**Strict policy:** No false claim that a simulator is BOOX hardware. Do not publish or move to formal P3 just because simulated browser and EPUB metadata pass. This QA note only changes a file in the QA branch.
