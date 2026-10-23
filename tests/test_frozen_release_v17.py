"""The approved structure is a real regression contract, not a README promise."""
import copy, datetime as dt, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from lxml import etree
from gib.contract import locked_contract,expected_headings
from gib.newsroom_v16 import canonical_issue
from gib.publish_v16 import as_xhtml,export
from gib.evidence_review import review_official_excerpts,check_claim_lineage
from gib.qa_tracker import build_record,rollup,persist_record,day_ok

NOW=dt.datetime(2026,10,23,1,0,tzinfo=dt.timezone.utc)
class FrozenSpecTests(unittest.TestCase):
 def setUp(self):
  self.raw=[{'title':f'Global finance case number {i} with inflation update','url':f'https://p{i}.example.org/article/{i}',
   'publisher':f'p{i}', 'snippet':f'Reported event {i} pending validation', 'published_at':NOW.isoformat()} for i in range(12)]
  self.issue=canonical_issue(self.raw,'morning',NOW)
 def test_explicit_five_stages_six_sections_four_times(self):
  c=locked_contract();self.assertEqual(len(c['pipeline']),5);self.assertEqual(len(c['sections']),6)
  self.assertEqual([i['name'] for i in c['sections']],['Executive Brief','The World in Brief','Essential Analysis','Deep Research','What Changed & What to Watch','Sources & Evidence'])
  self.assertEqual(c['schedule']['global_morning'],'07:30');self.assertEqual(c['schedule']['global_evening'],'17:30')
 def test_contract_mutation_blocked(self):
  from gib import contract
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'locked.json';p.write_text('"tampered"')
   with patch.object(contract,'CONTRACT_PATH',p):
    with self.assertRaises(RuntimeError):locked_contract()
 def test_xhtml_all_six_sections_in_approved_order_both_depths(self):
  for level in ('essential','deep'):
   html=as_xhtml(self.issue,[],level)
   doc=etree.fromstring(html.encode('utf-8'))
   headers=[''.join(x.itertext()) for x in doc.xpath('//*[contains(@class,"section-number")]')]
   self.assertEqual(headers,expected_headings())
   self.assertIn('QA／非正式刊物',html)
 def test_no_publication_without_manual_gate(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(PermissionError):export(self.issue,[],t,qa_only=False)
 def test_only_excerpt_match_not_truth_or_auto_approval(self):
  src={'source_id':'abc','url':'https://www.bls.gov/test','kind':'OFFICIAL_FEED'}
  i=copy.deepcopy(self.issue)
  i['articles']=[{'sources':[src],'evidence':[{'claim_id':'c1','source_id':'abc','support_excerpt':'This official example paragraph is deliberately long enough for an exact location match.'}]}]
  text='This official example paragraph is deliberately long enough for an exact location match.'
  r=review_official_excerpts(i,fetcher=lambda url:{'text':text,'sha256':'fakehash','retrieved_at':NOW.isoformat()})
  self.assertEqual(r[0]['status'],'EXCERPT_MATCH')
  self.assertNotEqual(i['articles'][0]['evidence'][0]['verification'],'VERIFIED')
 def test_unattested_verified_claim_rejected(self):
  i=copy.deepcopy(self.issue)
  i['articles'][0]['evidence'][0]['verification']='VERIFIED'
  self.assertTrue(check_claim_lineage(i))
 def test_fixture_does_not_count_as_real_day(self):
  record=build_record(self.issue,{'status':'REVISED_DRAFT_PENDING_REVIEW'},True,True,live_source=False,fixture=True)
  self.assertFalse(record['newsroom_quality_passed']);self.assertEqual(record['origin'],'FIXTURE_OR_OFFLINE')
 def test_ten_days_cannot_be_forged_from_one_day(self):
  with tempfile.TemporaryDirectory() as t:
   x=build_record(self.issue,{},False,False,live_source=False,fixture=True)
   persist_record(x,t)
   status=rollup(t,device_signoff=True,owner_release_approval=True)
   self.assertEqual(status['completed_trading_days'],0);self.assertFalse(status['production_ready'])
 def test_exchange_holiday_excluded(self):
  self.assertFalse(day_ok('2026-12-25'));self.assertTrue(day_ok('2026-10-23'))

if __name__=='__main__':unittest.main()
