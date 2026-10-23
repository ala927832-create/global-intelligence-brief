"""Regression quality controls for curated evidence sample. No internet usage."""
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from gib.editorial_rebuild import validate_packet, make_html, export_packet, ROOT, count_cjk
from gib.quality_gate import report_checks

SAMPLE=ROOT/'samples/official_research_2026-10-23.json'
class TestEditorialRebuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkt=json.loads(SAMPLE.read_text(encoding='utf-8'))
        cls.tempdir=tempfile.TemporaryDirectory()
        cls.qa_root=Path(cls.tempdir.name)
        shutil.copytree(ROOT/'assets'/'editorial',cls.qa_root/'assets'/'editorial')
        cls.outputs=export_packet(cls.pkt,cls.qa_root,edition='morning')
    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()
    def test_sources_dates_and_citations(self):
        self.assertTrue(validate_packet(self.pkt))
        self.assertEqual(len(self.pkt['stories']),4)
        self.assertGreaterEqual(len(self.pkt['sources']),5)
        for story in self.pkt['stories']:
            self.assertTrue(story['source_ids'])
    def test_editorial_html_has_semantic_components(self):
        s=make_html(self.pkt,'morning','deep',ROOT)
        for tag in ['issue-opening','keybox','watchbox','topic-strip','research-section','source-list']:
            self.assertIn(tag,s)
        self.assertGreaterEqual(count_cjk(s),7500)
    def test_real_epub_has_images_and_cites(self):
        file=self.qa_root/'reports/2026-10-23/morning-deep.epub'
        self.assertTrue(file.is_file())
        with zipfile.ZipFile(file) as z:
            self.assertGreaterEqual(len([n for n in z.namelist() if n.endswith('.png')]),3)
            text='\n'.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xhtml'))
            self.assertIn('imf.org',text)
            self.assertIn('bls.gov',text)
            self.assertIn('evidence-figure',text)
    def test_fail_closed_with_invalid_sources(self):
        bad=json.loads(json.dumps(self.pkt,ensure_ascii=False))
        bad['stories'][0]['source_ids']=['FAKE']
        with self.assertRaises(ValueError): validate_packet(bad)
    def test_quality_gate(self):
        q=report_checks(self.pkt,self.outputs,self.qa_root)
        self.assertTrue(q['all_passed'],str([x for x in q['checks'] if not x['passed']]))
if __name__=='__main__':unittest.main()
