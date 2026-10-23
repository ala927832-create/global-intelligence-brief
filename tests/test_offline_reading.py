import datetime as dt
import unittest
from lxml import etree
from gib.newsroom_v16 import canonical_issue
from gib.publish_v16 import as_xhtml

class OfflineReadingTest(unittest.TestCase):
    def test_one_file_contains_all_six_chapters_and_internal_targets(self):
        now=dt.datetime(2026,10,23,4,tzinfo=dt.timezone.utc)
        items=[{'title':f'Official sector {i} policy news headline',
                'url':f'https://sample{i}.example/story',
                'snippet':'Illustrative source statement; unverified.',
                'published_at':now.isoformat(),'publisher':f'Sample {i}'} for i in range(8)]
        issue=canonical_issue(items,'morning',now)
        raw=as_xhtml(issue,level='deep').encode('utf-8')
        root=etree.fromstring(raw)
        nodes=root.xpath('//*[@id]')
        ids=[node.get('id') for node in nodes]
        self.assertEqual(len(ids),len(set(ids)), 'duplicated ids: '+str(sorted({x for x in ids if ids.count(x)>1})))
        targets=[x[1:] for x in root.xpath('//@href') if x.startswith('#')]
        self.assertTrue(targets)
        self.assertTrue(all(t in ids for t in targets),set(targets)-set(ids))
        for key in ('executive','world','analysis','deep-research','watch','sources','reading-index'):
            self.assertIn(key,ids)
        self.assertIn('離線',raw.decode('utf-8'))

if __name__=='__main__':unittest.main()
