"""Curated primary research is actual article text provenance, not 'VERIFIED' news."""
import datetime as dt
import unittest

from gib.r2_evidence_packets import (
    _attach_curated_original_research, _load_issue_manifest,
    fetch_curated_primary_page
)

NOW=dt.datetime(2026,10,29,3,0,tzinfo=dt.timezone.utc)

class CuratedOriginalEvidenceTests(unittest.TestCase):
    def samples(self):
        registry=_load_issue_manifest()
        return [{
            "event_id":key,
            "original_title":item["exact_news_title"],
            "topic":"macro",
            "linked_sources":[],
            "source_domains":[]
        } for key,item in registry.items()]

    def test_four_current_issues_have_five_exact_primary_research_links(self):
        manifest=_load_issue_manifest()
        lookup={doc["url"]:doc for item in manifest.values()
                for doc in item["primary_documents"]}
        def fake(url):
            doc=lookup[url]
            return {
                "text":" Original primary document: "+" ".join(doc["required_phrases"]),
                "sha256":"a"*64,
                "retrieved_at":NOW.isoformat(),
            }
        packets=self.samples()
        audit=_attach_curated_original_research(packets,NOW,fake,6)
        self.assertEqual(len(packets),4)
        self.assertEqual(len(audit),5)
        self.assertTrue(all(x["status"]=="ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
                            for x in audit),audit)
        self.assertEqual(sum(len(d["curated_original_research"]) for d in packets),5)
        self.assertTrue(all(not doc["claim_fact_checked"]
                            for p in packets for doc in p["curated_original_research"]))
        self.assertTrue(all(not doc["human_reviewed"]
                            for p in packets for doc in p["curated_original_research"]))

    def test_no_matching_news_title_never_receives_an_external_document(self):
        packets=self.samples()
        packets[0]["original_title"]="An unrelated story with same numeric event id"
        calls=[]
        audits=_attach_curated_original_research(
            packets,NOW,lambda url:calls.append(url),0)
        self.assertEqual(calls,[])
        self.assertEqual(packets[0]["curated_original_research"],[])
        self.assertTrue(any(x["status"]=="OFFICIAL_READ_ONLY_BUDGET_REACHED"
                            for x in audits))

    def test_strict_allowlist_rejects_arbitrary_urls_before_network(self):
        for url in ("http://www.federalreserve.gov/", "https://unapproved.example/file",
                    "https://attacker.com@unapproved.example/"):
            with self.assertRaises(ValueError):
                fetch_curated_primary_page(url)

    def test_fetched_page_without_claim_text_is_not_promoted(self):
        p=self.samples()
        log=_attach_curated_original_research(
            p,NOW,lambda url:{
                "text":"unrelated generic homepage with no matched claim",
                "sha256":"b"*64,"retrieved_at":NOW.isoformat()
            },6)
        self.assertEqual(len(log),5)
        self.assertTrue(all(x["status"]=="PAGE_RETRIEVED_NO_EXACT_CLAIM_MATCH"
                            for x in log))
        self.assertEqual(sum(bool(doc["matched_primary_text_phrases"])
                             for row in p for doc in row["curated_original_research"]),0)

if __name__=="__main__":
    unittest.main()
