"""GIB V2 readable source-bound fallbacks, deep-reader coverage, no false approval."""
import datetime as dt
import html
import unittest
from gib.newsroom_v16 import canonical_issue
from gib.publish_v16 import issue_body, source_grounded_fallback, source_grounded_digest

NOW=dt.datetime(2026,10,28,8,0,tzinfo=dt.timezone.utc)

def raw_row():
    return {"title":"Original publisher source title",
            "url":"https://publisher.example/news/article-123",
            "publisher":"publisher.example",
            "published_at":NOW.isoformat(),
            "snippet":"Publisher reports new information, with no independent review.",
            "provider":"direct_opml_rss"}

class SourceBoundReaderTests(unittest.TestCase):
    def issue(self):
        return canonical_issue([raw_row()],"morning",NOW)

    def test_missing_model_edit_shows_attributed_summary_not_empty_placeholder(self):
        issue=self.issue()
        x=issue_body(issue,[],level="essential")
        self.assertIn("來源報導重點",x)
        self.assertIn("Publisher reports new information",x)
        self.assertIn("publisher.example/news/article-123",x)
        self.assertNotIn("缺少完整研究證據",x)
        self.assertNotIn("EDITOR_APPROVED",issue["editorial_status"])
        self.assertIn("未驗收",x)

    def test_only_matching_source_id_points_may_be_rendered(self):
        issue=self.issue()
        a=issue["articles"][0]
        source_id=a["sources"][0]["source_id"]
        a["reported_key_points"]=[
            {"source_id":"unknown","text":"UNSUPPORTED-INVENTED-CONTENT"},
            {"source_id":source_id,"text":"A factual point attributed to the existing source."}]
        result=source_grounded_digest(a)
        self.assertTrue(any("A factual point attributed to" in text for text in result))
        self.assertFalse(any("UNSUPPORTED" in x for x in result))

    def test_empty_snippet_never_invents_a_story(self):
        issue=self.issue()
        a=issue["articles"][0]
        a["headline_summary"]=""
        result=source_grounded_fallback(a)
        self.assertIn("只有新聞標題",result)
        self.assertNotIn("由此可見",result)

    def test_untrusted_html_escaped(self):
        issue=self.issue()
        a=issue["articles"][0]
        sid=a["sources"][0]["source_id"]
        a["source_digest"]={"points":[{"source_id":sid,"text":"<script>alert(1)</script>"}]}
        result=source_grounded_fallback(a)
        self.assertIn("&lt;script&gt;",result)
        self.assertNotIn("<script>",result)

    def test_deep_report_with_existing_studies_has_navigation_and_all_sections(self):
        issue=self.issue()
        issue["deep_research"]=[
            {"title":"Research A","question":"Question A",
             "sections":[{"heading":"Original evidence A","body":"Evidence-backed detail A"}],
             "conclusions":["Carefully supported conclusion A"],
             "falsifiers":["A defined counter-observation"]},
            {"title":"Research B","question":"Question B",
             "sections":[{"heading":"Original evidence B","body":"Evidence-backed detail B"}]}]
        x=issue_body(issue,[],level="deep")
        self.assertIn('href="#research-topic-1"',x)
        self.assertIn('href="#research-topic-2"',x)
        self.assertIn('id="research-topic-1"',x)
        self.assertIn('id="research-topic-2"',x)
        self.assertIn("Original evidence A",x)
        self.assertIn("Original evidence B",x)
        self.assertIn("A defined counter-observation",x)
        self.assertIn("40-50 分鐘",x)
        self.assertNotIn("缺少完整研究證據",x)

    def test_no_deep_study_shows_genuinely_limited_source_reader(self):
        issue=self.issue()
        x=issue_body(issue,[],level="deep")
        self.assertIn("SOURCE READING",x)
        self.assertIn("查看來源原文",x)
        self.assertIn("無通過審查的獨立研究專題",x)
        self.assertIn('id="deep-research"',x)
        self.assertNotIn("缺少完整研究證據",x)
        self.assertFalse(issue["deep_research"])

if __name__=="__main__": unittest.main()
