"""Unit checks for EIA/BLS reconstructible, explicitly unapproved evidence."""
import csv
import tempfile
import unittest
from pathlib import Path
from gib.official_data_rebuild import read_refinery_csv,build_evidence_package,rebuild_bls_revision

CSV=Path(__file__).resolve().parents[1]/"data"/"eia_wpuleus3_may_sep_2025_2026_transcribed.csv"

class OfficialDataRebuildTests(unittest.TestCase):
    def test_weekly_means_and_exact_coverage(self):
        result=build_evidence_package(CSV)
        eia=result["eia"]
        self.assertEqual(eia["number_of_weeks"],{"2025":22,"2026":22})
        self.assertEqual(eia["mean_pct"],{"2025":"93.70","2026":"95.41"})
        self.assertEqual(eia["difference_percentage_points_2026_minus_2025"],"1.70")
        self.assertEqual(eia["max_2026"],{"week_ending":"2026-08-28","utilization_pct":"98.0"})
        self.assertTrue(eia["matches_eia_claim_2026_above_95_pct"])
        self.assertFalse(eia["proves_highest_since_1998"])
        self.assertFalse(result["release_approved"])
        self.assertFalse(result["editorial_gates"]["human_reviewer_signed"])

    def test_bls_revision_is_reconstructed_from_old_and_new(self):
        b=rebuild_bls_revision()
        self.assertEqual(b["july_revision"]["delta"],-31000)
        self.assertEqual(b["august_revision"]["delta"],-29000)
        self.assertEqual(b["july_august_combined_revision_persons"],-60000)
        self.assertTrue(b["matches_bls_stated_combined_revision"])
        self.assertFalse(b["human_signed"])

    def test_missing_or_duplicate_week_must_not_be_published(self):
        with CSV.open(newline="",encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"eia.csv"
            def write(records):
                with p.open("w",encoding="utf-8",newline="") as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(records)
            write(rows[:-1])
            with self.assertRaises(ValueError):read_refinery_csv(p)
            write(rows+[rows[0]])
            with self.assertRaises(ValueError):read_refinery_csv(p)

if __name__=="__main__":
    unittest.main()
