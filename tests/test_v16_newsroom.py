import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from gib.newsroom_v16 import canonical_issue,audit_issue
from gib.gemini_editor_v16 import audit_model_output,research_and_revise
from gib.publish_v16 import export,as_xhtml

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
    def test_invalid_top_urls_do_not_consume_news_slots(self):
        countries=['Australia','Brazil','Chile','Denmark','Egypt','Finland','Greece','Hungary']
        bad=[]
        for i,country in enumerate(countries):
            entry=item(200+i,f'{country} central bank policy rate decision with inflation update')
            entry['url']=f'http://publisher-invalid.example/{i}' # QA requires HTTPS
            entry['official']=True
            bad.append(entry)
        issue=canonical_issue(bad+self.raw,'morning',NOW)
        self.assertGreaterEqual(len(issue['articles']),8)
        self.assertTrue(all(a['sources'][0]['url'].startswith('https://') for a in issue['articles']))

    def test_one_download_offline_navigation_and_qa_alias(self):
        # The Deep book includes all brief headlines, analyses and source
        # summaries; it does NOT promise offline access to external publishers.
        a=self.issue['articles'][0]
        key=a['event_id']
        x=as_xhtml(self.issue,[],level='deep')
        self.assertIn('id="reading-index"',x)
        self.assertIn('href="#analysis-'+key+'"',x)
        self.assertIn('id="analysis-'+key+'"',x)
        self.assertIn('id="brief-'+key+'"',x)
        self.assertIn('href="#sources"',x)
        with tempfile.TemporaryDirectory() as t:
            exported=export(self.issue,[],t)
            self.assertEqual(exported['offline_complete']['epub'],exported['deep']['epub'])
            from scripts.check_offline_package import inspect
            audit=inspect(exported['offline_complete']['epub'])
            self.assertTrue(audit['offline_in_book_navigation'],audit['issues'])
            self.assertGreater(audit['local_links'],10)
            self.assertEqual(audit['resource_dependencies_on_network'],0)
            with ZipFile(exported['offline_complete']['epub']) as z:
                chapters=' '.join(z.read(p).decode('utf-8') for p in z.namelist() if p.endswith('.xhtml'))
                self.assertIn('本書閱讀路線',chapters)
                self.assertIn('本書深入閱讀',chapters)

    def test_deep_draft_is_internal_and_not_approved(self):
        event=self.issue['articles'][0]
        edit={'event_id':event['event_id'],'source_ids':[event['sources'][0]['source_id']],
              'sections':{'background':'全球經濟報導需要比較官方公布的期間與口徑；僅憑標題不足以識別原因。'*4,
                          'transmission':'理解通膨如何可能影響利率與實體經濟時，必須同時追蹤不同指標和替代解釋。'*4,
                          'limitations':'目前新聞索引無法單獨證實這些因果關係。'*4}}
        deep=as_xhtml(self.issue,[edit],level='deep')
        self.assertIn('RESEARCH WORKING DRAFT',deep)
        self.assertIn('id="research-'+event['event_id']+'"',deep)
        self.assertIn('待驗證',deep)
        self.assertFalse(audit_issue(self.issue,True)['passed'])

    def test_published_dates_preserved(self):
        self.assertTrue(all(a.get('article_published_at') for a in self.issue['articles']))
    def test_edition_identity(self):self.assertEqual(self.issue['edition'],'morning')
if __name__=='__main__':unittest.main()
