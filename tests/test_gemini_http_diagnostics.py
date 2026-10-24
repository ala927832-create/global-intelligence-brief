"""Ensure Gemini HTTP failures are auditable without exposing credentials."""
import os
import unittest
from unittest.mock import patch
import requests
from gib.gemini_editor_v16 import research_and_revise


class GeminiHttpAuditTests(unittest.TestCase):
    def test_first_pass_http_error_is_redacted_and_classified(self):
        issue={"report_date":"2026-10-24","edition":"morning",
               "articles":[],"research_dossiers":[]}
        response=requests.Response()
        response.status_code=429
        error=requests.HTTPError("PRIVATE GOOGLE API RESPONSE MUST NOT LEAK",response=response)
        opts={"GEMINI_API_KEY":"SECRET_KEY_SHOULD_NOT_APPEAR",
              "ENABLE_GEMINI":"1","GEMINI_FREE_TIER_CONFIRMED":"1"}
        with patch.dict(os.environ,opts), patch("gib.gemini_editor_v16._call",side_effect=error) as call:
            result=research_and_revise(issue)
        self.assertEqual(call.call_count,1)
        self.assertEqual(result["status"],"ERROR_NO_PAID_FALLBACK")
        self.assertEqual(result["failed_stage"],"FIRST_PASS")
        self.assertEqual(result["http_status"],429)
        self.assertEqual(result["warnings"],["GEMINI_HTTP_429"])
        self.assertNotIn("PRIVATE",str(result))
        self.assertNotIn(opts["GEMINI_API_KEY"],str(result))

    def test_missing_free_tier_confirmation_never_calls_model(self):
        issue={"report_date":"2026-10-24","edition":"morning","articles":[]}
        with patch.dict(os.environ,{"ENABLE_GEMINI":"1","GEMINI_FREE_TIER_CONFIRMED":"0"}):
            with patch("gib.gemini_editor_v16._call") as call:
                result=research_and_revise(issue)
        call.assert_not_called()
        self.assertEqual(result["status"],"DISABLED")


if __name__=="__main__":
    unittest.main()
