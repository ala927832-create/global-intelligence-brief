"""Do not misclassify equivalent source dates while rejecting added statistics."""
import unittest
from gib.gemini_editor_v16 import unsupported_numeric_evidence

class NumericEvidenceTests(unittest.TestCase):
    def test_allowed_equivalent_dates_only(self):
        original="The report was published 2026-10-02. Utilization highest since 1998."
        self.assertEqual(unsupported_numeric_evidence(
            "報告在2026年10月2日發布，是98年以來同期最高水準。",original),[])
    def test_new_rate_still_blocked(self):
        original="Report 2026-10-02; highest since 1998; share 95%."
        candidates=["失業率為2%。", "煉油利用率為98%。",
                    "新增48,000人。"]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.assertTrue(unsupported_numeric_evidence(candidate,original))
    def test_recognizes_other_numbers_with_units(self):
        original="Payrolls increased 29,000 and unemployment rate 4.2 percent."
        self.assertEqual(unsupported_numeric_evidence("新增29,000人、失業率4.2%。",original),[])
        self.assertTrue(unsupported_numeric_evidence("新增200,000人。",original))

if __name__=="__main__":
    unittest.main()
