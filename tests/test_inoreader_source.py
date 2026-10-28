"""Phase 1: public Inoreader output feeds are not 'verified' news articles."""
import datetime as dt
import json
import unittest
from tools.gib_style_c_rc.inoreader_source import (
    attach_provenance, collect_export_feeds, normalize_items, _validate_feed_url
)


class InoreaderSourceTests(unittest.TestCase):
    def setUp(self):
        self.now = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=2)).isoformat()
        self.urls = {
            "global": "https://www.inoreader.com/stream/user/-/label/GIB_GLOBAL?token=private-one",
            "industry": "https://www.inoreader.com/stream/user/-/label/GIB_INDUSTRY?token=private-two",
        }

    def _json(self, items):
        return json.dumps({"version": "https://jsonfeed.org/version/1", "items": items}).encode()

    def test_global_and_industry_lanes_are_distinct_and_deduplicated(self):
        a={"title":"World affairs development","url":"https://news.example/world/a",
           "date_published":self.now,"summary":"Source claim pending verification."}
        b={"title":"Zinc smelter update","url":"https://industry.example/smelter/b",
           "date_published":self.now,"summary":"Producer statement."}
        contents={
            self.urls["global"]:(self._json([a]),"application/feed+json"),
            self.urls["industry"]:(self._json([a,b]),"application/feed+json"),
        }
        result,health=collect_export_feeds(self.urls,fetcher=lambda url:contents[url])
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]["inoreader_lanes"],["global","industry"])
        self.assertEqual(result[1]["inoreader_lanes"],["industry"])
        self.assertEqual(health["verified_claim_count"],0)
        self.assertEqual(set(health["connected_lanes"]),{"global","industry"})
        self.assertNotIn("private-one",str(health))
        self.assertNotIn("private-two",str(health))

    def test_rss_original_link_and_published_time(self):
        published = dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        rss=f"""<?xml version="1.0"?><rss><channel><title>Sample</title>
        <item><title>Policy update</title><link>https://official.example/notice</link>
        <pubDate>{published}</pubDate><description>&lt;p&gt;Original announcement&lt;/p&gt;</description></item>
        </channel></rss>""".encode()
        rows,rejected=normalize_items(rss,"application/rss+xml","global")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"],"https://official.example/notice")
        self.assertEqual(rows[0]["snippet"],"Original announcement")
        self.assertEqual(rows[0]["provider"],"inoreader_export")

    def test_missing_or_invalid_source_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"INOREADER_NOT_CONNECTED"):
            collect_export_feeds({"global":self.urls["global"],"industry":""})
        for bad in ("http://www.inoreader.com/output","https://evil.example/steal",
                    "https://www.inoreader.com.evil.example/path"):
            with self.assertRaises(ValueError):
                _validate_feed_url(bad)

    def test_reader_links_are_not_mistaken_for_original_articles(self):
        items=[{"title":"Reader alias","url":"https://www.inoreader.com/article/123",
                "date_published":self.now}]
        rows,errors=normalize_items(self._json(items),"application/feed+json","global")
        self.assertEqual(rows,[])
        self.assertEqual(errors["invalid_article_link"],1)

    def test_feed_failures_never_expose_secret_address(self):
        def fail(_):
            raise RuntimeError("network failed at "+self.urls["global"])
        with self.assertRaises(RuntimeError) as err:
            collect_export_feeds(self.urls,fetcher=fail)
        self.assertIn("INOREADER_FEED_UNAVAILABLE",str(err.exception))
        self.assertNotIn("private-one",str(err.exception))

    def test_attribution_is_lane_specific_and_not_fact_verified(self):
        raw=[{"url":"https://news.example/a","inoreader_lanes":["global","industry"]}]
        issue={"articles":[{"sources":[{"url":"https://news.example/a",
                        "retrieval_status":"INDEX_ONLY"}]}],"source_health":{}}
        health={"verified_claim_count":0}
        attach_provenance(issue,raw,health)
        src=issue["articles"][0]["sources"][0]
        self.assertEqual(src["inoreader_lanes"],["global","industry"])
        self.assertEqual(src["retrieval_status"],"INDEX_ONLY")
        self.assertEqual(src["discovery_provider"],"inoreader_export")

if __name__=="__main__":
    unittest.main()
