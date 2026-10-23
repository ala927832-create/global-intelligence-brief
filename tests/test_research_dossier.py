"""Review dossiers retain source provenance, not unsupported truth labels."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from gib.newsroom_v16 import canonical_issue
from gib.research_dossier import make_dossiers, write_review_workbook, progress
from gib.gemini_editor_v16 import _prepare
from gib.publish_v16 import as_xhtml

NOW=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)

class ResearchDossierTests(unittest.TestCase):
    def setUp(self):
        examples=[
          ("Central bank release on global financing conditions",
           "https://www.federalreserve.gov/newsevents/pressreleases/example-a.htm"),
          ("Asia shipping costs and manufacturing bottlenecks",
           "https://publisher.example/shipping"),
          ("International energy supply review",
           "https://www.eia.gov/pressroom/releases/example.htm"),
          ("Technology chip policy report",
           "https://publisher.example/chips"),
        ]
        rows=[{"title":title,"url":url,"published_at":NOW.isoformat(),
               "publisher":"Official" if ".gov/" in url else "Newswire",
               "snippet":"Provider summary; claim is NOT independently verified.",
               "official":".gov/" in url} for title,url in examples]
        self.issue=canonical_issue(rows,"morning",NOW)
        self.assertGreaterEqual(len(self.issue["articles"]),3)

    def test_missing_primary_evidence_is_explicit(self):
        ds=make_dossiers(self.issue)
        self.assertEqual(len(ds),3)
        for d in ds:
            self.assertEqual(d["editorial_state"],"OPEN_NEEDS_HUMAN_REVIEW")
            self.assertFalse(d["automatically_verified"])
            self.assertEqual(d["manually_attested_claims"],0)
            self.assertTrue(d["missing_evidence"])
            self.assertEqual(d["claims"][0]["verification"],"ATTRIBUTED_UNVERIFIED")

    def test_worksheet_contains_claim_ids_with_no_fake_signatures(self):
        self.issue["research_dossiers"]=make_dossiers(self.issue)
        with tempfile.TemporaryDirectory() as folder:
            outputs=write_review_workbook(self.issue,folder)
            text=Path(outputs["review_md"]).read_text(encoding="utf-8")
            self.assertIn("尚未簽核",text)
            self.assertIn("來源發布時間",text)
            self.assertIn("反方／替代解釋",text)
            self.assertTrue(Path(outputs["dossiers_json"]).is_file())
            self.assertEqual(outputs["events"],3)
        self.assertFalse(progress(self.issue)["auto_publish_permitted"])
        self.assertEqual(progress(self.issue)["manually_reviewed_events"],0)

    def test_evidence_is_inside_offline_book(self):
        claim=self.issue["articles"][0]["evidence"][0]
        claim["official_context_excerpt"]="Example official source note about economic conditions"
        claim["retrieved_at"]=NOW.isoformat()
        claim["source_sha256"]="a"*64
        page=as_xhtml(self.issue, [], level="deep")
        self.assertIn("Example official source note",page)
        self.assertIn("SHA-256",page)

    def test_research_gap_is_part_of_gemini_bound_input(self):
        self.issue["research_dossiers"]=make_dossiers(self.issue)
        inp=_prepare(self.issue)
        self.assertEqual(len(inp["events"]),3)
        for event in inp["events"]:
            req=event["research_requirements"]
            self.assertTrue(req["missing_evidence"])
            self.assertEqual(req["manually_attested_claims"],0)
            self.assertEqual(len(event["evidence"]),1)


if __name__=="__main__":
    unittest.main()
