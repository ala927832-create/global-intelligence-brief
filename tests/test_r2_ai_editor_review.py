"""AI review is not a substitute for owner-required human editorial approval."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/"qa/r2_ai_editor_review_18_claims_20261029.json"
LEDGER=ROOT/"qa/r2_crosssource_claim_ledger_20261029.json"

class AiFactReviewIntegrityTests(unittest.TestCase):
    def test_eighteen_real_claim_ids_with_bounded_ai_only_reviewer(self):
        report=json.loads(REVIEW.read_text(encoding="utf-8"))
        ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
        claim_to_sources={
            c["id"]:set(c["source_ids"])
            for topic in ledger["dossiers"] for c in topic["claims"]}
        checks=report["claim_reviews"]
        self.assertEqual(len(checks),18)
        self.assertEqual({x["claim_id"] for x in checks},set(claim_to_sources))
        self.assertTrue(all(set(x["source_ids"])==claim_to_sources[x["claim_id"]]
                            for x in checks))
        self.assertTrue(all(x["reviewer"]=="AI_GPT6" and not x["human_signature"]
                            and not x["public_release_permitted"]
                            for x in checks))
        self.assertEqual(sum(x["status"].startswith("DIRECT_PRIMARY_SUPPORTED")
                             for x in checks),16)
        self.assertEqual(sum(x["status"]=="ORIGINAL_ISSUER_AUTHORED_DISTRIBUTOR_FULL_TEXT_VERIFIED"
                             for x in checks),1)
        self.assertEqual(sum(x["status"]=="CONDITIONAL_DERIVED_COMPARISON"
                             for x in checks),1)
        self.assertEqual(report["review_status_counts"]["direct_original_primary_supported"],16)
        self.assertEqual(report["review_status_counts"]["original_index_direct_access_blocked"],0)
        self.assertEqual(report["review_status_counts"]["original_issuer_authored_distributor_text_available"],1)
        self.assertEqual(report["original_author_source_distribution_count"],1)
        reviewed={x["claim_id"]:x for x in checks}
        for cid in ("D03","T02"):
            self.assertEqual(reviewed[cid]["review_access"],"WEB_TEXT_DIRECT_ORIGINAL_PRIMARY")
            self.assertFalse(reviewed[cid]["additional_source_needed"])
        self.assertFalse(reviewed["D04"]["additional_source_needed"])
        self.assertIn("HTTP 403",reviewed["D04"]["verification_note"])
        self.assertIn("presseportal.de",reviewed["D04"]["independently_read_publisher_distribution_url"])
        self.assertIn("NOT been demonstrated",reviewed["T03"]["limitation"])
        self.assertTrue(report["ai_reviewer_work_completed"])
        self.assertTrue(report["ai_review_does_not_satisfy_original_human_signature_gate"])
        self.assertEqual(report["verified_human_editorial_signatures"],0)
        self.assertFalse(report["headline_coverage_cutoff_0730_persisted_and_verified"])
        self.assertFalse(report["gemini_pass_1_permitted"])
        self.assertFalse(report["gemini_pass_2_permitted"])
        self.assertFalse(report["release_approved"])

    def test_ai_review_must_not_mutate_original_newsroom_ledger_to_verified(self):
        ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
        for topic in ledger["dossiers"]:
            self.assertFalse(topic["human_reviewed"])
            self.assertFalse(topic["ready_for_gemini"])
            for claim in topic["claims"]:
                self.assertFalse(claim["editor_signed"])
                self.assertNotEqual(claim["source_match_status"],"VERIFIED")

if __name__=="__main__":
    unittest.main()
