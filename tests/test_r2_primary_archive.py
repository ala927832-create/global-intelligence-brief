"""Real prior run SHA provenance must NEVER replace current source or editor proof."""
import datetime as dt
import json
import unittest
from pathlib import Path
from gib.r2_evidence_packets import (
    _historical_original_document_provenance, _load_issue_manifest,
    R2_PROVENANCE_ARCHIVE
)

class ArchivedOriginalProofTests(unittest.TestCase):
    def fixture(self):
        archive=json.loads(R2_PROVENANCE_ARCHIVE.read_text(encoding="utf-8"))
        self.assertEqual(archive["generated_from_actual_github_actions_run_id"],40808266483)
        self.assertEqual(len(archive["original_documents"]),6)
        docs={}
        for r in archive["original_documents"]:
            docs.setdefault(r["event_id"],[]).append({
                "url":r["url"],
                "retrieval_status":"SOURCE_TEMPORARY_NETWORK_TIMEOUT_HOLD",
                "source_document_sha256":None,
                "matched_primary_text_phrases":[],
                "claim_fact_checked":False
            })
        return [{"event_id":k,"curated_original_research":v} for k,v in docs.items()]

    def test_historical_real_checksums_are_separate_from_unavailable_live_sources(self):
        packets=self.fixture()
        now=dt.datetime(2026,10,29,4,0,tzinfo=dt.timezone.utc)
        out=_historical_original_document_provenance(packets,now)
        self.assertEqual(out["attached"],6)
        self.assertFalse(out["gemini_allowed"])
        self.assertEqual(out["status"],"PRIOR_PROVENANCE_LINKED_NOT_CURRENT_EVIDENCE")
        for p in packets:
            for doc in p["curated_original_research"]:
                previous=doc["historical_matched_original_document"]
                self.assertEqual(previous["github_actions_run_id"],40808266483)
                self.assertEqual(len(previous["source_document_sha256"]),64)
                self.assertFalse(previous["current_run_retrieval_proven"])
                self.assertFalse(previous["human_editorial_signoff"])
                self.assertIsNone(doc["source_document_sha256"])
                self.assertFalse(doc["claim_fact_checked"])
                self.assertEqual(doc["retrieval_status"],"SOURCE_TEMPORARY_NETWORK_TIMEOUT_HOLD")

    def test_cannot_attest_future_archived_fetch_to_earlier_snapshot(self):
        packets=self.fixture()
        now=dt.datetime(2026,10,29,1,0,tzinfo=dt.timezone.utc)
        out=_historical_original_document_provenance(packets,now)
        self.assertEqual(out["attached"],0)
        self.assertFalse(any("historical_matched_original_document" in doc
                             for p in packets for doc in p["curated_original_research"]))

if __name__=="__main__":unittest.main()
