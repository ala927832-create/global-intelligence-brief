import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from live_html_qa import bounds,filter_window,render
from zoneinfo import ZoneInfo
class BridgeTests(unittest.TestCase):
 def test_cutoff_windows(self):
  d=dt.date(2026,10,27)
  a,b=bounds(d,"morning");self.assertEqual((a.hour,b.hour),(17,7))
  a,b=bounds(d,"evening");self.assertEqual((a.hour,b.hour),(7,17))
 def test_evening_requires_new_source(self):
  def item(k,t,url):return {"event_id":k,"article_published_at":t,"sources":[{"url":url}],"title_original":k}
  morn={"articles":[item("old","2026-10-26T23:10:00+00:00","https://source.invalid/old")]}
  eve={"edition":"evening","articles":[item("old","2026-10-27T03:00:00+00:00","https://source.invalid/old"),item("new","2026-10-27T04:00:00+00:00","https://source.invalid/new")]}
  r,exc=filter_window(eve,morn,*bounds(dt.date(2026,10,27),"evening"))
  self.assertEqual([x["event_id"] for x in r],["new"])
  self.assertEqual(exc[0]["reason"],"NO_NEW_SOURCE")
 def test_offline_html_no_fake_photos(self):
  issue={"report_date":"2026-10-27","edition":"morning"}
  gate={"cutoff_tpe":"2026-10-27T07:00:00+08:00","capture_utc":"2026-10-26T23:31:00+00:00"}
  page,pack,counts=render(issue,[],{},[],gate)
  self.assertIn("QA HOLD",page)
  self.assertNotIn('src="https://',page)
  self.assertEqual(page.lower().count("<!doctype html>"),1)
if __name__=="__main__":unittest.main()
