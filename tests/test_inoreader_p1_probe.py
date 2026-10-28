"""P1 acceptance: real-source gate logic tested without private credentials."""
import datetime as dt
import json
import unittest
from qa.inoreader_p1_probe import probe

class P1GateTests(unittest.TestCase):
    def setUp(self):
        self.urls={lane: f"https://www.inoreader.com/stream/user/1/tag/{lane}?token=secret-{lane}"
                   for lane in ("global","macro","energy_commodities","taiwan")}
        self.published=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1)).isoformat()

    def test_all_four_actual_payloads_required(self):
        response={}
        for lane,url in self.urls.items():
            items=[{"title":f"Fresh story in {lane}",
                    "url":f"https://source.example/{lane}",
                    "date_published":self.published,
                    "summary":"A source report, not editor-verified."}]
            response[url]=(json.dumps({"items":items}).encode(),"application/feed+json")
        report=probe(self.urls,fetcher=lambda url:response[url])
        self.assertEqual(report["gate"],"PASS_REAL_SOURCE_INGESTION")
        self.assertEqual(report["unique_original_articles"],4)
        self.assertEqual(report["connected_lanes"],4)
        self.assertFalse(report["release_approved"])
        self.assertEqual(report["editorial_facts_verified"],0)
        for lane in self.urls:
            self.assertEqual(report["lanes"][lane]["readable_items"],1)
            self.assertNotIn(f"secret-{lane}",str(report))

    def test_invalid_value_refuses_network_and_identifies_lane(self):
        bad={**self.urls,"global":"News folder"}
        def must_not_fetch(url):
            self.fail("Network must not be used if any lane URL is bad")
        report=probe(bad,fetcher=must_not_fetch)
        self.assertEqual(report["gate"],"BLOCKED_INVALID_FEED_VALUES")
        self.assertEqual(report["lanes"]["global"]["url_shape"],"INOREADER_EXPORT_NOT_A_URL")

    def test_safe_normalization_of_scheme_less_value(self):
        converted={**self.urls,"macro":"www.inoreader.com/stream/user/1/tag/macro?token=secret-macro"}
        def fetch(url):
            self.assertTrue(url.startswith("https://www.inoreader.com/"))
            item={"title":"Valid source", "url":"https://source.example/item",
                  "date_published":self.published}
            return json.dumps({"items":[item]}).encode(),"application/json"
        report=probe(converted,fetcher=fetch)
        self.assertEqual(report["gate"],"PASS_REAL_SOURCE_INGESTION")

    def test_http_conversion_is_https_only(self):
        converted={**self.urls,"energy_commodities":"http://inoreader.com/stream/user/1/tag/energy?token=secret-energy"}
        def fetch(url):
            self.assertTrue(url.startswith("https://"))
            item={"title":"Valid source", "url":"https://source.example/item",
                  "date_published":self.published}
            return json.dumps({"items":[item]}).encode(),"application/json"
        self.assertEqual(probe(converted,fetcher=fetch)["gate"],"PASS_REAL_SOURCE_INGESTION")

    def test_one_empty_lane_fails_gate(self):
        def fetch(url):
            lane=url.split("/tag/")[1].split("?")[0]
            items=[] if lane=="taiwan" else [{
                "title":"World news","url":f"https://news.example/{lane}",
                "date_published":self.published}]
            return json.dumps({"items":items}).encode(),"application/json"
        report=probe(self.urls,fetcher=fetch)
        self.assertEqual(report["gate"],"BLOCKED_EMPTY_SOURCE_LANE")
        self.assertEqual(report["lanes"]["taiwan"]["readable_items"],0)

    def test_remote_error_does_not_leak_secret_or_claim_success(self):
        def fetch(url):
            raise RuntimeError("request failed to "+url)
        report=probe(self.urls,fetcher=fetch)
        self.assertEqual(report["gate"],"BLOCKED_FEED_RETRIEVAL")
        self.assertNotIn("secret-",str(report))
        self.assertFalse(report["release_approved"])

if __name__=="__main__":
    unittest.main()
