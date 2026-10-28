# Global Intelligence Brief V1.6 — Editorial Newsroom Integration QA

> **編輯定位：** GIB 是獨立的全球新聞與深度研究刊物，不是台灣工業補助、鋅或鍍鋅產業專報。已批准的六章節／雙版本規格以 [frozen_contract.json](config/frozen_contract.json) 為準，不因 RSS 資料夾命名或專業查核來源變更。見 [2026-10-28 編輯定位校正](docs/GIB_EDITORIAL_RESTORE_20261028.md) 與 [AGENTS.md](AGENTS.md)。

Separate from **Zinc Intelligence**, retaining existing Zinc 10:30/17:30 workflows completely untouched. Morning 07:30, evening 17:30 planned only after source and BOOX QA.

**Read first:** [EDITORIAL_V16_IMPLEMENTATION.md](EDITORIAL_V16_IMPLEMENTATION.md).

Key modules: source collectors `gib/collect.py`, canonical evidence `gib/newsroom_v16.py`, optional Gemini 2-round editor `gib/gemini_editor_v16.py`, direct XHTML/EPUB publisher `gib/publish_v16.py`, CLI `run_newsroom_v16.py`.

Production remains **OFF**. The current fixture is deliberately too small and old to qualify. No private Zinc values are included. No API keys inside repo. Gemini not yet connected to user's account. Zero paid fallback.

Use the manual workflow `.github/workflows/newsroom_v16_qa.yml` to inspect source health and evidence; do not enable live schedule/LINE by copying older workflow configurations.
