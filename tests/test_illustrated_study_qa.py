"""Validate official counter-evidence and offline study navigation (no API use)."""
import copy
import json
import unittest
from pathlib import Path
from lxml import etree
from gib.official_data_rebuild import build_evidence_package
from gib.publish_v16 import as_xhtml
from scripts.build_two_case_illustrated_reader_qa import load_counterdata, two_study_sections

ROOT=Path(__file__).resolve().parents[1]

class IllustratedEvidenceReaderTests(unittest.TestCase):
    def test_reconstructs_counterinterpretation_from_official_snapshots(self):
        bls,eia,c=load_counterdata()
        self.assertEqual(c["civilian_labor_force_thousands"],485)
        self.assertEqual(c["employed_thousands"],406)
        self.assertEqual(c["unemployed_thousands"],78)
        self.assertEqual(round(100*eia["gross_inputs_thousand_bpd"]/eia["operable_capacity_thousand_bpd"],1),98.0)
        self.assertIs(bls["human_signed"],False)
        self.assertIs(eia["publication_approved"],False)

    def test_research_stays_unapproved_and_has_full_navigation(self):
        packet=json.loads((ROOT/"samples"/"official_two_case_20261024.json").read_text("utf-8"))
        arith=build_evidence_package(ROOT/"data"/"eia_wpuleus3_may_sep_2025_2026_transcribed.csv")
        bls,eia,c=load_counterdata()
        packet["deep_research"]=two_study_sections(arith,{"status":"OFFICIAL_HISTORY_NOT_RECONSTRUCTED"},bls,eia,c)
        packet["editorial_status"]="REVIEW_REQUIRED"
        packet["research_source_manifest"]=[{"source":"https://www.eia.gov/petroleum/data.php",
                                               "kind":"official source"}]
        root=etree.fromstring(as_xhtml(packet,[],"deep").encode("utf-8"))
        ids=set(root.xpath("//@id"))
        for k in ("executive","world","analysis","deep-research","watch","sources"):
            self.assertIn(k,ids)
        for id_ in ("eia_refinery_20261022","bls_employment_20261002"):
            self.assertIn("research-"+id_,ids)
        html=etree.tostring(root,encoding="unicode")
        self.assertIn("QA／非正式刊物",html)
        self.assertIn("具名",html)
        self.assertIn("補充原始資料",html)
        self.assertNotIn("30–45 分鐘深讀</",html)

if __name__=="__main__":
    unittest.main()
