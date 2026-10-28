"""Source-grounded QA website content checks: not only green builds."""
from __future__ import annotations
import json
import re
import unittest
from html import unescape
from pathlib import Path

ROOT=Path("docs/qa-web-v2")

class GIBV2WebQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.news=json.loads((ROOT/"source_grounded_20261028.json").read_text(encoding="utf-8"))["articles"]
        cls.essential=(ROOT/"essential.html").read_text(encoding="utf-8")
        cls.deep=(ROOT/"deep.html").read_text(encoding="utf-8")

    def test_readable_nine_stories_have_concrete_source_bound_claims(self):
        self.assertGreaterEqual(len(self.news),8)
        self.assertLessEqual(len(self.news),12)
        self.assertEqual(len({x["key"] for x in self.news}),len(self.news))
        for article in self.news:
            with self.subTest(article=article["key"]):
                self.assertGreaterEqual(len(article["points"]),3)
                self.assertTrue(all(len(point)>16 for point in article["points"]))
                self.assertGreaterEqual(len(article["summary"]),25)
                self.assertTrue(article["status"])
                self.assertTrue(article["links"])
                self.assertTrue(all(url.startswith("https://") for _,url in article["links"]))
                for html in (self.essential,self.deep):
                    self.assertIn('id="news-'+article["key"]+'"',html)
                    self.assertIn(article["summary"],html)
                    for point in article["points"]:
                        self.assertIn(point,html)
                    for _,url in article["links"]:
                        self.assertIn(url.replace("&","&amp;"),html)

    def test_missing_research_is_never_placeholder_and_deep_is_reachable(self):
        for html in (self.essential,self.deep):
            self.assertNotIn("<strong>缺少完整研究證據</strong>",html)
            for sec in ("executive","world","analysis","deep","watch","sources"):
                self.assertIn('id="'+sec+'"',html)
            self.assertIn("P2",html)
            self.assertIn('name="robots" content="noindex,nofollow,noarchive"',html)
        for key in ("research-1","research-2"):
            self.assertIn('href="#'+key+'"',self.deep)
            self.assertIn('id="'+key+'"',self.deep)
            self.assertIn('href="deep.html#'+key+'"',self.essential)
        self.assertGreaterEqual(self.deep.count('class="dossier-section"'),8)
        self.assertGreaterEqual(self.deep.count('class="research-figure"'),2)

    def test_no_broken_in_page_chapter_references(self):
        for html in (self.essential,self.deep):
            ids=set(re.findall(r'\bid="([^"]+)"',html))
            local=re.findall(r'href="#([^"]+)"',html)
            self.assertTrue(local)
            self.assertFalse(set(local)-ids, sorted(set(local)-ids))

    def test_length_targets_must_remain_unapproved_when_content_short(self):
        for html in (self.essential,self.deep):
            self.assertIn("尚未達到",html)
            visible=html.split('<main class="reading-paper">',1)[1].split('<section class="feedback"',1)[0]
            visible=re.sub(r"<[^>]*>"," ",visible)
            chinese=len(re.findall(r"[\u4e00-\u9fff]",unescape(visible)))
            self.assertGreaterEqual(chinese,2500)
            self.assertLess(chinese,9000)
        self.assertLess(len(re.findall(r"[\u4e00-\u9fff]",self.deep)),16000)
        # This is an explicit caution, not editorial acceptance.

if __name__=="__main__": unittest.main()
