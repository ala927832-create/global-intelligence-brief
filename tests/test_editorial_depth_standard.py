"""WSJ/Economist-inspired depth standards: evidence beats padding.

Tests use invented headlines as fixtures, never real-world news assertions.
"""
import datetime as dt
import copy
import os
import unittest
from unittest.mock import patch

from gib.newsroom_v16 import canonical_issue
from gib.editorial import rank
from gib.editorial_depth import audit_editorial_depth, hanzi, redundancy
from gib.gemini_editor_v16 import _prepare, audit_model_output, research_and_revise

NOW=dt.datetime(2026,10,23,2,tzinfo=dt.timezone.utc)


class DepthTests(unittest.TestCase):
    def setUp(self):
        fixture_titles=[
            "Global recession economic growth outlook",
            "Federal reserve policy rate decision",
            "Taiwan advanced semiconductor supply issue",
            "China cross border tariff trade announcement",
            "Energy oil production supply update",
            "Japan bank yen monetary decision",
            "International port shipping disruption",
            "Artificial intelligence chip sector investment",
            "European inflation jobs report",
            "Manufacturing steel industry recovery",
            "US Treasury bond yield information",
            "Global logistics freight transport conditions",
        ]
        raw=[]
        for i,headline in enumerate(fixture_titles):
            raw.append({
                "title":headline,
                "url":f"https://publisher{i}.example/article/{i}",
                "publisher":f"publisher{i}",
                "snippet":"An unverified news index summary about an announcement.",
                "published_at":NOW.isoformat()})
        self.issue=canonical_issue(raw,"morning",NOW)
        self.assertGreaterEqual(len(self.issue["articles"]),8)

    def test_material_global_policy_outranks_daily_price_listing(self):
        items=[
          {"title":"Daily gold price rate today in a local store",
           "section":"macro","publishers":["Retail Bulletin"],"official":False},
          {"title":"International central bank policy decision changes global trade",
           "section":"macro","publishers":["Central Bank"],"official":True},
        ]
        ordered=rank(items,{"macro":20})
        self.assertIn("International",ordered[0]["title"])
        self.assertGreaterEqual(ordered[-1]["editorial_rank_signals"]["narrow_listing"],1)

    def test_no_editorial_draft_does_not_fake_deep_research(self):
        report=audit_editorial_depth(self.issue,[])
        self.assertEqual(report["deep_drafts_meeting_minimum_review_standard"],0)
        self.assertFalse(report["full_issue_quality_passed"])
        self.assertTrue(report["release_blockers"])

    def test_padding_and_unsigned_claims_cannot_pass(self):
        article=self.issue["articles"][0]
        padded="不能僅憑一則未經證實的消息，就認定存在穩固的歷史因果關係。"
        sections={k:padded*25 for k in
            ("background","why_it_matters","transmission","history",
             "alternative","watch","limitations")}
        result=audit_editorial_depth(self.issue,[{
            "event_id":article["event_id"],"verification":"AI_INTERPRETATION_NOT_VERIFIED",
            "sections":sections}])
        entry=result["research"][0]
        self.assertGreater(entry["chinese_analysis_hanzi"],800)
        self.assertGreater(entry["repetition_ratio"],0.18)
        self.assertFalse(entry["ready_for_deep_review"])
        self.assertTrue(any("repetition" in reason for reason in entry["reasons"]))
        self.assertTrue(any("attested" in reason for reason in entry["reasons"]))

    def test_content_rubric_cannot_grant_auto_release(self):
        # An invented reviewer attestation is permissible ONLY in a unit test.
        article=self.issue["articles"][0]
        article["sources"].append({
            "source_id":"primary_fixture","url":"https://official.example/survey",
            "kind":"OFFICIAL_FEED","retrieval_status":"OFFICIAL_EXCERPT_MATCH"})
        article["evidence"]=[{
            "claim_id":str(i),"source_id":"primary_fixture",
            "verification":"VERIFIED","reviewer":"TEST_FIXTURE",
            "source_location":"test paragraph","source_sha256":"a"*64}
            for i in range(3)]
        paragraphs=[
            "政策宣告本身需要與其實際執行和後續數據分開理解，來源的統計期間也需要清楚標註。",
            "企業可能透過庫存、供應商議價、成本調整及訂單重新分配作出反應，但傳導時間並不固定。",
            "不同研究視角可能產生相反結果，應追蹤製造業訂單和實際需求是否支持原本的假設。",
            "若官方後續公告與早前報導不符，需更新結論而非延續過時的市場敘事。",
        ]
        sections={}
        for ix,key in enumerate(("background","why_it_matters","transmission",
                                 "history","alternative","watch","limitations")):
            sections[key]="".join(f"{p}此段為模擬分析項目{ix}。" for p in paragraphs*5)
        result=audit_editorial_depth(self.issue,[{
            "event_id":article["event_id"],"verification":"EDITOR_REVIEWED","sections":sections}])
        self.assertFalse(result["full_issue_quality_passed"])
        # What matters is that article review and publication remain separate.
        self.assertIn("Requires human factual review and owner publishing approval",
                      result["release_blockers"])

    def test_two_stage_includes_chinese_short_briefs_without_diluting_research(self):
        packet=_prepare(self.issue)
        self.assertEqual(len(packet["events"]),3)
        self.assertGreaterEqual(len(packet["briefing_index"]),5)
        candidate=self.issue["articles"][4]
        brief={"event_id":candidate["event_id"],"source_ids":[
            candidate["sources"][0]["source_id"]],
            "headline_zh":"全球產業政策簡訊",
            "brief_zh":"來源報導有新消息，目前缺少獨立核實的原始文件。"}
        edits,warns=audit_model_output({"briefs":[brief]},self.issue)
        self.assertEqual(len(edits),1)
        self.assertEqual(edits[0]["sections"],{})
        self.assertEqual(edits[0]["verification"],"AI_SHORT_BRIEF_UNVERIFIED")
        brief["brief_zh"]="報導預測將增加 987654 個單位。"
        edits,warns=audit_model_output({"briefs":[brief]},self.issue)
        self.assertFalse(edits)
        self.assertTrue(warns)

    def test_two_passes_no_real_api_and_short_brief_survives(self):
        a=self.issue["articles"][0]
        b=self.issue["articles"][4]
        response={"items":[{
            "event_id":a["event_id"],"source_ids":[a["sources"][0]["source_id"]],
            "headline_zh":"需要查證的產業政策",
            "brief_zh":"這是一則尚待查證的國際新聞。",
            "background":"此項政策宣告缺少官方文件，需要持續查證。"*9,
            "why_it_matters":"可能影響供應鏈，但仍需要更多獨立來源。"*9,
            "transmission":"新聞與經濟結果之間尚需市場和供應數據。"*9,
            "limitations":"目前缺少一手證據，不能下確定結論。"*9}],
            "briefs":[{
            "event_id":b["event_id"],"source_ids":[b["sources"][0]["source_id"]],
            "headline_zh":"重要國際短訊","brief_zh":"來源提供一項仍待查證的消息。"}]}
        second_response=copy.deepcopy(response)
        second_response["items"][0]["background"]=(
            "研究稿核對顯示仍只有來源索引，不能據此確認政策結果。"
            "下一階段應先找到對應官方公告，釐清適用範圍和發布日期。"
            "若後續正式數據與報導不一致，就需要改變原本的假設。"
        )*4
        second_response["items"][0]["why_it_matters"]=(
            "不能只憑來源標題推論供應鏈已受影響；必須先取得實際訂單、"
            "跨境交易或企業申報的可追溯資料，再與其他政策因素比較。"
            "若供應鏈數據未出現變化，應下修原有市場影響假說。"
        )*4
        with patch.dict(os.environ,{"ENABLE_GEMINI":"1",
             "GEMINI_FREE_TIER_CONFIRMED":"1","GEMINI_API_KEY":"NOT_REAL"},
             clear=False),patch("gib.gemini_editor_v16._call",side_effect=[response,second_response]) as api:
            res=research_and_revise(self.issue)
        self.assertEqual(api.call_count,2)
        self.assertEqual(res["status"],"REVISED_DRAFT_PENDING_REVIEW")
        self.assertTrue(any(e["event_id"]==b["event_id"] for e in res["edits"]))
        self.assertTrue(any(e["event_id"]==a["event_id"] for e in res["edits"]))
        self.assertGreater(max(res["revision_ratio_by_event"].values()),0.02)

    def test_unchanged_second_pass_does_not_count_as_edited(self):
        a=self.issue["articles"][0]
        identical={"items":[{
            "event_id":a["event_id"],"source_ids":[a["sources"][0]["source_id"]],
            "headline_zh":"需要查證的政策","brief_zh":"來源仍未核實。",
            "background":"這份研究還缺少原始官方公告和數據期間的定位證據。"*10,
            "why_it_matters":"缺乏原始證據就不應假設經濟影響已經發生。"*10,
            "transmission":"必須逐步確認政策改變是否已實際落地。"*10}]}
        with patch.dict(os.environ,{"ENABLE_GEMINI":"1",
             "GEMINI_FREE_TIER_CONFIRMED":"1","GEMINI_API_KEY":"FAKE"},
             clear=False),patch("gib.gemini_editor_v16._call",side_effect=[identical,identical]):
            res=research_and_revise(self.issue)
        self.assertEqual(res["status"],"SECOND_PASS_NO_MATERIAL_EDIT")
        self.assertFalse(res["edits"])
        self.assertEqual(len(res["first_pass_drafts"]),1)
        self.assertEqual(len(res["second_pass_rejected_drafts"]),1)
        from gib.publish_v16 import as_xhtml
        qa_issue=copy.deepcopy(self.issue)
        qa_issue["gemini_editorial"]={"status":res["status"]}
        page=as_xhtml(qa_issue,res["second_pass_rejected_drafts"],level="deep")
        self.assertIn("雙輪編輯未通過",page)
        self.assertIn("不能認定完成深度研究",page)


if __name__=="__main__":
    unittest.main()
