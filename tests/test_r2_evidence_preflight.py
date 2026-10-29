"""R2 tests are source-first, never a synthetic pass for real news quality."""
import datetime as dt
import hashlib
import unittest
from qa.r2_evidence_preflight import scan_source_index
from gib.contract import locked_contract

CUTOFF=dt.datetime(2026,10,29,7,30,
                   tzinfo=dt.timezone(dt.timedelta(hours=8)))
NOW=dt.datetime(2026,10,29,1,0,tzinfo=dt.timezone.utc)
PUBLISHED="2026-10-28T23:25:00+00:00"

def sample_rows(n=24):
    labels=["government election","central bank inflation",
            "technology semiconductor","energy oil refinery",
            "climate cyclone"]
    return [{
        "title":labels[i%5]+" major distinct update "+hashlib.sha256(str(i).encode()).hexdigest(),
        "url":f"https://publisher{i%5}.example/world/report-{i}",
        "published_at":PUBLISHED,
        "publisher":f"Publisher {i%5}",
        "provider":"direct_opml_rss",
        "source_group":"global",
        "snippet":f"Publisher fact report {i}: "+("source-index facts awaiting manual verification " * 3),
    } for i in range(n)]

class R2PreflightTests(unittest.TestCase):
    def test_r1_structural_success_opens_r2_testing_but_not_content_approval(self):
        report=scan_source_index(sample_rows(),NOW)
        self.assertTrue(report["r1"]["source_and_selection_structural_ready"],report)
        self.assertTrue(report["r2"]["started"])
        self.assertEqual(report["r2"]["status"],"HOLD_G2_EVIDENCE_AND_EDITORIAL_DEPTH")
        self.assertEqual(report["r2"]["completed_source_grounded_analyses"],0)
        self.assertEqual(report["r2"]["completed_current_deep_studies"],0)
        self.assertEqual(report["r2"]["independently_verified_top_three_leads"],0)
        self.assertIn("FOUR_EVIDENCED_DISTINCT_ANALYSES_NOT_COMPLETED",report["r2"]["blockers"])
        self.assertIn("TWO_PASS_MATERIAL_GEMINI_REVISION_NOT_TESTED",report["r2"]["blockers"])
        self.assertFalse(report["gemini_called"])
        self.assertFalse(report["generated_html"])
        self.assertFalse(report["generated_epub"])
        self.assertFalse(report["actual_scheduled_cutoff_capture_verified"])
        self.assertFalse(report["release_approved"])

    def test_missing_r1_source_cannot_enter_r2(self):
        report=scan_source_index(sample_rows(5),NOW)
        self.assertFalse(report["r2"]["started"])
        self.assertEqual(report["r2"]["status"],"NOT_STARTED_R1_SOURCE_FAILED")
        self.assertFalse(report["release_approved"])

    def test_event_source_count_not_equivalent_to_fact_check(self):
        report=scan_source_index(sample_rows(24),NOW)
        self.assertGreater(report["r2"]["attributable_index_evidence_points"],0)
        self.assertEqual(report["r2"]["manually_attested_verified_claims"],0)
        self.assertFalse(report["human_editorial_signoff"])
        self.assertEqual(len(report["r2"]["lead_evidence_gaps"]),3)
        self.assertTrue(all("NO_MANUALLY_SIGNED_VERIFIED_CLAIM" in item["gaps"]
                            for item in report["r2"]["lead_evidence_gaps"]))
        self.assertEqual(locked_contract()["editorial_acceptance"]
                         ["morning_content"]["distinct_substantive_analyses"],4)
