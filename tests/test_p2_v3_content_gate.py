"""V3 owner-required first gate: fail CLOSED before Gemini, HTML and EPUB."""
from __future__ import annotations
import datetime as dt
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qa.p2_content_gate import source_input_gate, selected_story_gate, eligible_source_rows
from gib.newsroom_v16 import canonical_issue
from gib.contract import locked_contract
from qa import p2_integrated_batch as batch

CUTOFF=dt.datetime(2026,10,29,7,30,tzinfo=dt.timezone(dt.timedelta(hours=8)))
FRESH=dt.datetime(2026,10,28,23,25,tzinfo=dt.timezone.utc).isoformat()

def article(i):
    topics=["government election","central bank inflation","technology semiconductor",
            "energy oil refinery","climate cyclone"]
    label=topics[i%len(topics)]
    distinct=hashlib.sha256(str(i).encode()).hexdigest()
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
        i["articles"]=[{"event_id":str(n),"editorial_tier":"main" if n<12 else "supplement",
                        "topic":["macro","central_banks","geopolitics","asia","technology"][n%5],
                        "headline_summary":"Real publisher excerpt provides substantive reported facts " * 2,
                        "sources":[{"url":f"https://publisher{n%5}.example/world/story-{n}"}]}
                       for n in range(24)]
        ok=selected_story_gate(i)
        self.assertEqual(ok["gate"],"PASS_EDITORIAL_VOLUME_ONLY_NOT_EVIDENCE_VERIFIED")
        self.assertFalse(ok["publication_approved"])

    def test_v3_newsroom_selection_actually_produces_20_tiered_events(self):
        rows=[article(i) for i in range(22)]
        valid,rejected,_,_=eligible_source_rows(rows,CUTOFF)
        self.assertEqual(len(valid),22)
        self.assertFalse(rejected)
        issue=canonical_issue(valid,"morning",CUTOFF,tiered_v3=True,
                              require_material_relevance=False)
        outcome=selected_story_gate(issue)
        self.assertEqual(outcome["gate"],"PASS_EDITORIAL_VOLUME_ONLY_NOT_EVIDENCE_VERIFIED",outcome)
        # The deduplicator may legitimately coalesce near-identical test
        # headlines: 22 discovery URLs need NOT yield 22 unique events.
        self.assertGreaterEqual(outcome["unique_events"],20)
        self.assertLessEqual(outcome["unique_events"],22)
        self.assertGreaterEqual(outcome["main_news"],10)
        self.assertLessEqual(outcome["main_news"],12)
        self.assertGreaterEqual(outcome["supplementary_news"],10)
        self.assertLessEqual(outcome["supplementary_news"],12)
        self.assertEqual(outcome["main_news"]+outcome["supplementary_news"],
                         outcome["unique_events"])
        self.assertEqual(len({x["event_id"] for x in issue["articles"]}),
                         outcome["unique_events"])
        self.assertFalse(issue.get("release_approved",False))

    def test_legacy_evening_remains_unexpanded(self):
        rows=[article(i) for i in range(22)]
        issue=canonical_issue(rows,"evening",CUTOFF,require_material_relevance=True)
        self.assertLessEqual(len(issue["articles"]),12)
        self.assertTrue(all(x.get("editorial_tier") is None for x in issue["articles"]))

    def test_historical_backfill_is_not_mistaken_for_approved_cutoff_capture(self):
        old=CUTOFF-dt.timedelta(days=1)
        capture=CUTOFF+dt.timedelta(minutes=50)
        result=source_input_gate([article(i) for i in range(25)],old,
                                  observed_at=capture)
        self.assertIn("RETROSPECTIVE_CAPTURE_NOT_ON_TIME",result["blockers"])
        self.assertFalse(result["is_timely_cutoff_snapshot_proven"])
        current=source_input_gate([article(i) for i in range(25)],CUTOFF,
                                  observed_at=capture)
        self.assertEqual(current["distinct_evidence_bearing_events"],25)
        self.assertFalse(current["is_timely_cutoff_snapshot_proven"])

    def test_global_publisher_headline_wider_than_keyword_filter_but_not_sports(self):
        news=article(0)
        news["title"]="Historic parliamentary agreement reshapes society"
        news["source_group"]="global"
        news["source_groups"]=["global"]
        news["provider"]="direct_opml_rss"
        sport=dict(news,title="Tennis world cup football championship final",
                   url="https://publisher9.example/sport/unique")
        eligible,rejected,_,_=eligible_source_rows([news,sport],CUTOFF)
        self.assertEqual(len(eligible),1)
        self.assertEqual(rejected["SPORTS_NOT_NEWS_DESK"],1)

    def test_latest_morning_selection_is_measured_even_when_old_replay_fails(self):
        rows=[article(i) for i in range(22)]
        now=dt.datetime(2026,10,29,0,0,tzinfo=dt.timezone.utc)
        source_health={"gate":"PASS_DIRECT_RSS_DISCOVERY","configured_sources":24,
                       "original_opml_p1_gate":"PASS_DIRECT_RSS_DISCOVERY",
                       "data_origin":"USER_OPML_PLUS_EXISTING_FREE_PUBLIC_INDEXES"}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(batch,"OUTPUT",root), \
                 patch.object(batch,"collect",return_value=(rows,source_health)), \
                 patch.object(batch,"collect_existing_free_sources",return_value={}), \
                 patch.object(batch,"fuse_with_original_opml",
                              return_value=(rows,source_health)), \
                 patch.object(batch,"run",side_effect=AssertionError("NO_PREVIEW")):
                result=batch.run_batch(report_date="2026-10-28",now=now,gemini=True)
            self.assertEqual(result["gate"],"HOLD_NO_READER_PREVIEW")
            self.assertEqual(result["first_source_gate"]["distinct_evidence_bearing_events"],0)
            self.assertGreaterEqual(
                result["latest_morning_source_window_diagnostic_only"]
                      ["distinct_evidence_bearing_events"],20)
            self.assertTrue(result["round1_structural_source_and_selection_met"],result)
            self.assertGreaterEqual(result["latest_morning_selected_news_gate"]["unique_events"],20)
            self.assertFalse(result["gemini_called"])
            self.assertFalse(result["nonpublished_preview_generated"])
            self.assertFalse(result["actual_cutoff_capture_verified"])
            self.assertFalse(list(root.rglob("*.html")))
            self.assertFalse(list(root.rglob("*.epub")))

    def test_selected_count_alone_is_not_enough_if_outlets_or_subjects_cluster(self):
        issue={"edition":"morning","articles":[{
            "event_id":str(n),"editorial_tier":"main" if n<12 else "supplement",
            "topic":"macro","headline_summary":"Reported publisher source facts " * 3,
            "sources":[{"url":f"https://single-publisher.example/news/{n}"}]
        } for n in range(24)]}
        res=selected_story_gate(issue)
        self.assertEqual(res["gate"],"HOLD_SELECTED_STORY_VOLUME")
        self.assertIn("SELECTED_PUBLISHER_DIVERSITY_BELOW_4",res["blockers"])
        self.assertIn("SELECTED_TOPIC_DIVERSITY_BELOW_4",res["blockers"])

    def test_source_excerpt_is_required_for_each_selected_event(self):
        rows=[{"event_id":str(n),"editorial_tier":"main" if n<12 else "supplement",
                "topic":["macro","central_banks","geopolitics","asia"][n%4],
                "sources":[{"url":f"https://publisher{n%4}.example/item-{n}"}],
                "headline_summary":"Reporter attributed original facts " * 3} for n in range(24)]
        rows[0]["headline_summary"]="Short"
        res=selected_story_gate({"edition":"morning","articles":rows})
        self.assertIn("SELECTED_EVENT_INSUFFICIENT_SOURCE_EXCERPT",res["blockers"])

    def test_legacy_live_epub_auto_render_cannot_bypass_first_quality_gate(self):
        yml=Path(".github/workflows/live_morning_smoke_qa.yml").read_text(encoding="utf-8")
        triggers=yml.split("on:",1)[1].split("permissions:",1)[0]
        self.assertNotIn("push:",triggers)
        self.assertIn("workflow_dispatch:",triggers)
        self.assertIn("if: ${{ false }}",yml)
        self.assertIn("p2_integrated_qa.yml",yml)

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
