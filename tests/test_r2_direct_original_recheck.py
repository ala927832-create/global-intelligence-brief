"""R2 public-original recheck must not counterfeit unavailable pages, signatures or reserves."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECHECK=ROOT/"qa/r2_direct_original_source_recheck_20261029.json"
REVIEW=ROOT/"qa/r2_ai_editor_review_18_claims_20261029.json"

class DirectPrimaryRecheckTests(unittest.TestCase):
    def test_direct_index_derived_strict_partition(self):
        src=json.loads(RECHECK.read_text(encoding="utf-8"))
        r=json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual((src["direct_primary_count_for_eighteen_claims"],
                          src["indexed_original_limited_count_for_eighteen_claims"],
                          src["conditional_derived_count_for_eighteen_claims"]),(16,1,1))
        self.assertEqual(len(r["claim_reviews"]),18)
        self.assertEqual(r["ai_fact_source_direct_count"],16)
        self.assertEqual(r["indexed_original_limited_count"],1)
        self.assertEqual(r["conditional_derivation_count"],1)
        x={i["claim_id"]:i for i in src["source_rechecks"]}
        self.assertEqual(set(x),{"D03","D04","T02","T03"})
        self.assertEqual(x["D04"]["direct_original_response"],"HTTP_403_NOT_DIRECTLY_RETRIEVED")
        self.assertFalse(src["human_editorial_signoff"])
        self.assertFalse(src["automated_claim_signature"])
        self.assertFalse(src["two_pass_gemini_authorized"])
        self.assertFalse(src["publication_approved"])
        self.assertTrue(x["T03"]["relative_difference_not_interpreted_as_reserve_revision"])
        self.assertTrue(x["T03"]["no_identical_resource_classification_or_appraisal_method_shown"])

    def test_dated_original_publication_and_units_are_explicit(self):
        j=json.loads(RECHECK.read_text(encoding="utf-8"))
        x={i["claim_id"]:i for i in j["source_rechecks"]}
        self.assertEqual(x["D03"]["original_publication"],"2026-10-13")
        self.assertEqual(x["D04"]["original_publication"],"2026-09-30")
        self.assertEqual(x["T02"]["original_publication"],"2026-10-28")
        self.assertEqual(x["T03"]["dated_observations"][-1]["value"],23)
        self.assertTrue(all(not i["editor_human_signed"]
                            for i in j["source_rechecks"]))
        self.assertTrue(j["g2_status"].startswith("HOLD"))

if __name__=="__main__":
    unittest.main()
