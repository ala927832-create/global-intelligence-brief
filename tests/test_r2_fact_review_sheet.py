"""R2 editor review worksheet is always unsigned and only cites frozen sources."""
import copy
import json
import unittest
from qa.r2_fact_editor_review_sheet import render, LEDGER
from qa.r2_editorial_draft_audit import (
    inspect, ANALYSES, STUDIES
)

class EditorialReviewSheetTests(unittest.TestCase):
    def setUp(self):
        self.ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
        self.analyses=json.loads(ANALYSES.read_text(encoding="utf-8"))
        self.studies=json.loads(STUDIES.read_text(encoding="utf-8"))

    def test_all_18_claims_need_signed_review_and_fixed_public_sources(self):
        text=render(self.ledger)
        self.assertEqual(sum(len(x["claims"]) for x in self.ledger["dossiers"]),18)
        for claim in (c for p in self.ledger["dossiers"] for c in p["claims"]):
            self.assertIn("#### "+claim["id"],text)
        self.assertNotIn("https://www.bls.gov/news.release/cpi.nr0.htm",text)
        self.assertIn("https://www.bls.gov/news.release/archives/cpi_10142026.htm",text)
        self.assertIn("已完成的人工簽章：0",text)
        self.assertIn("- [ ] ",text)

    def test_mutable_release_link_breaks_structural_audit(self):
        altered=copy.deepcopy(self.ledger)
        for src in altered["dossiers"][0]["sources"]:
            if src["id"]=="F2":src["url"]="https://www.bls.gov/news.release/cpi.nr0.htm"
        result=inspect(altered,self.analyses,self.studies)
        self.assertFalse(result["source_lineage_and_draft_structure_pass"])
        self.assertIn("MUTABLE_LATEST_RELEASE_LINK_NOT_PINN",result["drafts"][0]["structural_blockers"])

    def test_future_date_rejected_as_source(self):
        altered=copy.deepcopy(self.ledger)
        altered["dossiers"][0]["sources"][0]["publication_date"]="2026-11-01"
        result=inspect(altered,self.analyses,self.studies)
        self.assertIn("SOURCE_PUBLISHED_AFTER_ISSUE_CUTOFF_DAY",result["drafts"][0]["structural_blockers"])

if __name__=="__main__":unittest.main()
