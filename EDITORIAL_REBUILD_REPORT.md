# Global Intelligence Brief — Editorial Rebuild Implementation Report

Date: 2026-10-23 (Asia/Taipei)  
Design selection: **Layout 01**, warm paper / navy / teal / amber.  
Target: BOOX Note Air4 C, reflowable EPUB 3.

## What was rebuilt

- `gib/editorial_rebuild.py`: a dedicated, reusable, evidence-bound rendering engine; outputs semantic XHTML, HTML and EPUB from a shared `issue-evidence.json` packet.
- `assets/editorial/layout01-magazine.css`: complete reflowable editorial layout (masthead, category strip, structured story, verified facts, deep research, watchlist, source links), no forced page break on every subheading.
- `gib/quality_gate.py`: transparent editorial integrity tests and minimum evidence/length gates.
- `make_research_sample.py` and `samples/official_research_2026-10-23.json`: a manually curated, **not live** source-backed sample researched from current official documents.
- `build_sample.py`: creates two independent EPUBs and HTML editions; builds **only if** the sample passes quality gates.
- `assets/editorial/weo-2026-outlook.png`: chart using IMF growth/inflation projections for 2026/27.
- `assets/editorial/us-cpi-sep2026.png`: chart using BLS September 2026 CPI data.
- `tests/test_editorial_rebuild.py`: actual EPUB document tests (not just ZIP mimetype checks).
- `.github/workflows/morning_evening.yml`: **manual-only quality build**. Does not post to LINE or alter Zinc Intelligence.

## Exact measured results

| Result | Value |
| --- | ---: |
| Essential Chinese ideographs | 1,878 |
| Deep Chinese ideographs | 7,955 |
| Real dated primary sources in packet | 7 |
| News/event research topics | 4 |
| In-depth research chapters | 4 |
| Source-backed charts in deep EPUB | 2 |
| Custom editorial quality checks | 15 / 15 passing |
| First-party automated editorial regression tests | 5 / 5 passing |

**Important:** character count does not prove a 10–15/30–45 minute human reading time. The sample makes NO assertion of real-time completeness. The preview screenshots are from the actual generated HTML markup, not an authenticated capture from BOOX NeoReader.

## Core known limitations

1. **Not yet live:** the new independent GitHub repository has not been created; no FreeNewsApi.io key has been added; no live ten-trading-day acceptance sample exists.
2. **No physical device test:** cannot claim BOOX NeoReader behavior from browser screenshots alone.
3. **EPUBCheck unavailable in this environment:** XHTML and OPF parse, EPUB3 nav and embedded images exist; formal EPUBCheck must be part of final acceptance.
4. **Original legacy `main.py` and `gib/render.py` remain in the starter archive strictly for continuity.** Their brief-only Markdown output must **not** be used as a qualified issue. The scheduled publishing workflow has therefore been disabled; only the new source-backed publication engine is QA-approved for sample builds.
5. **Evening delta validation missing live data:** no evening editorial sample is presented as actual increment before a morning/evening paired-day dataset exists.
6. **No unverified sidebars:** all quotes/figures in the source-backed sample are labeled. Layout concepts must not be interpreted as data or external expert quotes.

## Release acceptance to activate 07:30 / 17:30

- 10 trading days of real news capture from FreeNewsApi.io plus independent official RSS, tracked by source/date.
- News clustering precision, missing high-impact events, independent-source counts, official timekeeping and event-delta tests reviewed.
- Deep publication based on substantial primary evidence; insufficient data -> quality hold, not invented prose.
- EPUBCheck and at least two real BOOX NeoReader font-size settings reviewed with screenshot evidence.
- No leakage of inventory/procurement state from Zinc Intelligence; bridge remains read-only with allowlist.
- Only after the above do we enable independent 07:30 and 17:30 schedules and notification delivery; Zinc's existing jobs must remain unchanged.

## Repro commands

```bash
python -m pip install -r requirements.txt
python make_research_sample.py
python build_sample.py
python -m unittest discover -s tests -v
```

The generated sample is under `reports/2026-10-23/`. The newly rebuilt published preview is under `docs/archive/2026-10-23/`.

## Source links used in the sample

- IMF WEO: https://www.imf.org/en/Publications/WEO/Issues/2026/10/13/world-economic-outlook-october-2026
- IMF GFSR: https://www.imf.org/en/Publications/GFSR/Issues/2026/10/13/global-financial-stability-report-october-2026
- US BLS CPI: https://www.bls.gov/news.release/archives/cpi_10142026.htm
- Federal Reserve FOMC statement: https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm
- Federal Reserve calendar: https://www.federalreserve.gov/newsevents/2026-october.htm
- BOJ schedule: https://www.boj.or.jp/about/calendar/index.htm
- BLS release schedule: https://www.bls.gov/schedule/2026/
