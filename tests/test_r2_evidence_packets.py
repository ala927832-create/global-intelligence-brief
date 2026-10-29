"""The four real-source evidence dossiers must be assembled before Gemini.

Fixture news and fake official HTTP content test safety/structure; they are
NOT editorial evidence and never pass for verified world-news reporting.
"""
import datetime as dt
import hashlib
import unittest

from gib.r2_evidence_packets import build_packets, choose_focus
from gib.newsroom_v16 import canonical_issue

NOW=dt.datetime(2026,10,29,1,0,tzinfo=dt.timezone.utc)
PUBLISHED="2026-10-28T23:25:00+00:00"
THEMES=[
    "government election policy",
    "central bank inflation",
    "technology semiconductor",
    "energy oil refinery",
    "climate cyclone",
    "asia economy exports"
]

def rows(n=24,official=False):
    result=[]
    for i in range(n):
        title=THEMES[i%len(THEMES)]+" unique sourced announcement "+hashlib.sha256(str(i).encode()).hexdigest()
        url=(f"https://www.federalreserve.gov/newsevents/pressreleases/mock-{i}.htm"
             if official and i<6 else f"https://news-publisher{i%5}.example/articles/{i}")
        result.append({
            "title":title,"url":url,
            "published_at":PUBLISHED,
            "snippet":f"Report {i} describes the following indexed announcement and relevant published event context for the global briefing.",
            "publisher":("Federal Reserve" if official and i<6 else f"Publisher {i%5}"),
            "provider":("official_rss" if official and i<6 else "direct_opml_rss"),
            "source_group":"global",
            "official":bool(official and i<6)
        })
    return result


class SourceFirstFourPacketsTests(unittest.TestCase):
    def test_four_distinct_focus_and_two_study_shortlist_without_writing_news(self):
        calls=[]
        def fake(url):
            calls.append(url)
            i=int(url.split("mock-")[1].split(".")[0])
            snippet=rows(24,official=True)[i]["snippet"]
            return {
                "text":"Official release page: "+snippet+" End of official page.",
                "sha256":"a"*64,
                "retrieved_at":NOW.isoformat()
            }
        result=build_packets(rows(24,official=True),NOW,fetcher=fake)
        self.assertEqual(result["status"],"HOLD_R2_EVIDENCE_BEFORE_GEMINI")
        self.assertEqual(len(result["analysis_packets"]),4)
        self.assertEqual(result["focus_distinct_topics"],4)
        self.assertEqual(len(result["current_deep_research_shortlist"]),2)
        self.assertEqual(result["focus_with_located_primary_context"],4,result)
        self.assertEqual(len(calls),4)
        self.assertEqual(result["focus_with_signed_claims"],0)
        self.assertEqual(result["focus_with_confirmed_contrary_evidence"],0)
        self.assertEqual(result["focus_with_verified_causal_data"],0)
        for packet in result["analysis_packets"]:
            self.assertTrue(packet["primary_official_context_not_fact_verified"])
            self.assertFalse(packet["evidence_ready_for_gemini"])
            self.assertTrue(packet["source_excerpt_sha256"])
            self.assertTrue(packet["article_publication_utc"])
            self.assertIsNone(packet["event_occurrence_utc"])
            self.assertIn("COUNTEREVIDENCE_WITH_SOURCE_LOCATION_NOT_VERIFIED",packet["blockers"])
            self.assertEqual(packet["signed_verified_claims"],0)
        self.assertFalse(result["gemini_called"])
        self.assertFalse(result["generated_reader_files"])
        self.assertFalse(result["release_approved"])

    def test_rss_only_never_licenses_gen_ai_facts(self):
        def forbidden(url):
            raise AssertionError("No official URLs should be fetched")
        result=build_packets(rows(24),NOW,fetcher=forbidden)
        self.assertEqual(len(result["analysis_packets"]),4)
        self.assertEqual(len(result["current_deep_research_shortlist"]),2)
        self.assertEqual(result["focus_with_located_primary_context"],0)
        self.assertFalse(result["gemini_first_pass_allowed"])
        self.assertFalse(result["gemini_second_pass_allowed"])

    def test_underfilled_source_fails_before_creating_study_packets(self):
        result=build_packets(rows(5),NOW,fetcher=lambda _:None)
        self.assertEqual(result["analysis_packets"],[])
        self.assertEqual(result["current_deep_research_shortlist"],[])
        self.assertEqual(result["status"],"HOLD_R1_STRUCTURE_BEFORE_R2_EVIDENCE_COLLECTION")
        self.assertFalse(result["gemini_called"])

    def test_primary_source_bound_not_fake_review_from_page_text(self):
        def fake(url):
            return {"text":"Unrelated current Federal Reserve homepage information",
                    "sha256":"b"*64,"retrieved_at":NOW.isoformat()}
        result=build_packets(rows(24,official=True),NOW,fetcher=fake)
        self.assertEqual(len(result["analysis_packets"]),4)
        self.assertEqual(result["focus_with_located_primary_context"],0)
        self.assertEqual(result["focus_with_signed_claims"],0)

if __name__=="__main__":
    unittest.main()
