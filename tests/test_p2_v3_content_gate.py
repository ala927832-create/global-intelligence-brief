"""V3 owner-required first gate: fail CLOSED before Gemini, HTML and EPUB."""
from __future__ import annotations
import datetime as dt
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qa.p2_content_gate import source_input_gate, selected_story_gate
from gib.contract import locked_contract
from qa import p2_integrated_batch as batch

CUTOFF=dt.datetime(2026,10,29,7,30,tzinfo=dt.timezone(dt.timedelta(hours=8)))
FRESH=dt.datetime(2026,10,28,23,25,tzinfo=dt.timezone.utc).isoformat()

def article(i):
    topics=["government election","central bank inflation","technology semiconductor",
            "energy oil refinery","climate cyclone"]
    label=topics[i%len(topics)]
    distinct=hashlib.sha256(str(i).encode()).hexdigest()[:24]
    return {
        "title":f"{label} confirmed developments {distinct} separate international event",
        "url":f"https://publisher{i%5}.example/world/story-{i}",
        "published_at":FRESH,
        "snippet":f"Publisher report {i}: "+("Detailed source-attributed news facts " * 4),
        "provider":"direct_opml_rss",
        "official":False
    }

class V3ContentGateTests(unittest.TestCase):
    def test_new_authoritative_owner_rules(self):
        c=locked_contract()
        self.assertEqual(c["contract_version"],"2026-10-29-owner-approved-v3")
        target=c["editorial_acceptance"]["morning_content"]
        self.assertEqual([target[k] for k in
                        ("main_news_min","main_news_max","supplementary_news_min",
                         "supplementary_news_max","unique_news_total_min",
                         "distinct_substantive_analyses","deep_research_min")],
                         [10,12,10,12,20,4,1])
        self.assertEqual([v["minutes"] for v in c["versions"]],["30-40","40-50"])
        self.assertEqual([v["evening_minutes"] for v in c["versions"]],["10-15","30-45"])
        self.assertEqual(len(c["editorial_acceptance"]["sequential_improvements"]),3)

    def test_counts_unique_events_not_duplicate_reprints(self):
        rows=[article(i) for i in range(20)]
        ok=source_input_gate(rows,CUTOFF)
        self.assertEqual(ok["gate"],"PASS_SOURCE_CANDIDATES_ONLY_NOT_FACT_VERIFIED",ok)
        self.assertEqual(ok["distinct_evidence_bearing_events"],20)
        self.assertEqual(ok["original_publisher_domains"],5)
        self.assertGreaterEqual(ok["editorial_topic_groups"],4)
        dup=article(0);dup["url"]="https://anotherpublisher.example/world/copied-0"
        fail=source_input_gate(rows[:19]+[dup],CUTOFF)
        self.assertEqual(fail["gate"],"HOLD_SOURCE_INPUT_INCOMPLETE")
        self.assertLess(fail["distinct_evidence_bearing_events"],20)

    def test_title_only_or_stale_headline_cannot_pass(self):
        rows=[article(i) for i in range(21)]
        rows[0]["snippet"]=""
        rows[1]["published_at"]="2026-10-25T10:00:00+00:00"
        fail=source_input_gate(rows,CUTOFF)
        self.assertEqual(fail["gate"],"HOLD_SOURCE_INPUT_INCOMPLETE")
        self.assertTrue(fail["rejected"]["TITLE_ONLY_OR_INSUFFICIENT_SOURCE_TEXT"])
        self.assertTrue(fail["rejected"]["OUTSIDE_WINDOW_OR_MISSING_DATETIME"])

    def test_selection_requires_main_supplement_not_just_20_uncategorized_links(self):
        i={"edition":"morning","articles":[{"event_id":str(n)} for n in range(24)]}
        out=selected_story_gate(i)
        self.assertEqual(out["gate"],"HOLD_SELECTED_STORY_VOLUME")
        self.assertIn("MAIN_NEWS_COUNT_OUTSIDE_10_12",out["blockers"])
        self.assertIn("SUPPLEMENT_NEWS_COUNT_OUTSIDE_10_12",out["blockers"])
        i["articles"]=[{"event_id":str(n),"editorial_tier":"main" if n<12 else "supplement"} for n in range(24)]
        ok=selected_story_gate(i)
        self.assertEqual(ok["gate"],"PASS_EDITORIAL_VOLUME_ONLY_NOT_EVIDENCE_VERIFIED")
        self.assertFalse(ok["publication_approved"])

    def test_underfilled_live_batch_writes_diagnostic_and_never_calls_publishing(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            with patch.object(batch,"OUTPUT",out), \
                 patch.object(batch,"collect",return_value=([],{"gate":"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED"})), \
                 patch.object(batch,"collect_existing_free_sources",return_value={}), \
                 patch.object(batch,"fuse_with_original_opml",return_value=([],{
                    "gate":"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED",
                    "configured_sources":24,"original_opml_p1_gate":"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED",
                    "data_origin":"USER_OPML_PLUS_EXISTING_FREE_PUBLIC_INDEXES"})), \
                 patch.object(batch,"run",side_effect=AssertionError("MUST_NEVER_RENDER")):
                result=batch.run_batch(report_date="2026-10-28",
                    now=dt.datetime(2026,10,29,0,0,tzinfo=dt.timezone.utc),
                    gemini=True)
            self.assertEqual(result["gate"],"HOLD_NO_READER_PREVIEW")
            self.assertFalse(result["gemini_called"])
            self.assertFalse(result["nonpublished_preview_generated"])
            self.assertEqual(result["editions"],{})
            self.assertTrue((out/"2026-10-28"/"P2_V3_CONTENT_HOLD.json").exists())
            self.assertFalse(list(out.rglob("*.epub")))
            self.assertFalse(list(out.rglob("*.html")))

if __name__=="__main__":
    unittest.main()
