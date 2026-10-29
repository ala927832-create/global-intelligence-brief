"""Six-slot, holiday/weekend, actual time, provenance and automatic stop QA."""
from __future__ import annotations
import datetime as dt
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from email.utils import format_datetime
from html import escape

from qa.p2_three_day_snapshot import (
    ALLOWED_DATES, SCHEDULES, SCHEMA, TZ, UTC,
    plan, validate_plan, slot_window, compare_seen_indices,
    execute_capture, disable_if_expired, artifact_name, three_day_rollup
)

class ThreeDayQA(unittest.TestCase):
    def ts(self,date,time):
        return dt.datetime.fromisoformat(date+"T"+time+"+08:00").astimezone(UTC)

    def test_workflow_can_import_source_modules_and_only_self_disable(self):
        workflow=Path(".github/workflows/gib_p2_three_day_source_capture.yml").read_text(encoding="utf-8")
        guard=workflow.split("  guard:",1)[1].split("  capture:",1)[0]
        self.assertIn("Install source QA import dependencies before guard",guard)
        self.assertIn("pip install 'requests>=2.32,<3'",guard)
        self.assertIn("GIB_SCHEDULE_CRON: ",guard)
        self.assertIn("github.event.schedule",guard)
        self.assertIn("qa/p2_three_day_snapshot.py plan",guard)
        finalizer=workflow.split("  finalizer:",1)[1]
        self.assertIn("actions: write",finalizer)
        self.assertIn("qa/p2_three_day_snapshot.py disable",finalizer)
        self.assertNotIn("workflow_dispatch:",workflow)
        capture_steps=workflow.split("  capture:",1)[1].split("  finalizer:",1)[0]
        self.assertNotIn("ENABLE_GEMINI:",capture_steps)
        self.assertNotIn("python run_newsroom_v16.py",capture_steps)
        self.assertNotIn("LINE_CHANNEL_ACCESS_TOKEN",capture_steps)

    def test_only_six_workday_slots_authorized(self):
        self.assertEqual(ALLOWED_DATES,{"2026-10-29","2026-10-30","2026-11-02"})
        for day in sorted(ALLOWED_DATES):
            for cron,slot in SCHEDULES.items():
                hour="07:35" if slot=="morning" else "17:35"
                p=plan(self.ts(day,hour),cron)
                self.assertTrue(p["active"],(day,slot))
                self.assertTrue(p["at_cutoff"])
                self.assertEqual(p["slot"],slot)
                self.assertFalse(p["release_approved"])
        for day in ("2026-10-28","2026-10-31","2026-11-01","2026-11-03"):
            p=plan(self.ts(day,"07:35"),"30 23 * * 0-4")
            self.assertFalse(p["active"])
            with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_DATE_OR_SLOT"):
                validate_plan(self.ts(day,"07:35"),"30 23 * * 0-4")
        self.assertFalse(plan(self.ts("2026-10-29","07:35"),"bad cron")["active"])

    def test_local_cutoffs_are_07_30_17_30_without_overlap(self):
        for day in ALLOWED_DATES:
            start,end=slot_window(day,"morning")
            nextstart,nextend=slot_window(day,"evening")
            self.assertEqual((end.hour,end.minute),(7,30))
            self.assertEqual((nextend.hour,nextend.minute),(17,30))
            self.assertEqual(start.hour,17)
            self.assertEqual(start.minute,30)
            self.assertEqual(end,nextstart)

    def test_delayed_capture_cannot_claim_ontime(self):
        p=plan(self.ts("2026-10-30","09:05"),"30 23 * * 0-4")
        self.assertTrue(p["active"])
        self.assertFalse(p["at_cutoff"])
        self.assertGreater(p["start_lag_minutes"],45)

    def test_fixture_save_genuine_index_metadata_and_no_publish(self):
        now=self.ts("2026-10-29","07:35")
        def feed(url):
            sid=hashlib.sha256(url.encode()).hexdigest()[:16]
            stamp=format_datetime(now-dt.timedelta(minutes=30))
            return ('<rss><channel><item><title>Policy news '+escape(sid)+
                    '</title><link>https://publisher.example/report/'+escape(sid)+
                    '</link><pubDate>'+stamp+
                    '</pubDate><description>Only feed-index summary</description></item></channel></rss>').encode()
        add={"official_rss":lambda errors:[],
             "gdelt":lambda errors:[],
             "freenews":lambda errors:[]}
        with tempfile.TemporaryDirectory() as folder:
            snap,report=execute_capture(now=now,cron="30 23 * * 0-4",
                                         opml_fetcher=feed,extra_fetchers=add,
                                         out=folder)
            self.assertEqual(snap["schema"],SCHEMA)
            self.assertEqual(snap["time_gate"],"AT_CUTOFF_CAPTURE_STARTED")
            self.assertEqual(snap["slot"],"morning")
            self.assertEqual(snap["source_health"]["configured_sources"],24)
            self.assertEqual(snap["source_window_article_count"],24)
            self.assertEqual(snap["publication_status"],"OFF_INTERNAL_QA_ONLY")
            self.assertFalse(snap["content_fact_checked"])
            self.assertFalse(snap["line_sent"])
            self.assertFalse(snap["gemini_used"])
            self.assertFalse(snap["release_approved"])
            self.assertFalse(snap["p2_editorial_approved"])
            self.assertEqual(snap["round1_source_selection_quality"]["scope"],
                             "MORNING_ONLY_G0_G1_READ_ONLY")
            self.assertFalse(snap["round1_source_selection_quality"]["structural_pass"])
            self.assertFalse(snap["round1_source_selection_quality"]["p2_editorial_pass"])
            self.assertEqual(report["original_opml_source_gate"],"PASS_DIRECT_RSS_DISCOVERY")
            self.assertTrue((Path(folder)/"snapshot_window.json").is_file())
            self.assertEqual(
                json.loads((Path(folder)/"source_index_all.json").read_text(encoding="utf-8"))[0]["verification_status"],
                "INDEX_ONLY_NOT_FACT_CHECKED")

    def test_approved_cutoff_archive_records_g0_and_g1_with_real_feed_fields(self):
        now=self.ts("2026-10-30","07:35")
        from qa.p2_three_day_snapshot import validate_config
        feed_config=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))
        configured=validate_config(feed_config)
        feed_index={feed["url"]:idx for idx,feed in enumerate(configured)}
        themes=["global war","central bank","china asia","semiconductor technology",
                "energy oil","GDP inflation","merger earnings"]
        def feed(url):
            idx=feed_index[url]
            unique=hashlib.sha256(str(idx).encode()).hexdigest()
            stamp=format_datetime(now-dt.timedelta(minutes=25))
            title=themes[idx%len(themes)]+" independently reported "+unique
            synopsis=("Source-attributed original event "+str(idx)+
                      " includes observed details and described developments. "*3)
            return ('<rss><channel><item><title>'+escape(title)+
                    '</title><link>https://publisher'+str(idx%6)+'.example/story/'+str(idx)+
                    '</link><pubDate>'+stamp+
                    '</pubDate><description>'+escape(synopsis)+
                    '</description></item></channel></rss>').encode()
        providers={"official_rss":lambda errors:[],
                   "gdelt":lambda errors:[],
                   "freenews":lambda errors:[]}
        with tempfile.TemporaryDirectory() as folder:
            snap,summary=execute_capture(now=now,cron="30 23 * * 0-4",
                                         opml_fetcher=feed,extra_fetchers=providers,
                                         out=folder)
            r1=snap["round1_source_selection_quality"]
            self.assertTrue(r1["time_verified"])
            self.assertTrue(r1["structural_pass"],r1)
            self.assertEqual(r1["g1"]["main_news"],12)
            self.assertEqual(r1["g1"]["supplementary_news"],12)
            self.assertGreaterEqual(r1["g1"]["selected_primary_publisher_domains"],4)
            self.assertGreaterEqual(r1["g1"]["selected_editorial_topics"],4)
            self.assertFalse(r1["p2_editorial_pass"])
            self.assertEqual(summary["round1_source_selection_quality"]["g1"]["unique_events"],24)
            self.assertFalse(snap["gemini_used"])
            self.assertFalse(snap["release_approved"])
            self.assertFalse(list(Path(folder).rglob("*.html")))
            self.assertFalse(list(Path(folder).rglob("*.epub")))

    def test_evening_delta_without_morning_is_hold(self):
        morning=[{"url":"https://example.com/original","title":"First","snippet":"Source text"}]
        evening=[{"url":"https://example.com/original","title":"Changed","snippet":"Source text"},
                 {"url":"https://example.com/second","title":"New","snippet":"Source text"}]
        compare=compare_seen_indices(morning,evening)
        self.assertEqual(compare["shared_original_urls"],1)
        self.assertEqual(compare["newly_seen_original_urls"],["https://example.com/second"])
        self.assertEqual(compare["changed_index_text_original_urls"],["https://example.com/original"])
        self.assertEqual(compare["material_news_updates_verified"],0)
        self.assertEqual(compare["independent_claims_verified"],0)

    def test_terminal_evening_auto_disables_only_approved_workflow(self):
        calls=[]
        result=disable_if_expired(
            now=self.ts("2026-11-02","17:36"),
            cron="30 9 * * 1-5",stopper=lambda:calls.append("disable"))
        self.assertTrue(result["disabled"])
        self.assertEqual(calls,["disable"])
        pre=disable_if_expired(
            now=self.ts("2026-10-30","17:31"),
            cron="30 9 * * 1-5",stopper=lambda:calls.append("should not"))
        self.assertFalse(pre["disabled"])
        self.assertEqual(calls,["disable"])
        fallback=disable_if_expired(
            now=self.ts("2026-11-03","07:35"),
            cron="30 23 * * 0-4",stopper=lambda:calls.append("fallback"))
        self.assertTrue(fallback["disabled"])
        self.assertEqual(calls,["disable","fallback"])

    def test_rollup_requires_six_evidence_slots_no_fake_completion(self):
        sample={"schema":SCHEMA,"date_tpe":"2026-11-02","slot":"evening",
                "time_gate":"AT_CUTOFF_CAPTURE_STARTED",
                "observed_start_utc":self.ts("2026-11-02","17:31").isoformat(),
                "source_window_article_count":14,
                "index_delta":{"material_news_updates_verified":0}}
        with patch("qa.p2_three_day_snapshot._read_artifact",
                   return_value=(None,"NOT_CAPTURED_YET")):
            r=three_day_rollup(sample)
        self.assertEqual(r["approved_snapshots"],6)
        self.assertEqual(r["observed_snapshots"],1)
        self.assertEqual(r["slots"][-1]["slot"],"evening")
        self.assertFalse(r["real_global_news_completeness_verified"])
        self.assertFalse(r["editorial_p2_approved"])
        self.assertEqual(r["publication_status"],"OFF")

if __name__=="__main__":
    unittest.main()
