import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from gib.newsroom_v16 import canonical_issue,audit_issue
from gib.gemini_editor_v16 import audit_model_output,research_and_revise
from gib.publish_v16 import export

NOW=dt.datetime(2026,10,23,3,0,tzinfo=dt.timezone.utc)
def item(n,title,provider='news'):
    return {'title':title,'url':f'https://publisher{n%5}.example/story/{n}',
       'snippet':f'Publisher reports new {title}; independent confirmation pending.',
       'published_at':NOW.isoformat(), 'publisher':f'publisher{n%5}',
       'official':False,'provider':provider}
class TestNewsroom(unittest.TestCase):
    def setUp(self):
        self.raw=[item(i,t) for i,t in enumerate([
          'Global economy outlook and GDP update','Federal reserve rate policy meeting',
          'Taiwan technology chip policy shift','China trade tariff news',
          'Energy oil supply market data','Japan central bank yen decision',
          'International shipping port disruption','Artificial intelligence chip demand',
          'European economic growth inflation','Manufacturing steel industry update',
          'US Treasury bond yield developments','Global supply chain logistics changes'],1)]
        self.issue=canonical_issue(self.raw,'morning',NOW)
    def test_full_candidate_count(self):
        self.assertGreaterEqual(len(self.issue['articles']),8)
    def test_never_verify_a_snippet(self):
        self.assertTrue(all(c['verification']=='ATTRIBUTED_UNVERIFIED' for a in self.issue['articles'] for c in a['evidence']))
    def test_no_automatic_release(self):
        a=audit_issue(self.issue,require_full=True);self.assertFalse(a['passed']);self.assertIn('Requires explicit editorial approval',a['reasons'])
    def test_no_matched_evening_rebroadcast(self):
        night=canonical_issue(self.raw,'evening',NOW+dt.timedelta(hours=6),prior=self.issue)
        self.assertEqual(len(night['articles']),0)
    def test_missing_morning_must_flag(self):
        night=canonical_issue(self.raw,'evening',NOW+dt.timedelta(hours=6))
        self.assertFalse(night['source_health']['has_morning_comparison'])
    def test_sources_and_claims_bound(self):
        for article in self.issue['articles']:
            allowed={s['source_id'] for s in article['sources']}
            self.assertTrue(all(c['source_id'] in allowed for c in article['evidence']))
    def test_hallucinated_number_rejected(self):
        row=self.issue['articles'][0]
        data={'items':[{'event_id':row['event_id'],'source_ids':[row['sources'][0]['source_id']],
                        'why_it_matters':'Price surged 987654 percent'}]}
        edits,warnings=audit_model_output(data,self.issue)
        self.assertEqual(edits,[]);self.assertTrue(warnings)
    def test_unknown_source_rejected(self):
        row=self.issue['articles'][0]
        data={'items':[{'event_id':row['event_id'],'source_ids':['invented']}]}
        edits,_=audit_model_output(data,self.issue)
        self.assertFalse(edits)
    def test_gemini_is_opt_in(self):
        prev=os.environ.pop('ENABLE_GEMINI',None)
        try:self.assertEqual(research_and_revise(self.issue)['status'],'DISABLED')
        finally:
            if prev is not None:os.environ['ENABLE_GEMINI']=prev
    def test_html_epub_real_xhtml(self):
        with tempfile.TemporaryDirectory() as t:
            out=export(self.issue,[],t)
            self.assertTrue(Path(out['essential']['epub']).is_file())
            with ZipFile(out['deep']['epub']) as z:
                pages=[x for x in z.namelist() if x.endswith('.xhtml')]
                self.assertTrue(pages)
                for x in pages:etree.fromstring(z.read(x))
            html=Path(out['essential']['xhtml']).read_text(encoding='utf-8')
            self.assertIn('The World in Brief',html);self.assertIn('尚未通過發行審核',html)
    def test_published_dates_preserved(self):
        self.assertTrue(all(a.get('article_published_at') for a in self.issue['articles']))
    def test_edition_identity(self):self.assertEqual(self.issue['edition'],'morning')
if __name__=='__main__':unittest.main()
