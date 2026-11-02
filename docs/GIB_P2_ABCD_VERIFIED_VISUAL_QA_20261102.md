# GIB P2 A–D final sourced chart and offline QA — 2026-11-02

## Boundary and verdict

- Frozen main contract remains `2026-10-29-owner-approved-v3`. No changes to original approved text, Style C/Layout 01, main, scheduled news collection, fees, LINE, or publication.
- **P1 visual proof previously completed**: NASA 2021 geography context photo, ECB background, data-center background, each attributed and identified as archival, not the contemporaneous incident.
- **P2 four charts completed and technically validated**, A/B/C/D; color and grayscale PNG for each; physically embedded into **Essential and Deep** offline HTML and EPUB3 (4 charts + 3 licensed photos each).
- Internal deterministic QA 47/47 pass; originals text nodes identical versus P1. Source links, image files, chart identifiers, EPUB ZIP CRC, EPUB mimetype+OPF+XHTML passed.
- **Not final device or publication PASS**. Chromium denied both file and localhost HTTP (`ERR_BLOCKED_BY_ADMINISTRATOR`), therefore no browser-render QA pass is claimed; real BOOX device and formal EPUBCheck tool not available. Final user/editorial signoff and release are OFF.

## Figures and exact numeric ground truth

| Figure | Dated data | Official provenance and required qualification |
|---|---|---|
| A — Hormuz | EIA **20.9, 21.0, 21.3, 21.6, 14.9, 4.9** million barrels/day, 2025 Q1–2026 Q2 | [EIA 2026-08-12](https://www.eia.gov/outlooks/steo/report/energysecurity/article.php), Table 2 or 4. Historical quarterly average, not October 30 incident flow or real-time ship positions. NASA 2021-03-24 photo is geographic context, not event photo. |
| B — Brent / WTI spot | 19 common daily dates, **2026-10-01 through 2026-10-27**. Brent 123.10, WTI 103.37 USD/bbl on Oct 27 | [EIA Brent XLS](https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls) SHA256 `c7c1e1eeb321fa5982f74747886963b35bd2df3c2f63960271c353421d5830ca`; [EIA WTI XLS](https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls) SHA256 `1f4c7c6c80c4ef6eb9e7b6c95e87c8df6439e3fb6ecccea72e9135bb37acf048`. Do not label as Oct 29 futures settlement. |
| C — Fed / ECB / BOJ | Fed target range **3.75–4.00% (Oct 28)**; ECB deposit facility **2.50% (Oct 29)**; BOJ uncollateralized overnight call guideline **1.25% (Oct 30)** | [Fed decision](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm), [ECB decision](https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp261029~9a493adf17.en.html), [BOJ homepage policy guideline](https://www.boj.or.jp/en/). Different rate definitions are explicitly labelled and must not be interchanged. |
| D — cash capex | Calendar Jul–Sep 2026, USD billion: **Amazon 77.259, Alphabet 51.355, Microsoft 39.367, Meta 33.942** | [Amazon IR](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/default.aspx), [Alphabet SEC 8-K](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000080/googexhibit991q32026.htm), [Microsoft SEC 10-Q](https://www.sec.gov/Archives/edgar/data/789019/000119312526436133/msft-20260930.htm), [Meta IR](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/default.aspx). **Total cash property/equipment purchases, not all AI-specific investment.** Microsoft FY27 Q1 equals same calendar quarter. |

## QA completion

- Four full-color and four grayscale chart images with CJK text readable at source resolution; checked manually as individual charts and combined contact sheet.
- Original 24-news issue and commentary text unchanged (HTML text stripped of chart figures exactly matches source issue; EPUB original XHTML text invariant after removing chart figures).
- Each edition self-contained in ZIP under root HTML / `charts/` / `assets/`; separate EPUB3 embeds seven real images.
- QA package includes sources-and-limitations Markdown, plotted numeric JSON, original EIA dated series + XLS hashes, source scripts, and deterministic QA output.
- **No fake external published result**; GitHub chart QA run for EIA source [#41373149788](https://github.com/ala927832-create/global-intelligence-brief/actions/runs/41373149788), full offline QA authored locally to package without changing production branch.

## Remaining release gates

1. Real-device BOOX NeoReader image enlargement, legibility in 150 ppi color/300 ppi monochrome, page-turning, and offline links.
2. Browser desktop/tablet/mobile actual render QA in a permitted environment; the current tool could not test Chromium.
3. Formal EPUBCheck execution and owner-approved release workflow.
4. Other frozen V3 P2/P3 editorial-quality and trial-day gates remain fully in force; P2 *visual* technical pass is not a release decision.

**Status:** P2 A/B/C/D data-visual source+offline package = QA TECHNICAL PASS; **formal issue release remains HOLD/OFF**.
