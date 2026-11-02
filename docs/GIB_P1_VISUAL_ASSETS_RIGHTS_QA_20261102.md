# Global Intelligence Brief — P1 Licensed Visual Assets QA (2026-11-02)

## Immutable boundary
- Official main-branch frozen contract: `config/frozen_contract.json` version `2026-10-29-owner-approved-v3`. No main-branch edits.
- Editorial body, Style C/Layout 01 CSS, issue schedules, existing fees, LINE and all production publishing remain unchanged. No AI-generated newsroom photographs.
- Original Inoreader subscription authorizes the *news attribution*, **NOT reuse of a publisher photograph**.

## P1 execution results
1. **Rights & captions — PASS (3/3 sources reviewed)** in `qa/visual_p1/assets_manifest.json`.
2. **Photographic offline acquisition — HOLD**: QA GitHub Action [run 41367710482](https://github.com/ala927832-create/global-intelligence-brief/actions/runs/41367710482) failed with Wikimedia image CDN **HTTP 429**. No image files acquired, no SHA256 verified, no color/greyscale binary outputs, no EPUB image embedding validated. Do not label this complete.
3. Automatic push-triggered downloader retries disabled; any next download attempt must respect Wikimedia retry limits and their User-Agent policy. Existing source URL links are metadata only, **not offline assets**.
4. **Event-specific cover photo — HOLD**: no right-cleared image genuinely depicting the October 30 event has been established. The three current candidates are expressly historical/background documentary photographs. Do not pass them off as the current incident. The source-neutral photo alternative is not a legal or editorial exception.
5. **Chart source specification — PASS (A/B/C/D)**. Four charts selected; source methods recorded, **zero fake numerical charts generated**. Chart construction belongs to P2 after consistent time-window, definition and license tests.

## Approved historical/background image candidates (rights pages verified, files not acquired)
| Placement | Source / author / time | License | Editorial limitation |
|---|---|---|---|
| Energy logistics explanatory photo | [Oil Tanker ship](https://commons.wikimedia.org/wiki/File:Oil_Tanker_ship.jpg); Shipspotter Stahl; 2019-11-29 | CC BY-SA 4.0 | Generic tanker, place not confirmed; **not** Hormuz 2026 incident |
| ECB context photo | [ECB Skytower](https://commons.wikimedia.org/wiki/File:Frankfurt_am_Main,_Seat_of_the_European_Central_Bank_(Skytower_(ECB)).jpg); Dr. Thomas Liptak; 2026-09-06 | CC BY-SA 4.0 | ECB headquarters, **not** current rate meeting |
| AI capital expenditure infrastructure photo | [Datacenter Server Racks](https://commons.wikimedia.org/wiki/File:Datacenter_Server_Racks_(22370909788).jpg); Carl Lender; 2015-11-04 | CC BY 2.0 | Generic server racks, **not** Amazon or any 2026 hyperscaler project |

License pages must accompany images: link to the applicable Creative Commons license, name the author, explain date/location/crop/resizing, and apply attribution/share-alike obligations to adapted image files when relevant. Never infer image rights from a news RSS feed.

## Chart specifications reserved for P2
- **A Hormuz high-level geography and oil flow**: EIA [World Oil Transit Chokepoints](https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints). Historical period labelled; no real-time vessel movements or unsupported event locations.
- **B Brent/WTI daily price trend**: EIA [Petroleum Spot Prices](https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm). USD/bbl, aligned data dates, source update timestamp and no fabricated causal conclusion.
- **C Fed / ECB / BOJ policy**: [Fed historical policy target range](https://www.federalreserve.gov/monetarypolicy/openmarket.htm), [ECB interest-rate history](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html), [BOJ 2026 monetary policy statements](https://www.boj.or.jp/en/mopo/mpmdeci/state_2026/). Three comparable small multiples but each has its OWN rate definition. The BOJ basic discount rate is **not** substituted for the policy rate.
- **D AI CapEx**: [Amazon Q3 2026 IR](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/default.aspx) and original SEC exhibit. Comparable peers remain unpopulated until own same-basis financial filings are reviewed; actual cash purchases must never be mixed with planned CapEx.

## Acceptance checklist
- [x] Main/Style C/production untouched and original news text unchanged
- [x] Four chart designs A–D acknowledged and source requirements recorded
- [x] Three background image source license pages inspected
- [x] Captions state photographed date/location and noncontemporaneous nature
- [ ] Actual licensed bytes downloaded under permissible access limits
- [ ] Original SHA256 and color/grayscale Boox file checks
- [ ] Contemporaneous event-specific cover image legally cleared
- [ ] HTML & EPUB offline embedding, responsive crop and BOOX real-device test

**P1 overall: HOLD — provenance/rights research completed, production-eligible offline photo assets incomplete.**
