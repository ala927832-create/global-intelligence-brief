"""GIB OPML/P1: bounded source discovery contracts, no credentials/network."""
import datetime as dt
import json
import unittest
from pathlib import Path
from qa.opml_free_p1 import collect, parse_feed, validate_config, check_one, attach_opml_provenance

class FreeOpmlTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))
        self.now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        self.published=self.now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.feeds=validate_config(self.config)

    def rss(self, title, link):
        return f'<rss version="2.0"><channel><item><title>{title}</title><link>{link}</link><pubDate>{self.published}</pubDate><description>Index only, no claim verification</description></item></channel></rss>'.encode()

    def test_24_original_opml_plus_three_verified_taiwan_official_feeds(self):
        self.assertEqual(len(self.feeds),27)
        self.assertEqual(len({x["url"] for x in self.feeds}),27)
        self.assertEqual({l:sum(x["lane"]==l for x in self.feeds)
                          for l in ("global","macro","energy_commodities","taiwan")},
                         {"global":9,"macro":6,"energy_commodities":3,"taiwan":9})
        self.assertTrue(all(x["url"].startswith("https://") for x in self.feeds))
        self.assertNotIn("Inoreader Pro",str(self.config))
        self.assertEqual(sum(x.get("source_class")=="official_government_rss" for x in self.feeds),3)
        self.assertTrue(all("www.ida.gov.tw" in x["url"] for x in self.feeds if x.get("source_class")=="official_government_rss"))

    def test_full_four_group_probe_with_realistic_rss_fixtures(self):
        mapping={f["url"]:self.rss("Article "+f["id"],"https://public.example/news/"+f["id"])
                 for f in self.feeds}
        articles, health=collect(self.config,fetcher=lambda url:mapping[url],now=self.now)
        self.assertEqual(health["gate"],"PASS_DIRECT_RSS_DISCOVERY")
        self.assertEqual(health["configured_sources"],27)
        self.assertEqual(len(articles),27)
        self.assertEqual(health["recent_7d_unique_article_urls"],27)
        self.assertFalse(health["release_approved"])
        self.assertEqual(health["editorial_claims_verified"],0)
        self.assertTrue(all(x["provider"]=="direct_opml_rss" for x in articles))

    def test_feed_suspended_system_message_is_never_a_news_article(self):
        bad=b'<rss><channel><item><title>Feed suspended! Please contact the owner.</title><description>Inoreader Pro plan is required to export RSS feeds.</description><pubDate>Fri, 01 Mar 2019 10:00:01 +0000</pubDate><link>https://www.inoreader.com/blog/post.html</link></item></channel></rss>'
        parsed, info=parse_feed(bad,self.feeds[0],self.now)
        self.assertEqual(parsed,[])
        self.assertEqual(info["rejected"]["suspended"],1)
        meta,rows=check_one(self.feeds[0],fetcher=lambda url:bad,now=self.now)
        self.assertEqual(meta["status"],"SUSPENDED_OUTPUT")
        self.assertEqual(rows,[])

    def test_atom_alternate_original_url_and_iso_time(self):
        stamp=self.now.isoformat()
        atom=f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Global policy</title><link rel="alternate" href="https://policy.example/article/2" /><published>{stamp}</published><summary>Context</summary></entry></feed>'.encode()
        rows,stats=parse_feed(atom,self.feeds[0],self.now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"],"https://policy.example/article/2")
        self.assertEqual(stats["rejected"]["missing_timezone_or_date"],0)

    def test_reject_missing_timezone_and_future_article(self):
        xml=b'<rss><channel><item><title>Invalid time</title><link>https://publisher.example/story</link><pubDate>2026-10-28T12:00:00</pubDate></item></channel></rss>'
        rows,stat=parse_feed(xml,self.feeds[0],self.now)
        self.assertEqual(rows,[])
        self.assertEqual(stat["rejected"]["missing_timezone_or_date"],1)

    def test_cross_feed_duplicate_preserves_source_ids_and_original_url(self):
        duplicate=self.rss("Common original","https://public.example/a?utm_source=a")
        def fake_fetch(url):
            return duplicate
        articles, report=collect(self.config,fetcher=fake_fetch,now=self.now)
        self.assertEqual(len(articles),1)
        self.assertEqual(len(articles[0]["source_ids"]),27)
        self.assertEqual(set(articles[0]["source_groups"]),
                         {"global","macro","energy_commodities","taiwan"})
        self.assertEqual(report["gate"],"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED")

    def test_four_group_gate_fails_when_energy_has_no_articles(self):
        def fake_fetch(url):
            source=next(x for x in self.feeds if x["url"]==url)
            return b'<rss><channel></channel></rss>' if source["lane"]=="energy_commodities" else self.rss("Current","https://public.example/"+source["id"])
        _,report=collect(self.config,fetcher=fake_fetch,now=self.now)
        self.assertEqual(report["gate"],"PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED")
        self.assertEqual(report["coverage"]["energy_commodities"]["feeds_with_valid_articles"],0)
        self.assertEqual(report["coverage"]["energy_commodities"]["feed_errors"],3)

    def test_selected_issue_citations_keep_opml_source_lineage(self):
        raw = [{
            "url": "https://news.example/report",
            "source_group": "global", "source_groups": ["global","macro"],
            "source_id": "global_01", "source_ids": ["global_01","macro_01"]
        }]
        issue = {"articles": [{"sources": [{
            "url": "https://news.example/report",
            "retrieval_status": "INDEX_ONLY"
        }]}], "source_health": {}}
        report={"gate":"PASS_DIRECT_RSS_DISCOVERY"}
        attach_opml_provenance(issue,raw,report)
        src=issue["articles"][0]["sources"][0]
        self.assertEqual(src["discovery_provider"],"direct_opml_rss")
        self.assertEqual(src["opml_source_groups"],["global","macro"])
        self.assertEqual(src["opml_source_ids"],["global_01","macro_01"])
        self.assertEqual(issue["articles"][0]["opml_source_groups"],["global","macro"])
        self.assertEqual(issue["source_health"]["free_opml"],report)

    def test_parser_never_promotes_unreadable_response_to_valid_news(self):
        meta,rows=check_one(self.feeds[0],fetcher=lambda url:b'<!doctype html><html><body>Access denied</body></html>',now=self.now)
        self.assertEqual(rows,[])
        self.assertIn(meta["status"],("NO_USABLE_ARTICLES","UNREADABLE_FEED_ParseError"))

if __name__=="__main__":
    unittest.main()
