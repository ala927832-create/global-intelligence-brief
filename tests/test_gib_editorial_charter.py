"""Regression protection for the GIB owner-approved 2026-10-23 global editorial charter."""
import json
import unittest
from pathlib import Path

class FrozenGlobalEditorialCharterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads(Path("config/frozen_contract.json").read_text(encoding="utf-8"))
        cls.daily=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))
        cls.refs=json.loads(Path("config/specialist_official_references.json").read_text(encoding="utf-8"))

    def test_original_six_sections_and_dual_depth_are_untouched(self):
        self.assertEqual(self.contract["contract_version"],"2026-10-23-approved-v1")
        self.assertEqual(self.contract["change_policy"],"OWNER_CONFIRMATION_REQUIRED_BEFORE_CHANGING_ANY_FIELD")
        self.assertEqual([x["name"] for x in self.contract["sections"]],[
            "Executive Brief","The World in Brief","Essential Analysis","Deep Research",
            "What Changed & What to Watch","Sources & Evidence"])
        self.assertEqual([x["minutes"] for x in self.contract["versions"]],["10-15","30-45"])
        self.assertEqual(self.contract["zinc_policy"],
                         "READ_ONLY_PUBLIC_VERIFIED_CROSS_MARKET_SIGNALS_ONLY; ORIGINAL_REPO_UNCHANGED")
        self.assertEqual(self.contract["publishing"],"OFF_UNTIL_QUALITY_AND_OWNER_APPROVAL")

    def test_exact_original_user_opml_daily_feed_inventory(self):
        feeds=self.daily["feeds"]
        self.assertEqual(len(feeds),24)
        self.assertEqual(len({x["url"] for x in feeds}),24)
        by_lane={k:sum(f["lane"]==k for f in feeds) for k in ("global","macro","energy_commodities","taiwan")}
        self.assertEqual(by_lane,{"global":9,"macro":6,"energy_commodities":3,"taiwan":6})
        self.assertFalse(any(x["id"].startswith("taiwan_ida_") for x in feeds))
        self.assertFalse(any("ida.gov.tw" in x["url"] for x in feeds))
        self.assertEqual(self.daily["imported_from"],"Inoreader Feeds 20261028.xml")

    def test_supplemental_source_watchlist_has_no_editorial_ranks(self):
        refs=self.refs["sources"]
        self.assertGreaterEqual(len(refs),15)
        self.assertTrue(all(x.get("editorial_role")=="SPECIALIST_EVIDENCE_REFERENCE_ONLY" for x in refs))
        self.assertTrue(all("priority" not in x and "frequency" not in x for x in refs))
        ids={x["id"] for x in refs}
        self.assertTrue({"ida_press_reference","ida_regulations_reference",
                         "ida_policy_reference","lme_zinc_prices",
                         "worldsteel_press","aga_galvanizing"}<=ids)

    def test_no_specialist_override_of_global_newsworthiness(self):
        self.assertIn("GLOBAL_NEWSWORTHINESS_NOT_PERSONAL_BUSINESS_RELEVANCE",
                      {x["selection_rule"] for x in self.refs["sources"]})
        text=Path("AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("frozen_contract.json",text)
        self.assertIn("Source groups are NOT editorial desks or importance weights",text)
        self.assertIn("The World in Brief",text)

if __name__=="__main__":
    unittest.main()
