# GIB V4 Style C visual restoration — expert QA 2026-11-02

## Ground truth and change policy
- Original frozen main contract: `2026-10-29-owner-approved-v3`, `Layout 01`, EPUB3 reflowable, BOOX Note Air4 C, 3:4 *ebook cover design ratio*.
- Original frozen QA reference CSS SHA: `1c283b5520f100893284945301da87039318d210`.
- No change to main branch, official CSS, report body, news claims, numeric charts, image provenance, fee, LINE, automations, or publication status. This work is **QA-only variants** and stand-alone local artifacts.

## Critical comparative visual audit
1. Original EPUB was only styled by a **316-byte** CSS; frozen Style C semantics were absent, so it displayed default book serif and the masthead lost all navy/teal hierarchy.
2. Original EPUB generated a redundant visible H1 above the real news title; two headings competed in the first screen.
3. Chapter navigation links in EPUB were crammed together and hard to tap.
4. Original HTML had an oversized full-bleed NASA figure, pushing the substantive brief below the first viewport. Optimized HTML retains the entire uncropped photo at a restrained 900px width, and reduces its mobile-first spacing.
5. Original HTML mobile navigation was compressed into inline text; now displayed in a 2-column touch-friendly layout.
6. Original EPUB used only four wide data figures; narrow reflow made data-label text hard to read. Updated EPUB displays the **four already verified 700px portrait chart variants** with retained original source PNGs. Figure A caption now clarifies that the NASA geography photo is on the cover.

## Implemented QA artifacts
- `GIB_Deep_HTML_StyleC_Standalone_QA.html`, `GIB_Essential_HTML_StyleC_Standalone_QA.html`: actual standalone files with embedded images and added QA-only style overrides. All original HTML body text retained exactly.
- `GIB_Deep_EPUB_StyleC_PortraitCharts_QA.epub`, `GIB_Essential_EPUB_StyleC_PortraitCharts_QA.epub`: exact same news and analysis text, plus 4 portrait chart assets, updated OPF, EPUB-aware richer Style C typography. One figure-only A caption clarification; original image bytes preserved.
- Screenshots generated from actual Chromium DOM CSS reflow. Prior screenshots and after screenshots allow review of the change without making imaginary design mockups.
- Reproducible build / render / EPUB chart upgrade / validation Python scripts and matching QA report included in chat download package.

## Tested
- **16/16 HTML+EPUB old/new combinations**, Deep/Essential; desktop 1440×900, mobile 390×844, EPUB preview 930×1240 & narrow 390×844, all with 7 original figures decoded, no horizontal overflow.
- **16/16 reflow portrait figures**: Deep/Essential × 4 A/B/C/D charts × (930,390), each decoded; verified source PNGs 700px and correct OPF references.
- Both EPUBs ZIP/OPF/XHTML/CRC validation passed; internal href anchors and all local image references have zero missing targets; 24 source-attributed news items, 4 data figures and 3 historical photos in each.
- Colors directly derived from frozen palette: dark masthead `#16324D`, page `#FAF8F2`, deep ink `#24333D`, teal `#285C6E`. Contrast checks: primary body ~12.24:1, secondary note ~5.92:1, masthead ~11.43:1.
- The cover-photo role remains archival NASA geographical illustration, not 2026 news-event photograph.

## Remaining formal gates
- **BOOX NeoReader physical acceptance still HOLD** (real pagination, zoom, color/greyscale, page turns).
- **Official EPUBCheck still HOLD**; local structural parsing is not the W3C tool.
- Frozen cover 3:4 design **not yet independently applied to a dedicated ebook-cover asset**. The landscape main news photo is not being relabeled as such.
- This is an editorial/visual QA improvement, NOT a full professional newsroom certification or permission to launch. P3/P4, LINE, main merge and formal publishing remain OFF.

**Result:** Visual/reader simulated QA PASS for the defects actually reproduced and corrected. Formal physical-device / publication signoff HOLD.
