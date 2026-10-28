"""Phase 1: public Inoreader output feeds are not 'verified' news articles."""
import datetime as dt
import json
import unittest
from tools.gib_style_c_rc.inoreader_source import (
    attach_provenance, collect_export_feeds, normalize_items, _validate_feed_url, strict_timestamp
)


class InoreaderSourceTests(unittest.TestCase):
    def setUp(self):
        self.now = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=2)).isoformat()
        self.urls = {
            "global": "https://www.inoreader.com/stream/user/-/label/GIB_GLOBAL?token=private-one",
            "macro": "https://www.inoreader.com/stream/user/-/label/GIB_MACRO?token=private-two",
            "energy_commodities": "https://www.inoreader.com/stream/user/-/label/GIB_ENERGY?token=private-three",
            "taiwan": "https://www.inoreader.com/stream/user/-/label/GIB_TAIWAN?token=private-four",
        }

    def _json(self, items):
        return json.dumps({"version": "https://jsonfeed.org/version/1", "items": items}).encode()

    def test_four_lanes_are_distinct_and_deduplicated(self):
        a={"title":"World affairs development","url":"https://news.example/world/a",
           "date_published":self.now,"summary":"Source claim pending verification."}
        b={"title":"Zinc smelter update","url":"https://industry.example/smelter/b",
           "date_published":self.now,"summary":"Producer statement."}
        c={"title":"Central bank report","url":"https://macro.example/report/c",
           "date_published":self.now,"summary":"Official macroeconomic update."}
        d={"title":"Taiwan industrial policy","url":"https://taiwan.example/policy/d",
           "date_published":self.now,"summary":"Local industrial policy update."}
        contents={
            self.urls["global"]:(self._json([a]),"application/feed+json"),
            self.urls["macro"]:(self._json([a,c]),"application/feed+json"),
            self.urls["energy_commodities"]:(self._json([b]),"application/feed+json"),
            self.urls["taiwan"]:(self._json([d]),"application/feed+json"),
        }
        result,health=collect_export_feeds(self.urls,fetcher=lambda url:contents[url])
        self.assertEqual(len(result),4)
        self.assertEqual(result[0]["inoreader_lanes"],["global","macro"])
        self.assertEqual(result[1]["inoreader_lanes"],["macro"])
        self.assertEqual(result[2]["inoreader_lanes"],["energy_commodities"])
        self.assertEqual(result[3]["inoreader_lanes"],["taiwan"])
        self.assertEqual(health["verified_claim_count"],0)
        self.assertEqual(set(health["connected_lanes"]),set(self.urls))
        self.assertEqual(len(health["lane_stats"]),4)
        for token in ("private-one","private-two","private-three","private-four"):
            self.assertNotIn(token,str(health))

    def test_rss_original_link_and_published_time(self):
        published = dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        rss=f"""<?xml version="1.0"?><rss><channel><title>Sample</title>
        <item><title>Policy update</title><link>https://official.example/notice</link>
        <pubDate>{published}</pubDate><description>&lt;p&gt;Original announcement&lt;/p&gt;</description></item>
        </channel></rss>""".encode()
        rows,rejected=normalize_items(rss,"application/rss+xml","energy_commodities")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"],"https://official.example/notice")
        self.assertEqual(rows[0]["snippet"],"Original announcement")
        self.assertEqual(rows[0]["provider"],"inoreader_export")

    def test_missing_or_invalid_source_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"INOREADER_NOT_CONNECTED"):
            collect_export_feeds({**self.urls,"taiwan":""})
        for bad in ("http://www.inoreader.com/output","https://evil.example/steal",
                    "https://www.inoreader.com.evil.example/path"):
            with self.assertRaises(ValueError):
                _validate_feed_url(bad)

    def test_undated_or_timezone_naive_is_excluded(self):
        self.assertIsNone(strict_timestamp("2026-10-28T07:00:00"))
        self.assertIsNone(strict_timestamp(""))
        self.assertIsNotNone(strict_timestamp("2026-10-28T07:00:00+08:00"))
        items=[{"title":"Ambiguous time","url":"https://news.example/naive",
                "date_published":"2026-10-28T07:00:00"}]
        rows,rejected=normalize_items(self._json(items),"application/feed+json","macro")
        self.assertEqual(len(rows),0)
        self.assertEqual(rejected["missing_publication_time"],1)

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
        raw=[{"url":"https://news.example/a","inoreader_lanes":["global","macro"]}]
        issue={"articles":[{"sources":[{"url":"https://news.example/a",
                        "retrieval_status":"INDEX_ONLY"}]}],"source_health":{}}
        health={"verified_claim_count":0}
        attach_provenance(issue,raw,health)
        src=issue["articles"][0]["sources"][0]
        self.assertEqual(src["inoreader_lanes"],["global","macro"])
        self.assertEqual(src["retrieval_status"],"INDEX_ONLY")
        self.assertEqual(src["discovery_provider"],"inoreader_export")

if __name__=="__main__":
    unittest.main()
