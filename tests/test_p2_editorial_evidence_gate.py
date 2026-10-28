"""Regression: genuine world-news coverage, time boundaries and evidence remain fail-closed."""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from gib.editorial import material_news_candidate
from gib.p2_editorial_acceptance import assess_snapshot, inspect_lead_evidence, p2_readiness
from tools.gib_style_c_rc.live_html_qa import bounds
from qa.p2_integrated_batch import local_cutoff


class P2EditorialEvidenceGateTests(unittest.TestCase):
    def test_original_scheduled_half_hours_are_exact(self):
        date=dt.date(2026,10,27)
        start,end=bounds(date,"morning")
        self.assertEqual(start.isoformat(),"2026-10-26T17:30:00+08:00")
        self.assertEqual(end.isoformat(),"2026-10-27T07:30:00+08:00")
        start2,end2=bounds(date,"evening")
        self.assertEqual(start2,end)
        self.assertEqual(end2.isoformat(),"2026-10-27T17:30:00+08:00")
        self.assertEqual(local_cutoff(date,"morning"),end.astimezone(dt.timezone.utc))
        self.assertEqual(local_cutoff(date,"evening"),end2.astimezone(dt.timezone.utc))

    def test_late_snapshot_never_proves_a_completed_edition(self):
        target=dt.datetime(2026,10,26,23,30,tzinfo=dt.timezone.utc)
        late={"checked_at_utc":"2026-10-28T03:47:00+00:00"}
        result=assess_snapshot(late,target)
        self.assertEqual(result["state"],"RETROSPECTIVE_SNAPSHOT_NOT_COMPLETE")
        self.assertGreater(result["lag_minutes"],1500)
        self.assertFalse(result["on_time_proven"])
        invalid=assess_snapshot({"checked_at_utc":"unknown"},target)
        self.assertEqual(invalid["state"],"CAPTURE_TIMESTAMP_INVALID")

    def test_global_relevance_covers_elections_ceasefire_and_chinese_world_news(self):
        for title in ("European parliament election raises trade questions",
                      "United Nations seeks ceasefire in regional conflict",
                      "國際協議引發全球市場關注",
                      "聯合國發表人道危機報告"):
            self.assertTrue(material_news_candidate({"title":title}),title)
        self.assertFalse(material_news_candidate(
            {"title":"Football championship goalscorer celebrated"}))
        self.assertFalse(material_news_candidate(
            {"title":"Celebrity red carpet fashion at awards party"}))

    def test_two_media_domains_still_do_not_qualify_as_fact_corrob(self):
        a={"event_id":"lead-A","event_time_utc":None,
           "sources":[
             {"source_id":"a","url":"https://news-one.example/a","publisher":"One"},
             {"source_id":"b","url":"https://news-two.example/a","publisher":"Two"}
           ],
           "evidence":[{"claim_id":"c1","verification":"ATTRIBUTED_UNVERIFIED",
                        "source_id":"a","source_location":"feed headline/snippet"}]}
        issue={"edition":"morning","articles":[a],
               "editorial_depth_audit":{"deep_drafts_meeting_minimum_review_standard":0},
               "source_health":{"distinct_domains":2,"cutoff_snapshot":{
                   "state":"RETROSPECTIVE_SNAPSHOT_NOT_COMPLETE"}},
               "gemini_editorial":{"status":"SECOND_PASS_NO_MATERIAL_EDIT"},
               "editorial_status":"REVIEW_REQUIRED"}
        report=p2_readiness(issue)
        self.assertEqual(report["gate"],"P2_EDITORIAL_HOLD")
        self.assertFalse(report["automatic_release_approved"])
        self.assertIn("NO_MANUALLY_SIGNED_VERIFIED_CLAIM",report["lead_evidence"][0]["gaps"])
        self.assertIn("EVENT_OCCURRENCE_TIME_UNCONFIRMED",report["lead_evidence"][0]["gaps"])
        self.assertIn("ONE_EVIDENCED_DEEP_STUDY_MISSING",report["blockers"])
        self.assertIn("PER_EDITION_REAL_TIME_SOURCE_COVERAGE_UNPROVEN",report["blockers"])

    def test_official_exact_excerpt_is_not_verified(self):
        a={"event_id":"lead-B","event_time_utc":"2026-10-27T01:00:00+00:00",
           "sources":[{"url":"https://www.federalreserve.gov/abc","source_id":"one"},
                      {"url":"https://news.example/abc","source_id":"two"}],
           "evidence":[{"verification":"SOURCE_EXCERPT_MATCH_NOT_FACT_VERIFIED",
                        "source_sha256":"1234567890","source_location":"official",
                        "source_id":"one"}]}
        result=inspect_lead_evidence({"articles":[a]})[0]
        self.assertEqual(result["located_official_excerpt_not_fact_verified"],1)
        self.assertEqual(result["manually_signed_claims"],0)
        self.assertFalse(result["independently_verified_lead"])


if __name__=="__main__":
    unittest.main()
