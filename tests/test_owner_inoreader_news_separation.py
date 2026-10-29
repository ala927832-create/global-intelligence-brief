"""Owner rule: approved subscribed news is REPORTABLE, not AI-fact-certified.

Tests use the REAL 24-feed roster with synthetically constructed RSS entries.
Synthetic entries are not proof that an article actually appeared in the feed.
"""
import datetime as dt
import hashlib
import json
import unittest
from pathlib import Path

from gib.contract import locked_contract
from gib.subscription_news_policy import is_subscribed_news, news_evidence_policy
from gib.newsroom_v16 import canonical_issue
from gib.p2_editorial_acceptance import p2_readiness
from qa.p2_content_gate import eligible_source_rows, source_input_gate, selected_story_gate

CUTOFF=dt.datetime(2026,10,29,7,30,tzinfo=dt.timezone(dt.timedelta(hours=8)))
PUBLISHED="2026-10-28T23:05:00+00:00"
FEEDS=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))["feeds"]

def subscribed(i, title=None, snippet=""):
    src=FEEDS[i%len(FEEDS)]
    return {
        "title":title or f"Contemporary international reporting item {i} with an original linked headline",
        "url":f"https://newsroom-{i%5}.example/world/{i}",
        "published_at":PUBLISHED,"snippet":snippet,
        "provider":"direct_opml_rss","source_id":src["id"],
        "source_ids":[src["id"]],"source_group":src["lane"],
        "source_groups":[src["lane"]],"source_name":src["name"],
        "publisher":src["name"],"official":False,
        "verification_status":"INDEX_ONLY_NOT_FACT_CHECKED"
    }


class OwnerSubscribedNewsSeparateFromAiResearchTests(unittest.TestCase):
    def test_frozen_contract_records_explicit_owner_exception_without_publication(self):
        c=locked_contract()
        owner=c["editorial_selection"]["inoreader_subscribed_news_owner_amendment"]
        self.assertEqual(owner["approved_date"],"2026-10-29")
        self.assertIn("SOURCE-ATTRIBUTED NEWS",owner["policy"])
        self.assertIn("not veto",owner["policy"])
        self.assertEqual(c["publishing"],"OFF_UNTIL_QUALITY_AND_OWNER_APPROVAL")
        self.assertEqual(c["schedule"]["global_morning"],"07:30")
        self.assertEqual(c["schedule"]["global_evening"],"17:30")
        self.assertEqual(c["editorial_acceptance"]["morning_content"]["distinct_substantive_analyses"],4)

    def test_subscriber_bare_headline_admitted_without_inventing_news_blurb(self):
        row=subscribed(0,"Historic cultural discovery draws international attention","")
        self.assertTrue(is_subscribed_news(row))
        allowed,blocked,_,_=eligible_source_rows([row],CUTOFF)
        self.assertEqual(len(allowed),1)
        self.assertFalse(blocked)
        mode=news_evidence_policy(row)
        self.assertEqual(mode["summary_policy"],"HEADLINE_ONLY_LINK_NO_AI_SUMMARY")
        self.assertFalse(mode["independent_claim_verification"])
        issue=canonical_issue(allowed,"morning",CUTOFF,tiered_v3=True)
        self.assertEqual(len(issue["articles"]),1)
        story=issue["articles"][0]
        self.assertEqual(story["headline_summary"],"")
        self.assertTrue(story["news_reporting_eligible"])
        self.assertFalse(story["news_summary_generation_allowed"])
        self.assertEqual(story["sources"][0]["url"],row["url"])
        self.assertEqual(story["evidence"][0]["verification"],"ATTRIBUTED_UNVERIFIED")
        self.assertFalse(issue.get("release_approved",False))

    def test_subscribed_sports_or_other_topics_eligible_as_news_but_not_forced_to_front_page(self):
        title="Tennis championship final draws global audience"
        news=subscribed(2,title)
        admitted,blocked,_,_=eligible_source_rows([news],CUTOFF)
        self.assertEqual(len(admitted),1)
        self.assertNotIn("SPORTS_NOT_NEWS_DESK",blocked)
        # This tests inclusion only, not automatic headline ranking/verification.
        self.assertFalse(news_evidence_policy(news)["gemini_or_publication_permission"])

    def test_an_unsubscribed_feed_or_impostor_still_requires_real_excerpt(self):
        row=subscribed(0,"Local sports title only","")
        impostors=[
            dict(row,provider="freenews"),
            dict(row,source_id="made_up_source"),
            dict(row,source_name="Fake feed"),
            dict(row,source_group="taiwan"),
            dict(row,source_ids=["invalid"]),
            dict(row,source_id=["invalid"])
        ]
        for bad in impostors:
            with self.subTest(bad=bad):
                self.assertFalse(is_subscribed_news(bad))
                allowed,blocked,_,_=eligible_source_rows([bad],CUTOFF)
                self.assertFalse(allowed)
                self.assertTrue(blocked)
        # Fake publisher cannot write six invented sentences to claim OPML.
        misleading=dict(row,provider="gdelt",snippet="Published text " * 6)
        self.assertFalse(is_subscribed_news(misleading))

    def test_stale_fake_future_non_https_and_inoreader_redirects_remain_blocked(self):
        original=subscribed(1,"International reporting title","")
        invalid=[
            dict(original,published_at="2026-10-20T00:00:00+00:00"),
            dict(original,published_at="2026-10-29T03:00:00+00:00"),
            dict(original,url="http://untrusted.example/one"),
            dict(original,url="https://www.inoreader.com/article/one"),
            dict(original,published_at="missing")
        ]
        for bad in invalid:
            accepted,rejected,_,_=eligible_source_rows([bad],CUTOFF)
            self.assertFalse(accepted)
            self.assertTrue(rejected)

    def test_twenty_real_roster_ids_support_source_attributed_news_tiers(self):
        topics=[
            "G7 government election agreement","Bank of Canada inflation monetary policy",
            "Energy oil refinery supply","Technology semiconductor innovation",
            "United Nations ceasefire diplomatic agreement"
        ]
        rows=[subscribed(i,f"{topics[i%5]}: independently titled event {hashlib.sha256(str(i).encode()).hexdigest()}") for i in range(24)]
        source=source_input_gate(rows,CUTOFF,observed_at=CUTOFF+dt.timedelta(minutes=5))
        self.assertEqual(source["gate"],"PASS_SOURCE_CANDIDATES_ONLY_NOT_FACT_VERIFIED",source)
        self.assertEqual(source["source_attributed_subscribed_news_events"],24)
        self.assertEqual(source["subscribed_headline_only_links"],24)
        self.assertEqual(source["source_excerpt_supported_news_events"],0)
        eligible,_,_,_=eligible_source_rows(rows,CUTOFF)
        issue=canonical_issue(eligible,"morning",CUTOFF,tiered_v3=True)
        selection=selected_story_gate(issue)
        self.assertEqual(selection["gate"],"PASS_EDITORIAL_VOLUME_ONLY_NOT_EVIDENCE_VERIFIED",selection)
        self.assertEqual(selection["selected_subscribed_news_reportable"],24)
        self.assertEqual(selection["selected_subscribed_headline_only"],24)
        self.assertEqual(selection["main_news"],12)
        self.assertEqual(selection["supplementary_news"],12)
        self.assertTrue(all(not row["news_summary_generation_allowed"] for row in issue["articles"]))
        self.assertTrue(all(not row["headline_summary"] for row in issue["articles"]))
        ready=p2_readiness(issue)
        self.assertEqual(ready["news_reporting_eligible_from_subscription"],24)
        self.assertEqual(ready["news_reporting_rejected_due_to_opposing_ai_interpretation"],0)
        self.assertEqual(ready["gate"],"P2_EDITORIAL_HOLD")
        self.assertNotIn("LEAD_CROSS_REFERENCE_AND_PRIMARY_FACT_REVIEW_INCOMPLETE",ready["blockers"])
        self.assertFalse(ready["automatic_release_approved"])

    def test_evening_subscriber_news_not_subject_to_legacy_material_keyword_gate(self):
        row=subscribed(8,"Unusual national arts museum announcement","")
        issue=canonical_issue([row],"evening",CUTOFF,require_material_relevance=True)
        self.assertEqual(len(issue["articles"]),1)
        self.assertTrue(issue["articles"][0]["news_reporting_eligible"])

if __name__=="__main__":
    unittest.main()
