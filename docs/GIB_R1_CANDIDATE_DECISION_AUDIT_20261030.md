# R1 candidate decision replay audit — 2026-10-30

Internal evidence only; not editorial signoff or release.

- Frozen actual source: six real captures artifact 12944730644.
- Replay: GitHub Actions 40982943508, artifact 12945951483 (full_replay.json plus review_01..06).
- Six structural source/selection gates PASS; each generated 12 main and 12 supplement.
- Counts per capture: 238, 239, 239, 239, 237, 237 ranked candidate records. All have a source URL, selected position if selected, rank score, editorial-type heuristic, event-family heuristic, and exclusion reason.
- Each: 24 selected; 3 nonselected candidates tagged as potentially related selected event family; 8 nonselected candidates score >= 24th selected candidate's score. These 8 are *audit flags*, not proof they should replace selected items.
- Failure: "LOWER_EDITORIAL_RANK_OR_DIVERSITY_CAP_REVIEW" is not a resolved factual editorial reason; title-based labels are hypotheses, and event families are incomplete (e.g. major Ukraine refinery ceasefire or Saudi airport attack may be missed by taxonomy). No independent case-by-case signoff, no verified 90+ expert score.
- Example review priorities: omitted Big Tech data-center spending and Bank of Japan rates, plus omitted Israel election final count potentially same event. Selected Iran Hormuz and Israel election require claim-grounded uniqueness checks. This document reports source headlines as publisher claims only.
- Verdict: automated candidate audit artifact EXISTS, but independent editorial review, actual omission signoff and 90-point critical quality FAIL/HOLD. Do not merge or publish.

Do not conflate selected URL uniqueness with true distinct world events. The six captures cover near-identical time windows and are not six independent news cycles.
