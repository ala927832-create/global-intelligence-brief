"""Regression guards for cutoff integrity, photo specificity and offline embedding."""
import datetime as dt
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from zoneinfo import ZoneInfo
from tools.gib_style_c_rc.live_html_qa import (
    bounds, filter_raw_before_ranking, filter_window, get_photo, PHOTOS, render
)

TPE=ZoneInfo("Asia/Taipei")
class ConsolidatedQATests(unittest.TestCase):
    def test_windows_do_not_overlap(self):
        start, end = bounds(dt.date(2026,10,28),"morning")
        self.assertEqual((start.hour,end.hour),(17,7))
        self.assertEqual((start.date(),end.date()),(dt.date(2026,10,27),dt.date(2026,10,28)))
        later, finish = bounds(dt.date(2026,10,28),"evening")
        self.assertEqual(later,end)
        self.assertEqual(finish.hour,17)

    def test_cutoff_filter_precedes_story_cap(self):
        start,end=bounds(dt.date(2026,10,28),"morning")
        outside=[{"title":f"Old {i}","published_at":"2026-10-27T15:00:00+08:00"} for i in range(30)]
        valid=[{"title":"Real window report","published_at":"2026-10-28T06:45:00+08:00"}]
        picked, rejected=filter_raw_before_ranking(outside+valid,start,end)
        self.assertEqual([x["title"] for x in picked],["Real window report"])
        self.assertEqual(len(rejected),30)

    def test_naive_and_future_timestamps_do_not_pass(self):
        start,end=bounds(dt.date(2026,10,28),"morning")
        picked,rejected=filter_raw_before_ranking([
            {"title":"Naive","published_at":"2026-10-28T04:00:00"},
            {"title":"Tomorrow","published_at":"2026-10-28T09:00:00+08:00"},
            {"title":"Eligible","published_at":"2026-10-27T21:00:00+08:00"}],start,end)
        self.assertEqual(len(picked),1)
        self.assertEqual(len(rejected),2)

    def test_evening_duplicate_without_new_source_is_excluded(self):
        start,end=bounds(dt.date(2026,10,28),"evening")
        prior={"articles":[{"event_id":"abc","sources":[{"url":"https://example.org/1"}]}]}
        issue={"edition":"evening","articles":[
            {"event_id":"abc","article_published_at":"2026-10-28T11:00:00+08:00",
             "sources":[{"url":"https://example.org/1"}]},
            {"event_id":"def","article_published_at":"2026-10-28T12:00:00+08:00",
             "sources":[{"url":"https://example.org/2"}]}]}
        picked, rejected=filter_window(issue,prior,start,end)
        self.assertEqual([x["event_id"] for x in picked],["def"])
        self.assertEqual(rejected[0]["reason"],"NO_NEW_SOURCE")

    def test_real_byte_embedding_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            row=PHOTOS[0]
            im=Image.new("RGB",(640,480),color=(25,85,100))
            im.save(folder/row["filename"],"JPEG")
            data, report=get_photo(row,folder,False)
            self.assertTrue(data.startswith("data:image/jpeg;base64,"))
            self.assertEqual(report["status"],"EMBEDDED_QA_RIGHTS_REVIEW_PENDING")
            self.assertEqual(len(report["original_sha256"]),64)

    def test_hero_image_must_match_story_topic(self):
        story={"event_id":"e1","title_original":"Refinery report","topic":"energy",
            "article_published_at":"2026-10-28T06:50:00+08:00",
            "headline_summary":"Source says refinery operations remain high.",
            "sources":[]}
        issue={"edition":"morning","report_date":"2026-10-28"}
        page,packet,coverage=render(issue,[story],{
            "data-centre":"data:image/jpeg;base64,DATACENTRE",
            "refinery":"data:image/jpeg;base64,REFINERY"},[],{
                "cutoff_tpe":"2026-10-28T07:00:00+08:00",
                "capture_utc":"2026-10-28T00:15:00+00:00"})
        hero=page.split('<section class="hero" id="front">',1)[1].split("</section>",1)[0]
        self.assertIn("REFINERY",hero)
        self.assertNotIn("DATACENTRE",hero)
        self.assertIn("Source says refinery operations remain high.",page)
        self.assertNotIn("Newsroom index item. Independent",page)

if __name__=="__main__": unittest.main()
