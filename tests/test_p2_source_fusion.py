"""P2 approved-source fusion tests; synthetic metadata never signifies real news."""
import datetime as dt
import unittest

from qa.p2_source_fusion import (
    collect_existing_free_sources, fuse_with_original_opml, _recent_free_row)
from qa.opml_free_p1 import attach_opml_provenance
from gib.newsroom_v16 import canonical_issue

UTC=dt.timezone.utc

class FusionTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,28,4,0,tzinfo=UTC)
        self.dt="2026-10-28T03:00:00+00:00"
        self.opml=[
            {"provider":"direct_opml_rss","url":"https://world.example/current",
             "published_at":self.dt,"title":"Global central bank inflation policy decision",
             "snippet":"Original-source headline","source_id":"global_01",
             "source_ids":["global_01"],"source_group":"global",
             "source_groups":["global"]}]
        self.health={"gate":"PASS_DIRECT_RSS_DISCOVERY",
                     "data_origin":"USER_OPML_DIRECT_PUBLISHER_RSS",
                     "configured_sources":24,"checked_at_utc":self.now.isoformat()}

    def test_fuses_existing_original_sources_without_false_independence(self):
        results={
            "gdelt":{"raw":[{"provider":"gdelt",
                             "title":"Same syndicated headline",
                             "url":"https://world.example/current?utm_source=gdelt",
                             "published_at":self.dt,
                             "snippet":"Reprint, not a second source"}],"errors":[]},
            "official_rss":{"raw":[{"provider":"official_rss",
                  "title":"Federal Reserve publishes statement on policy rate",
                  "url":"https://www.federalreserve.gov/newsevents/pressreleases/abc.htm",
                  "published_at":self.dt,"snippet":"Primary institution statement"}],"errors":[]},
            "freenews":{"raw":[{"provider":"freenews",
                  "title":"Trade and tariff developments across borders",
                  "url":"https://news.example/trade","published_at":self.dt,
                  "snippet":"Attributed article summary"}],"errors":[]}}
        combined,health=fuse_with_original_opml(self.opml,self.health,results,self.now)
        self.assertEqual(len(combined),3)
        self.assertEqual(health["p2_original_opml_index_items"],1)
        self.assertEqual(health["p2_external_net_new_index_items"],2)
        self.assertEqual(health["original_opml_p1_gate"],"PASS_DIRECT_RSS_DISCOVERY")
        self.assertTrue(health["p2_all_claims_unverified"])
        original=next(x for x in combined if x["url"]=="https://world.example/current")
        self.assertEqual(set(original["discovery_providers"]),{"gdelt","direct_opml_rss"})
        self.assertEqual(original["source_ids"],["global_01"])
        self.assertEqual(health["p2_external_source_fusion"]["gdelt"]["duplicate_original_urls"],1)

        issue=canonical_issue(combined,"morning",self.now,
                              require_material_relevance=True)
        attach_opml_provenance(issue,combined,health)
        source_map={s["url"]:s for a in issue["articles"] for s in a["sources"]}
        self.assertEqual(source_map["https://world.example/current"]["opml_source_ids"],
                         ["global_01"])
        self.assertFalse(source_map["https://news.example/trade"].get("opml_source_ids"))
        self.assertIn("freenews",source_map["https://news.example/trade"]["discovery_providers"])
        self.assertTrue(all(c["verification"]=="ATTRIBUTED_UNVERIFIED"
                            for a in issue["articles"] for c in a["evidence"]))

    def test_reject_undated_nonpublic_and_stale_external_indexes(self):
        rows=[
            {"title":"Policy","url":"http://example.com/story","published_at":self.dt},
            {"title":"Policy","url":"https://news.google.com/redirect","published_at":self.dt},
            {"title":"Policy","url":"https://world.example/story","published_at":"2026-10-28T02:00:00"},
            {"title":"Policy","url":"https://world.example/story","published_at":"2026-10-12T02:00:00Z"}
        ]
        reasons=[_recent_free_row(x,"gdelt",self.now)[1] for x in rows]
        self.assertEqual(reasons,[
            "MISSING_TITLE_OR_ORIGINAL_HTTPS_URL",
            "ORIGINAL_PUBLISHER_URL_UNCONFIRMED",
            "MISSING_TIMEZONE",
            "STALE_OR_OUTSIDE_SNAPSHOT"
        ])

    def test_missing_free_api_key_not_disguised_as_global_coverage(self):
        res=collect_existing_free_sources({},self.now,fetchers={
            "official_rss":lambda errors: [],
            "gdelt":lambda errors: [],
            "freenews":lambda errors: (errors.append("KEY_NOT_CONFIGURED") or [])})
        rows,health=fuse_with_original_opml(self.opml,self.health,res,self.now)
        self.assertEqual(len(rows),1)
        self.assertEqual(health["p2_external_source_fusion"]["freenews"]["errors"],[
            "KEY_NOT_CONFIGURED"
        ])
        self.assertEqual(health["p2_external_net_new_index_items"],0)
        self.assertEqual(health["gate"],"PASS_DIRECT_RSS_DISCOVERY")
        self.assertFalse(health.get("editorial_claims_verified",0))

    def test_additional_feeds_never_override_original_opml_p1_gate(self):
        broken={**self.health,"gate":"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED"}
        other={"official_rss":{"raw":[{"provider":"official_rss",
            "title":"Official economy and global inflation index",
            "url":"https://www.federalreserve.gov/news/aaa",
            "published_at":self.dt}]}}
        _,health=fuse_with_original_opml(self.opml,broken,other,self.now)
        self.assertEqual(health["gate"],"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED")
        self.assertEqual(health["original_opml_p1_gate"],"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED")

if __name__=="__main__":
    unittest.main()
