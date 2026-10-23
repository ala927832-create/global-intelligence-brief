import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from gib.collect import timestamp
from gib.editorial import cluster,rank,label_updates,next_seen
from gib.zinc_bridge import extract_public_watch
from main import run,ROOT

NOW=dt.datetime(2026,10,23,0,0,tzinfo=dt.timezone.utc)


def example_articles():
    return [
      {'title':'Sample central bank policy meeting announced','url':'https://example.org/policy?utm_source=x',
       'published_at':'2026-10-22T18:00:00+00:00','publisher':'Sample Publisher','snippet':'Illustrative only',
       'official':False,'provider':'fixture'},
      {'title':'Sample central bank policy meeting announced','url':'https://other.org/policy',
       'published_at':'2026-10-22T19:00:00+00:00','publisher':'Other Publisher','snippet':'Illustrative only',
       'official':False,'provider':'fixture'},
      {'title':'Sample industrial supply report published','url':'https://example.org/supply',
       'published_at':'2026-10-22T20:00:00+00:00','publisher':'Sample Publisher','snippet':'Illustrative only',
       'official':False,'provider':'fixture'},
      {'title':'Future dated fake article','url':'https://example.org/future',
       'published_at':'2028-02-01T01:00:00Z','publisher':'Fixture','provider':'fixture'}
    ]

class TestPipeline(unittest.TestCase):
    def test_normalize_and_cluster(self):
        got=cluster(example_articles(),NOW)
        self.assertEqual(len(got),2)
        self.assertEqual(len(got[0]['publishers']),2)
        self.assertNotIn('utm_source',got[0]['url'])
    def test_same_oil_event_headline_variants_cluster(self):
        raw=[
            {'title':'Oil Prices Rise as Supply Concerns Linger amid Middle East Attacks',
             'url':'https://one.example/a','published_at':NOW.isoformat(),
             'publisher':'First Outlet','snippet':'Unverified title only'},
            {'title':'Oil prices rise as supply concerns linger amid Houthi attacks on Saudi Arabia',
             'url':'https://two.example/b','published_at':NOW.isoformat(),
             'publisher':'Second Outlet','snippet':'Unverified title only'}]
        got=cluster(raw,NOW)
        self.assertEqual(len(got),1)
        self.assertEqual(len(got[0]['related_urls']),2)

    def test_evening_non_replay(self):
        articles=rank(cluster(example_articles(),NOW),{})
        seen=next_seen([],articles,NOW)
        self.assertEqual(label_updates(articles,seen,'evening',NOW),[])
    def test_genuine_new_official_notice_is_not_filtered(self):
        previous={'key':'old','title':'Official monetary policy statement',
                  'last_seen':NOW.isoformat(),'source_count':1,'urls':['https://bank.example/old']}
        a={'title':'Official monetary policy statement','url':'https://bank.example/new',
           'published_at':(NOW+dt.timedelta(hours=2)).isoformat(),
           'publishers':['Central Bank'],'official':True,'related_urls':['https://bank.example/new']}
        selected=label_updates([a],[previous],'evening',NOW+dt.timedelta(hours=3))
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['status'],'NEW_OFFICIAL_NOTICE')
    def test_schedule_reserved_but_disabled_until_editorial_approval(self):
        content=(ROOT/'.github'/'workflows'/'morning_evening.yml').read_text(encoding='utf-8')
        self.assertIn('07:30 Asia/Taipei',content)
        self.assertIn('17:30 Asia/Taipei',content)
        self.assertIn('workflow_dispatch:',content)
        self.assertNotIn('  schedule:',content)
        self.assertNotIn('LINE_CHANNEL_ACCESS_TOKEN',content)
    def test_zinc_private_isolation(self):
        snap={'run_time':NOW.isoformat(),'procurement':{'inventory':12345,'secret':'DO_NOT_LEAK'},
              'decision_book':{'markets':{'lme_zinc':{'direction':'BEAR','data_gate':'PASS_CLOSE_ONLY','as_of':'2026-10-22'}}},
              'market_research':{'events':{'upcoming':[{'title':'Illustrative policy meeting','date':'2026-10-28','status':'SCHEDULED_NOT_RELEASED','source_url':'https://example.org'}]}}}
        extracted=extract_public_watch(snap,NOW)
        self.assertEqual(extracted['status'],'VALID')
        self.assertNotIn('DO_NOT_LEAK',json.dumps(extracted))
        self.assertEqual(len(extracted['watch']),1)
    def test_old_zinc_rejected(self):
        self.assertEqual(extract_public_watch({'run_time':'2025-01-01T00:00:00Z'},NOW)['status'],'STALE')
    def test_timezone(self):
        self.assertEqual(timestamp('2026-10-22T22:15:00Z'),'2026-10-22T22:15:00+00:00')
    def test_offline_integrated_morning_evening(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            (root/'config').mkdir()
            (root/'config'/'sources.json').write_text((ROOT/'config'/'sources.json').read_text(encoding='utf-8'),encoding='utf-8')
            fixture=root/'offline.json'
            fixture.write_text(json.dumps({'articles':example_articles(),'zinc':{'status':'UNAVAILABLE'}},ensure_ascii=False),encoding='utf-8')
            x=run('morning',root,NOW,fixture)
            self.assertEqual(len(x['events']),2)
            y=run('evening',root,NOW+dt.timedelta(hours=10),fixture)
            self.assertEqual(len(y['events']),0)
            page=(root/'docs'/'archive'/'2026-10-23'/'evening-essential.html').read_text(encoding='utf-8')
            self.assertIn('不重複',page)
            self.assertTrue((root/'reports'/'2026-10-23'/'morning-deep.md').exists())
            self.assertFalse((root/'data'/'latest_snapshot.json').exists())

if __name__=='__main__':unittest.main()
