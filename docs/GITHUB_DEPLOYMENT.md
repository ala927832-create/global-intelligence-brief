# GitHub deployment — Global Intelligence Brief

This is a QA-only, no-publication deployment package. The owner-approved `config/frozen_contract.json` remains unchanged, including the 5 stages, 6 report sections, and 4 specified schedule points. Zinc Intelligence is a separate repository and is not to be modified.

## Existing repository

https://github.com/ala927832-create/global-intelligence-brief

The GitHub repository was bootstrapped with `README.md`, `qa/source_connectivity.py`, and `.github/workflows/connection_qa.yml`. Live checks verified FreeNewsApi.io and Gemini API key authentication (model generation was not called); GDELT sometimes returned 429; BLS returned 403 from the GitHub runner. Source availability is not the same as claim verification.

## Import full newsroom code

Extract this ZIP locally. Upload all contents **inside** the package's `global-intelligence-brief/` folder to the root of the GitHub repository, keeping nested paths, e.g. `gib/`, `config/`, `tests/`, `.github/workflows/`, `assets/`. Do **not** replace or remove `qa/source_connectivity.py` and `.github/workflows/connection_qa.yml`; they are separate credentials diagnostics already in GitHub. The complete 37-test suite passes locally (2026-10-23). Do not accidentally upload `.env`, token/key files or private Zinc data.

If doing this with git CLI, clone the repository, copy the *contents* of the extracted folder into it (not a nested extra folder), and push one reviewable commit.

## Run QA (no public delivery)

1. GitHub → Actions → `GIB - manual editorial and EPUBCheck QA (no publication)` → Run workflow; select `source_mode=live_sources`, `edition=morning`, initially `use_gemini_free=false`.
2. Confirm API connectivity and see QA artifacts. Run again with `use_gemini_free=true` only **after verifying that the selected Gemini model/project has appropriate free quota**, and setting repository Variable `GEMINI_FREE_TIER_CONFIRMED=1`.
3. Check EPUBCheck results and inspect both EPUBs on BOOX Note Air4 C. A successful run is **not** editorial approval.
4. To begin scheduled QA, set repository Variable `QA_ARMED=1` after manual QA. It runs QA only, no LINE/Pages, with source freshness and verification gaps recorded; ten **qualified** NYSE trading sessions with both morning and evening are required. Existing Zinc schedules remain unchanged.

## Sources and failure handling

- FreeNewsApi.io `FREENEWS_API_KEY` is private in GitHub Actions Secrets.
- Gemini `GEMINI_API_KEY` is private in GitHub Actions Secrets; model requests require explicit free-tier confirmation variable.
- GDELT HTTP 429: respect throttle and retry later, avoid tight retries.
- BLS HTTP 403: this host blocks some datacenter accesses; do not bypass. Keep status `source unavailable` and corroborate with other official primary documents/manual evidence review.
- Final publication is blocked until the ten-day review, real source/claim verification, EPUBCheck, BOOX real-device checks, and owner signoff.
