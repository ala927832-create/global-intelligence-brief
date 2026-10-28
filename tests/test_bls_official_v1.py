"""BLS public v1 numeric series; date fidelity, no claim of news-release timestamps."""
import datetime as dt
import unittest
from unittest.mock import Mock
import requests
from qa.bls_official_v1 import parse_bls_payload, fetch_bls, SERIES, API_URL

class BlsOfficialV1Tests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,28,0,0,tzinfo=dt.timezone.utc)
        self.fixture={"status":"REQUEST_SUCCEEDED",
                      "Results":{"series":[
                        {"seriesID":sid,"data":[
                            {"year":"2026","period":"M09","value":"155.2","footnotes":[{"code":"P","text":"Preliminary."}]},
                            {"year":"2026","period":"M13","value":"1000","footnotes":[]},
                            {"year":"2027","period":"M01","value":"777","footnotes":[]}
                        ]} for sid in SERIES]}}
    def test_four_official_series_keep_observation_period_not_release_date(self):
        x=parse_bls_payload(self.fixture,self.now)
        self.assertEqual(x["status"],"OFFICIAL_SERIES_OK")
        self.assertEqual(set(x["series"]),set(SERIES))
        self.assertFalse(x["official_release_timestamp_in_api"])
        self.assertFalse(x["release_approved"])
        for sid,row in x["series"].items():
            self.assertEqual(row["latest"]["observation_period"],"2026-09")
            self.assertEqual(row["latest"]["value"],155.2)
            self.assertEqual(row["observations_returned"],1)
            self.assertEqual(row["latest"]["footnotes"][0]["code"],"P")
    def test_missing_one_series_is_never_reported_as_full_success(self):
        fixture={**self.fixture,"Results":{"series":self.fixture["Results"]["series"][:-1]}}
        x=parse_bls_payload(fixture,self.now)
        self.assertEqual(x["status"],"PARTIAL_OFFICIAL_SERIES")
        self.assertEqual(len(x["missing_series"]),1)
    def test_http_403_is_explicit_not_fake_data(self):
        response=Mock(status_code=403)
        err=requests.HTTPError(response=response)
        r=Mock()
        r.post.side_effect=err
        status=fetch_bls(session=r)
        self.assertEqual(status["status"],"HTTP_403")
        self.assertFalse(status["release_approved"])
    def test_bls_sends_one_batched_keyless_request(self):
        response=Mock()
        response.raise_for_status.return_value=None
        response.json.return_value=self.fixture
        client=Mock()
        client.post.return_value=response
        r=fetch_bls(session=client)
        self.assertEqual(r["status"],"OFFICIAL_SERIES_OK")
        kwargs=client.post.call_args.kwargs
        self.assertEqual(set(kwargs["json"]["seriesid"]),set(SERIES))
        self.assertNotIn("registrationkey",kwargs["json"])
        self.assertEqual(client.post.call_args.args[0],API_URL)
    def test_reject_incomplete_payload(self):
        self.assertEqual(parse_bls_payload({},self.now)["status"],"BLS_API_NOT_SUCCESSFUL")
        self.assertEqual(parse_bls_payload({"status":"REQUEST_SUCCEEDED","Results":{}},self.now)["status"],"INVALID_RESPONSE")

if __name__=="__main__":
    unittest.main()
