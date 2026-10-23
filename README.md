# Global Intelligence Brief

**Status:** Initial repository setup and credential/source diagnostics. **No public release, LINE messages or market-trade actions.**

This project is independent of Zinc Intelligence. The approved specification is frozen pending owner authorization:

1. Python news collection (FreeNewsApi.io + GDELT + official RSS), event evidence.
2. Gemini research and explanation (first pass).
3. Python claim/evidence validation.
4. Gemini revision/editorial quality (second pass).
5. Professional XHTML / EPUB 3: Essential and Deep Research.

Six report sections (fixed order): Executive Brief; The World in Brief; Essential Analysis; Deep Research; What Changed & What to Watch; Sources & Evidence.

Editorial defaults: Traditional Chinese; Layout 01; BOOX Note Air4 C; 3:4 cover; Essential 10–15 minutes / Deep 30–45 minutes. Schedule after sign-off: Global 07:30 / 17:30 Taiwan; existing Zinc 10:30 / conditional 17:30 remains unchanged.

## Credential and live-source diagnostic

GitHub Actions → **GIB connection QA** checks FreeNewsApi.io, GDELT and official Fed/BLS/BoJ RSS. Gemini performs a minimal API test **only after** the repository variable `GEMINI_FREE_TIER_CONFIRMED=1` is set. Never paste secrets into tickets, logs, files or chat.

Secrets: `GEMINI_API_KEY`, `FREENEWS_API_KEY`. Variable: `GEMINI_FREE_TIER_CONFIRMED=1` only when the selected Gemini project/model actually has a free quota and no unwanted billing.

**This diagnostic is not** the 10-trading-day acceptance run or the full V1.7 newsroom. The locked full newsroom package is not yet committed. Publication remains intentionally disabled until live verification, EPUBCheck, BOOX device verification, and explicit owner approval.

