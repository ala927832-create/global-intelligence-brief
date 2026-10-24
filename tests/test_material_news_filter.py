"""High-precision relevance triage: avoid irrelevant sports in finance publications."""
import datetime as dt
import unittest
from gib.newsroom_v16 import canonical_issue
from gib.editorial import material_news_candidate

class MaterialNewsTests(unittest.TestCase):
    def test_macro_energy_and_fed_eligible(self):
        for headline in (
            "U.S. refineries have been running at very high rates in 2026",
            "Federal Reserve interest rate policy decision impacts economy",
            "Supply chain disruption raises energy and shipping costs",
            "September employment report shows wages and unemployment",
        ):
            self.assertTrue(material_news_candidate({"title":headline}))
    def test_non_finance_sports_excluded(self):
        for headline in (
            "Warriors fans pack Chase Center for home opener with championship hopes",
            "Who Are College Football's Leading Receivers After Week 7?",
            "Australian umpire's Ranji Trophy sojourn at BKC",
            "Drama for Trackhouse-Aprilia: Ai Ogura penalised",
            "Aston Villa soccer match preview",
        ):
            self.assertFalse(material_news_candidate({"title":headline}))
    def test_newsroom_does_not_pad_with_sports(self):
        now=dt.datetime(2026,10,24,7,tzinfo=dt.timezone.utc)
        raw=[{"title":title,"url":f"https://example.org/item{i}",
               "publisher":"Test","published_at":now.isoformat()} for i,title in enumerate((
            "U.S. refineries have been running at very high rates in 2026",
            "Warriors fans pack Chase Center for home opener with championship hopes",
            "Federal Reserve monetary policy decision on global inflation",
            "Who Are College Football's Leading Receivers After Week 7?",
        ))]
        result=canonical_issue(raw,"morning",now)
        self.assertEqual(len(result["articles"]),2)
        self.assertGreaterEqual(result["source_health"]["unrelated_candidate_excluded"],2)

if __name__=="__main__":
    unittest.main()
