"""P2 paired QA exercises the actual V1.6+Style C exports with fake RSS only.

Fixture test proves integration wiring, NOT genuine source retrieval or editorial approval.
GitHub main-branch QA uses real public publisher RSS separately.
"""
from __future__ import annotations
import datetime as dt
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import qa.p2_integrated_batch as batch
import run_newsroom_v16 as newsroom


class IntegratedP2BatchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pandoc"),"Pandoc not installed: CLI CI performs real EPUB QA")
    def test_same_snapshot_real_canonical_issue_style_c_and_dual_epub_two_editions(self):
        now=dt.datetime(2026,10,28,4,0,tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"config").mkdir(parents=True)
            (root/"config/sources.json").write_text(
                (batch.ROOT/"config/sources.json").read_text(encoding="utf-8"),
                encoding="utf-8")
            groups=["macro","geopolitics","technology","energy","asia","corporates"]
            titles=[
                "global inflation policy and central bank outlook",
                "international tariff and trade sanction policy",
                "semiconductor chip AI technology investment",
                "energy petroleum electricity supply outlook",
                "japan china currency and yen market",
                "corporate earnings merger and acquisition deal"
            ]
            feeds=json.loads(batch.CONFIG.read_text(encoding="utf-8"))["feeds"]
            def fetch(url):
                source=next(x for x in feeds if x["url"]==url)
                index=feeds.index(source)
                topic=titles[index%len(titles)]
                items=[]
                for edition,pub in (
                    ("morning","Mon, 26 Oct 2026 20:00:00 +0000"),
                    ("evening","Tue, 27 Oct 2026 06:00:00 +0000")
                ):
                    items.append(
                        "<item><title>"+topic+" item "+source["id"]+" "+edition+
                        "</title><link>https://news.example/"+source["id"]+"/"+edition+
                        "</link><pubDate>"+pub+"</pubDate>"
                        "<description>Attributed source headline only, no verified reporting.</description></item>"
                    )
                return ("<rss version=\"2.0\"><channel>"+"".join(items)+"</channel></rss>").encode()
            with patch.object(batch,"OUTPUT",root/"p2_reports"), \
                 patch.object(newsroom,"ROOT",root):
                report=batch.run_batch(now=now,gemini=False,source_fetcher=fetch)
            self.assertFalse(report["release_approved"])
            self.assertFalse(report["p2_content_accepted"])
            self.assertEqual(report["source_configured"],24)
            self.assertEqual(report["source_gate"],"PASS_DIRECT_RSS_DISCOVERY")
            self.assertTrue(report["source_index_sha256"])
            self.assertEqual(set(report["editions"]),{"morning","evening"})
            self.assertEqual(report["report_date_tpe"],"2026-10-27")
            for name,episode in report["editions"].items():
                issue=json.loads(Path(episode["issue_json"]).read_text(encoding="utf-8"))
                self.assertEqual(issue["edition"],name)
                self.assertEqual(issue["report_date"],"2026-10-27")
                self.assertFalse(issue["release_approved"])
                self.assertGreaterEqual(episode["article_count"],1)
                self.assertEqual(episode["sources_with_identified_provenance"],episode["article_count"])
                self.assertEqual(episode["independently_verified_claim_count"],0)
                self.assertEqual(episode["gemini_status"],"NOT_REQUESTED")
                self.assertTrue(episode["release_hold_reasons"])
                self.assertTrue(Path(episode["essential_epub"]).is_file())
                self.assertTrue(Path(episode["deep_epub"]).is_file())
                html=Path(episode["style_c_html"]).read_text(encoding="utf-8")
                self.assertIn("GLOBAL INTELLIGENCE BRIEF",html)
                self.assertIn("QA HOLD",html)
                self.assertIn("SOURCE CANDIDATE",html)
                self.assertNotIn("EDITOR_APPROVED",html)
                for heading in ("01 Executive Brief", "02 The World in Brief",
                                "03 Essential Analysis", "04 Deep Research",
                                "05 What Changed", "06 Sources"):
                    self.assertIn(heading,html)
                self.assertIn("What the source index reports",html)
                self.assertIn("HOLD: no 2–3 independently evidenced",html)
                self.assertNotIn("http://news.example",html)
                align=json.loads((Path(episode["issue_json"]).parent/"style_c_alignment.json").read_text(encoding="utf-8"))
                self.assertEqual(align["canonical_issue_sha256"],episode["issue_sha256"])
                self.assertEqual(align["style_c_issue_sha256"],episode["issue_sha256"])
                self.assertFalse(align["release_approved"])
            evening=json.loads(Path(report["editions"]["evening"]["issue_json"]).read_text(encoding="utf-8"))
            self.assertTrue(evening["source_health"]["has_morning_comparison"])
            self.assertEqual(evening["editorial_delta_status"],"CANDIDATES_ONLY_MATERIAL_CHANGE_UNVERIFIED")

    def test_backfill_does_not_accept_future_unfinished_edition(self):
        now=dt.datetime(2026,10,28,4,0,tzinfo=dt.timezone.utc)
        self.assertEqual(batch.completed_report_date(now),dt.date(2026,10,27))
        with self.assertRaisesRegex(ValueError,"P2_DATE_IS_NOT_A_COMPLETED"):
            batch.run_batch(report_date="2026-10-28",now=now,source_fetcher=lambda url:b"")

    def test_style_c_escapes_unverified_ai_prose_without_changing_layout(self):
        from tools.gib_style_c_rc.live_html_qa import render
        story={
            "event_id":"e0001","title_original":"Major global policy",
            "headline_summary":"Attributed context, not verified",
            "article_published_at":"2026-10-27T06:00:00+00:00",
            "topic":"geopolitics","sources":[{"url":"https://world.example/story",
                                               "source_id":"s1","retrieval_status":"INDEX_ONLY",
                                               "publisher":"World Example"}]
        }
        edits=[{"event_id":"e0001","brief_zh":"未核實的新聞摘要",
                "sections":{"background":"<script>alert(1)</script> 為來源待核實背景",
                            "alternative":"反例與不確定性"}}]
        html,packet,coverage=render({"report_date":"2026-10-27","edition":"morning"},
                                    [story],{},[],{"cutoff_tpe":"2026-10-27 07:00",
                                                     "capture_utc":"2026-10-28 04:00"},edits)
        self.assertIn("AI EDITORIAL DRAFT",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>alert(1)</script>",html)
        self.assertIn("反例與不確定性",html)
        self.assertIn("QA HOLD",html)
        self.assertEqual(len(packet),1)
        self.assertTrue(coverage)


if __name__=="__main__":
    unittest.main()
