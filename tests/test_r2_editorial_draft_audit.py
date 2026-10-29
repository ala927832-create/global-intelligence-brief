"""R2 structural editorial audit regression; no artificial fact signoff."""
import copy
import json
import unittest
from qa.r2_editorial_draft_audit import inspect, LEDGER, ANALYSES, STUDIES

class EditorialEvidenceDraftAuditTests(unittest.TestCase):
    def setUp(self):
        self.ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
        self.analyses=json.loads(ANALYSES.read_text(encoding="utf-8"))
        self.studies=json.loads(STUDIES.read_text(encoding="utf-8"))

    def test_real_public_research_ledger_four_long_analyses_two_deep_studies_are_source_cited(self):
        x=inspect(self.ledger,self.analyses,self.studies)
        self.assertTrue(x["source_lineage_and_draft_structure_pass"],x["structural_blockers"])
        self.assertEqual(x["distinct_news_focus_articles"],4)
        self.assertEqual(x["headline_linked_deep_studies"],2)
        self.assertGreater(x["focus_analysis_chinese_hanzi"],3400)
        self.assertGreater(x["deep_studies_chinese_hanzi"],2000)
        self.assertGreaterEqual(x["unique_cited_claims"],18)
        self.assertFalse(x["independent_human_fact_verification_completed"])
        self.assertFalse(x["editorial_depth_signoff_completed"])
        self.assertFalse(x["gemini_pass_one_called"])
        self.assertFalse(x["gemini_pass_two_called"])
        self.assertFalse(x["release_approved"])
        self.assertEqual(x["g2_status"],"HOLD_EVIDENCE_AND_HUMAN_EDITORIAL_SIGNOFF")

    def test_unsourced_added_claim_must_fail(self):
        changed=copy.deepcopy(self.analyses)
        changed["articles"][0]["sections"]["background"]+="[F99]"
        result=inspect(self.ledger,changed,self.studies)
        self.assertIn("CITED_CLAIM_MISSING_FROM_EVIDENCE_LEDGER",
                      result["drafts"][0]["structural_blockers"])
        self.assertFalse(result["source_lineage_and_draft_structure_pass"])

    def test_missing_counterargument_or_institutional_reference_must_fail(self):
        altered=copy.deepcopy(self.ledger)
        altered["dossiers"][0]["counterevidence"]=[]
        altered["dossiers"][0]["sources"]=altered["dossiers"][0]["sources"][:1]
        result=inspect(altered,self.analyses,self.studies)
        self.assertFalse(result["source_lineage_and_draft_structure_pass"])
        self.assertIn("MISSING_COUNTEREVIDENCE_OR_CAUSAL_CHAIN",
                      result["drafts"][0]["structural_blockers"])

    def test_gemini_or_unsigned_verified_ledger_cannot_claim_pass(self):
        changed=copy.deepcopy(self.analyses)
        changed["gemini_passes"]=2
        result=inspect(self.ledger,changed,self.studies)
        self.assertIn("GEMINI_PASS_RECORDED_BEFORE_SIGNOFF",result["structural_blockers"])
        altered=copy.deepcopy(self.ledger)
        altered["dossiers"][0]["claims"][0]["editor_signed"]=True
        result2=inspect(altered,self.analyses,self.studies)
        self.assertIn("UNATTESTED_CLAIM_PREMATURELY_MARKED_VERIFIED",
                      result2["drafts"][0]["structural_blockers"])

if __name__=="__main__":
    unittest.main()
