import datetime as dt,os,unittest
from unittest.mock import patch
from gib.collect import freenews
class DetailsTest(unittest.TestCase):
 def test_list_without_url_resolved_by_uuid_detail(self):
  config={'freenews_titles':['inflation'],'freenews_details_daily_cap':3}
  def lookup(url,params=None,headers=None,timeout=20):
   if url.endswith('/news'):
    return {'data':[{'uuid':'one','title':'Inflation official policy review','published_at':'2026-10-23T02:00:00Z','publisher':'Example Press'}]}
   return {'data':{'uuid':'one','title':'Inflation official policy review','url':'https://news.example.org/story',
                  'summary':'Reported summary.','published_at':'2026-10-23T02:00:00Z'}}
  with patch.dict(os.environ,{'FREENEWS_API_KEY':'FAKE_TEST_ONLY'}),patch('gib.collect.get_json',side_effect=lookup),patch('gib.collect.time.sleep'):
   err=[];result=freenews(config,dt.datetime(2026,10,23,3,0,tzinfo=dt.timezone.utc),err)
  self.assertEqual(len(result),1);self.assertEqual(result[0]['url'],'https://news.example.org/story')
  self.assertNotIn('body',result[0])
if __name__=='__main__':unittest.main()
