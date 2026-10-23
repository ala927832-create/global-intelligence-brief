"""BOOX color EPUB regression tests; no news network/API calls."""
import datetime as dt
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from gib.epub import EPUB_CSS, render_epub, validate_epub
from main import run, ROOT

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 23, 0, 0, tzinfo=UTC)

class TestBOOXEPUB(unittest.TestCase):
    def test_epub3_color_cover_toc_and_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            md = d/'story.md'
            md.write_text('# 全域晨報\n\n> 排版測試，非真實新聞。\n\n## 今日焦點\n\n**重要：** 需核對來源。\n\n## 深度研究\n\n研究內容。',encoding='utf-8')
            epub = d/'book.epub'
            render_epub(md, epub, 'morning', 'deep', '2026-10-23')
            validate_epub(epub)
            with zipfile.ZipFile(epub) as z:
                fn = z.namelist()
                css = '\n'.join(z.read(n).decode('utf-8') for n in fn if n.endswith('.css'))
                self.assertIn('#203D58',css)
                self.assertIn('#427A76',css)
                self.assertIn('page-break-before',css)
                self.assertNotIn('http://',css)
                nav = '\n'.join(z.read(n).decode('utf-8') for n in fn if n.endswith('nav.xhtml'))
                self.assertIn('今日焦點',nav)
                self.assertIn('深度研究',nav)
                cover = [n for n in fn if n.endswith('.png')]
                self.assertTrue(cover)
                opfs = [n for n in fn if n.endswith('.opf')]
                self.assertEqual(len(opfs), 1)
                self.assertIn('zh-TW',z.read(opfs[0]).decode('utf-8'))
                from PIL import Image
                import io
                cover_image = Image.open(io.BytesIO(z.read(cover[0])))
                self.assertEqual(cover_image.size, (900,1200))

    def test_four_public_epub_downloads_from_one_morning_evening_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'config').mkdir()
            (root/'config'/'sources.json').write_text((ROOT/'config'/'sources.json').read_text(encoding='utf-8'),encoding='utf-8')
            fixture=root/'fixture.json'
            fixture.write_text(json.dumps({'articles':[
                {'title':'【示範，不是真實新聞】財經消息及新聞測試',
                 'url':'https://example.org/demo','published_at':'2026-10-22T22:00:00Z',
                 'publisher':'示範來源','snippet':'僅供電子書排版驗證。',
                 'provider':'fixture','official':False}
            ]},ensure_ascii=False), encoding='utf-8')
            run('morning',root,NOW,fixture)
            run('evening',root,NOW+dt.timedelta(hours=10),fixture)
            for period in ('morning','evening'):
                for depth in ('essential','deep'):
                    book=root/'docs'/'archive'/'2026-10-23'/f'{period}-{depth}.epub'
                    self.assertTrue(book.is_file(),str(book))
                    validate_epub(book)
                    htmlpage=(book.with_suffix('.html')).read_text(encoding='utf-8')
                    self.assertIn(f'{period}-{depth}.epub',htmlpage)
                    self.assertIn('layout-01.css', htmlpage)
                    self.assertIn('category-strip', htmlpage)
            self.assertIn('color',EPUB_CSS.read_text(encoding='utf-8').lower())

if __name__=='__main__':
    unittest.main()
