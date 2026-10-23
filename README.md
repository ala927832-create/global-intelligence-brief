# Global Intelligence Brief V1.6 — Editorial Newsroom Integration QA

Separate from **Zinc Intelligence**, retaining existing Zinc 10:30/17:30 workflows completely untouched. Morning 07:30, evening 17:30 planned only after source and BOOX QA.

**Read first:** [EDITORIAL_V16_IMPLEMENTATION.md](EDITORIAL_V16_IMPLEMENTATION.md).

Key modules: source collectors `gib/collect.py`, canonical evidence `gib/newsroom_v16.py`, optional Gemini 2-round editor `gib/gemini_editor_v16.py`, direct XHTML/EPUB publisher `gib/publish_v16.py`, CLI `run_newsroom_v16.py`.

Production remains **OFF**. The current fixture is deliberately too small and old to qualify. No private Zinc values are included. No API keys inside repo. Gemini not yet connected to user's account. Zero paid fallback.

Use the manual workflow `.github/workflows/newsroom_v16_qa.yml` to inspect source health and evidence; do not enable live schedule/LINE by copying older workflow configurations.
