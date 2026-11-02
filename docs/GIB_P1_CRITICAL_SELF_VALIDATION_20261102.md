# GIB P1 critical self-validation — 2026-11-02

## Scope and hard boundary
- **Frozen main contract:** `2026-10-29-owner-approved-v3`. No production/main, Style C, schedule, LINE, expense, or release control modifications.
- This document reports a **QA-only** attempt; it does not authorize publication or imply product readiness.
- P2 A–D chart *execution* is forbidden until complete P1 PASS. Chart source specifications are already recorded in `qa/visual_p1/assets_manifest.json`.

## Iterative fixes performed
1. First run **41367710482** — Commons CDN returned HTTP 429. Acquisition blocked without guessing that external URLs were offline files.
2. Replaced background-photo providers with **official DVIDS public-domain photograph** and **two Unsplash free (not Unsplash+) photographs**. Their own source/rights pages, authors, dates and editorial limitations remain in the manifest.
3. Run **41371035679** — photos partly acquired; strict non-event caption test flagged one appropriately contextual but differently worded caption. The literal test, not the rights policy, was corrected.
4. Run **41371271634** — all **three real photo files downloaded**; original checksum, resizing, 3 color and 3 grayscale derivatives generated, provenance JSON and HTML license index uploaded to artifact **13108588959**. The run intentionally exited nonzero on the remaining **cover-photo gate**. GitHub Actions failure is therefore **editorial gate HOLD**, not a failure to download photos.
5. Push-triggered retry removed from QA photo workflow; now only manual QA dispatch, with all production jobs unaffected.

## Independently reproduced local artifact QA
Artifact: https://github.com/ala927832-create/global-intelligence-brief/actions/runs/41371271634/artifacts/13108588959

| Photo | Source/date/rights | Offline RGB | Offline grayscale | Optimized SHA256 verified |
|---|---|---|---|---|
| Energy logistics archive | DVIDS / 2009-09-10 / US government public domain | 1000×670 | 1000×670 | yes |
| ECB building archive | Unsplash, Markus Spiske / 2021-01-10 / Unsplash free license | 853×1280 | 853×1280 | yes |
| Data center archive | Unsplash, Kevin Ache / 2023-09-25 / Unsplash free license | 1280×853 | 1280×853 | yes |

- **3/3** original bytes obtained with source SHA-256, file sizes, creator identity, date and attribution.
- **3/3** color and **3/3** grayscale derivatives exist, verified opening with PIL.
- **3/3** sha256 optimized hashes reproduced from uploaded artifact.
- Caption warns **not the 2026-10-30 incident or meeting**. The photographs do not provide evidence of any attack or particular technology company investment.
- The license gallery is offline HTML with relative image references and credits, QA only, not the frozen production reader.
- No 3:4 original cover image of the actual top news incident has been licensed and obtained. Image archive relevance ≠ contemporaneous incident-photo provenance.
- No BOOX physical-device acceptance or full issue EPUB asset embed validation has happened.

## Critical gate verdict
| Gate | State |
|---|---|
| Real original media | PASS, 3/3 |
| Rights metadata & source | PASS, 3/3 |
| Source hashing and offline resized color/gray photos | PASS, 3/3 |
| Caption fidelity and clear historic framing | PASS, 3/3 |
| **Current-event main-news licensed cover** | **HOLD** |
| Issue-level offline EPUB/BOOX acceptance | **HOLD** |
| **P1 overall** | **HOLD** |
| **P2 actual A/B/C/D figures generated** | **NOT STARTED; blocked by P1 policy** |
| Publishing, LINE, main branch | **OFF / unchanged** |

**Do not silently substitute a historic documentary photo for an incident photo or reclassify P1 to PASS merely to activate P2.** The remaining work must obtain a credible, rights-cleared cover matching the leading report and then run actual issue-level HTML/EPUB and BOOX checks. If such a photo cannot be licensed under frozen rules, the gate stays HOLD; no false readiness or automatic P2 progression.

## Evidence
- Run 41371271634 uploaded asset ZIP, IDs and SHA files: `qa_out/p1_visual/provenance.json`.
- QA files: `qa/visual_p1/assets_manifest.json`, `qa/visual_p1/prepare_assets.py`.
- Existing original editorial content and Style C were never altered by this P1 photo QA.
