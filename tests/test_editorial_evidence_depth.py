"""Editorial depth and provenance checks without calling paid APIs or the web."""
import copy
import datetime as dt
import os
import unittest
from unittest.mock import patch

from gib.newsroom_v16 import canonical_issue
from gib.gemini_editor_v16 import audit_model_output, research_and_revise, _prepare
from gib.evidence_review import review_official_excerpts
from gib.publish_v16 import as_xhtml

NOW = dt.datetime(2026, 10, 23, 2, tzinfo=dt.timezone.utc)


def news(n, label, snippet):
    return {
        "title": label,
        "url": "https://publisher.example/article/" + str(n),
        "publisher": "Example",
        "snippet": snippet,
        "published_at": NOW.isoformat(),
        "provider": "fixture",
    }


class EditorialEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.issue = canonical_issue([
            news(1, "Global inflation report", "The report claims inflation rose 4.2 percent."),
            news(2, "Asia exports report", "The report says export growth reached 9.8 percent."),
        ], "morning", NOW)
        self.assertEqual(len(self.issue["articles"]), 2)

    def test_numeric_claims_must_be_from_same_event(self):
        first = self.issue["articles"][0]
        second = self.issue["articles"][1]
        foreign = "9.8" if "9.8" not in first["headline_summary"] else "4.2"
        self.assertIn(foreign, second["headline_summary"])
        candidate = {"items": [{
            "event_id": first["event_id"],
            "source_ids": [first["sources"][0]["source_id"]],
            "headline_zh": "重大消息",
            "brief_zh": "據稱升幅達到 " + foreign + "，但仍需核實。",
        }]}
        edits, warnings = audit_model_output(candidate, self.issue)
        self.assertEqual(edits, [])
        self.assertTrue(any("numeric" in x for x in warnings))

    def test_localized_editorial_lead_reflows_with_offline_links(self):
        item = self.issue["articles"][0]
        editor = {"event_id": item["event_id"],
                  "source_ids": [item["sources"][0]["source_id"]],
                  "headline_zh": "全球通膨報告需要查核",
                  "brief_zh": "報導提出物價變化的觀察，仍需核對統計期間與官方來源。",
                  "sections": {"background": "應區分消息發布日期與觀察期間。" * 10,
                               "transmission": "需要釐清可能的利率傳導機制。" * 10,
                               "limitations": "索引不足以證實因果關係。" * 10}}
        page = as_xhtml(self.issue, [editor], level="deep")
        self.assertIn("全球通膨報告需要查核", page)
        self.assertIn('id="research-' + item["event_id"] + '"', page)
        self.assertIn('href="#research-' + item["event_id"] + '"', page)
        self.assertIn("RESEARCH WORKING DRAFT", page)

    def test_two_model_calls_only_and_editorial_qc(self):
        article = self.issue["articles"][0]
        response = {"items": [{
            "event_id": article["event_id"],
            "source_ids": [article["sources"][0]["source_id"]],
            "headline_zh": "通膨新聞需要額外證據",
            "brief_zh": "我們知道的是新聞索引聲稱的內容，仍缺少可追溯的一手資料。",
            "background": "應核對原始報告與發布日期。" * 18,
            "why_it_matters": "這可能影響政策預期，但目前缺乏因果驗證。" * 12,
            "limitations": "尚未取得相應的完整官方證據。" * 10
        }]}
        with patch.dict(os.environ, {
            "ENABLE_GEMINI": "1",
            "GEMINI_FREE_TIER_CONFIRMED": "1",
            "GEMINI_API_KEY": "FAKE_MOCK_KEY"
        }), patch("gib.gemini_editor_v16._call", side_effect=[response, response]) as call:
            done = research_and_revise(self.issue)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(done["status"], "REVISED_DRAFT_PENDING_REVIEW")
        self.assertEqual(done["edits"][0]["headline_zh"], "通膨新聞需要額外證據")
        self.assertGreater(done["word_count_cjk"], 150)

    def test_official_context_is_not_automatic_fact_certification(self):
        issue = copy.deepcopy(self.issue)
        report = issue["articles"][0]
        source = report["sources"][0]
        source["kind"] = "OFFICIAL_FEED"
        source["url"] = "https://www.federalreserve.gov/newsevents/pressreleases/sample.htm"
        claim = report["evidence"][0]
        claim["support_excerpt"] = (
            "Federal Reserve monetary policy target decision was announced in this report, "
            "but the indexing summary is not an exact excerpt from the official page."
        )
        text = ("Intro. Federal Reserve monetary policy committee discussed economic "
                "conditions and monetary policy targets. " * 10)
        results = review_official_excerpts(issue, fetcher=lambda url: {
            "text": text, "sha256": "a" * 64, "retrieved_at": NOW.isoformat()
        })
        self.assertEqual(results[0]["status"], "OFFICIAL_CONTEXT_UNVERIFIED")
        self.assertTrue(claim["official_context_excerpt"])
        self.assertNotEqual(claim["verification"], "VERIFIED")
        self.assertEqual(source["retrieval_status"], "OFFICIAL_BACKGROUND_ONLY")
        payload = _prepare(issue)
        self.assertTrue(payload["events"][0]["evidence"][0]["official_context_excerpt"])

    def test_model_cannot_invent_links(self):
        a = self.issue["articles"][0]
        edits, warnings = audit_model_output({"items": [{
            "event_id": a["event_id"],
            "source_ids": [a["sources"][0]["source_id"]],
            "brief_zh": "請去 https://invented.example.com 查看更多"
        }]}, self.issue)
        self.assertFalse(edits)
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
