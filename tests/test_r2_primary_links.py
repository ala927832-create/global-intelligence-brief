"""Curated primary research is actual article text provenance, not 'VERIFIED' news."""
import datetime as dt
import io
import unittest
from pypdf import PdfWriter

from gib.r2_evidence_packets import (
    _attach_curated_original_research, _load_issue_manifest,
    fetch_curated_primary_page
)

NOW=dt.datetime(2026,10,29,3,0,tzinfo=dt.timezone.utc)

class CuratedOriginalEvidenceTests(unittest.TestCase):
    def samples(self):
        registry=_load_issue_manifest()
        return [{
            "event_id":key,
            "original_title":item["exact_news_title"],
            "topic":"macro",
            "linked_sources":[],
            "source_domains":[]
        } for key,item in registry.items()]

    def test_four_current_issues_have_six_exact_primary_research_links(self):
        manifest=_load_issue_manifest()
        lookup={doc["url"]:doc for item in manifest.values()
                for doc in item["primary_documents"]}
        def fake(url):
            doc=lookup[url]
            return {
                "text":(" Original primary document dated "+doc["publication_date"]+
                        ": "+" ".join(doc["required_phrases"])),
                "sha256":"a"*64,
                "retrieved_at":NOW.isoformat(),
            }
        packets=self.samples()
        audit=_attach_curated_original_research(packets,NOW,fake,6)
        self.assertEqual(len(packets),4)
        self.assertEqual(len(audit),6)
        self.assertTrue(all(x["status"]=="ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
                            for x in audit),audit)
        self.assertEqual(sum(len(d["curated_original_research"]) for d in packets),6)
        self.assertTrue(all(not doc["claim_fact_checked"]
                            for p in packets for doc in p["curated_original_research"]))
        self.assertTrue(all(not doc["human_reviewed"]
                            for p in packets for doc in p["curated_original_research"]))
        self.assertTrue(all(doc["original_document_date_located"]
                            for p in packets for doc in p["curated_original_research"]))
        # A contrary position may be in a DIFFERENT release by the same
        # issuer (e.g. Bank of Canada governor Q&A vs rate press release).
        self.assertTrue(all(any(doc["contrasting_position_located"]
                                for doc in p["curated_original_research"])
                            for p in packets))

    def test_single_authority_policy_decision_does_not_require_second_original_issuer(self):
        from gib.r2_evidence_packets import _needs_two_distinct_primary_issuers
        registry=_load_issue_manifest()
        fed=registry["518b083502af6be8"]
        canada=registry["5dc602fc74652df4"]
        tanzania=registry["4ada865e9de2e48a"]
        self.assertFalse(_needs_two_distinct_primary_issuers(fed))
        self.assertFalse(_needs_two_distinct_primary_issuers(canada))
        self.assertTrue(_needs_two_distinct_primary_issuers(tanzania))
        # Even when a single issuer is sufficient to prove the announcement,
        # counterarguments, independent interpretation and signing remain open.
        self.assertFalse(fed.get("human_reviewed",False))

    def test_two_bank_documents_do_not_count_as_two_independent_issuers(self):
        from gib.r2_evidence_packets import _distinct_primary_issuer_domains
        bank=[
            {"url":"https://www.bankofcanada.ca/2026/10/decision/"},
            {"url":"https://www.bankofcanada.ca/2026/10/governor/"}
        ]
        self.assertEqual(len(_distinct_primary_issuer_domains(bank)),1)
        different=bank+[{"url":"https://www.nishati.go.tz/news/government"}]
        self.assertEqual(len(_distinct_primary_issuer_domains(different)),2)

    def test_gas_numeric_difference_requires_two_located_hashed_originals(self):
        from gib.r2_evidence_packets import _source_stated_quantity_comparison
        registry=_load_issue_manifest()
        event="4ada865e9de2e48a"
        base={"event_id":event,"curated_original_research":[]}
        missing=_source_stated_quantity_comparison(base,registry)
        self.assertEqual(missing["status"],"HOLD_SOURCE_QUANTITY_PAIR_NOT_LOCATED")
        self.assertTrue(missing["numbers_not_silently_reconciled"])
        source=registry[event]["primary_documents"]
        def doc(spec):
            return {
                "url":spec["url"],"source_kind":spec["source_kind"],
                "source_document_sha256":"a"*64,
                "original_document_date_located":True,
                "manifest_publication_date_not_independently_checked":spec["publication_date"],
                "retrieval_status":"ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED",
                "matched_primary_text_phrases":list(spec["required_phrases"])}
        base["curated_original_research"]=[doc(x) for x in source]
        complete=_source_stated_quantity_comparison(base,registry)
        self.assertEqual(complete["status"],
                         "TWO_ORIGINAL_ISSUER_VOLUME_ESTIMATES_LOCATED_REQUIRES_RECONCILIATION")
        self.assertEqual(complete["absolute_reported_estimate_difference_bcf_approx"],23)
        self.assertFalse(complete["resource_classification_verified"])
        self.assertFalse(complete["difference_explained"])
        self.assertFalse(complete["independent_claim_reviewer_signed"])
        base["curated_original_research"][1]["source_document_sha256"]=None
        with_missing_hash=_source_stated_quantity_comparison(base,registry)
        self.assertEqual(with_missing_hash["status"],"HOLD_SOURCE_QUANTITY_PAIR_NOT_LOCATED")

    def test_original_fed_source_feed_with_only_short_headline_is_not_lost(self):
        from gib.r2_evidence_packets import _original_source_feed_matches
        cutoff=dt.datetime(2026,10,28,23,30,tzinfo=dt.timezone.utc)
        packet=next(p for p in self.samples()
                    if p["event_id"]=="518b083502af6be8")
        original="https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"
        official={
            "title":"Federal Reserve issues FOMC statement",
            "url":original,
            "published_at":"2026-10-28T18:00:00+00:00",
            "official":True,"source_id":"macro_03",
            "snippet":"Federal Reserve issues FOMC statement",
            "provider":"direct_opml_rss"
        }
        hits=_original_source_feed_matches(packet,[official],cutoff)
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]["source_discovery_id"],"macro_03")
        self.assertFalse(hits[0]["claim_fact_checked"])
        self.assertFalse(hits[0]["article_body_retrieved_from_feed"])
        untrusted=dict(official,official=False)
        unrelated=dict(official,url=original+"-unrelated")
        stale=dict(official,published_at="2026-10-01T18:00:00+00:00")
        for invalid in (untrusted,unrelated,stale):
            self.assertFalse(_original_source_feed_matches(packet,[invalid],cutoff))

    def test_source_fetch_always_validates_tls_certificate(self):
        class CheckingSession:
            def get(self,url,**kwargs):
                self.k=kwargs
                raise __import__("requests").exceptions.SSLError("mock certificate chain failure")
        session=CheckingSession()
        with self.assertRaises(__import__("requests").exceptions.SSLError):
            fetch_curated_primary_page("https://www.nishati.go.tz/news/article",session=session)
        self.assertTrue(session.k["verify"])
        self.assertFalse(session.k["allow_redirects"])

    def test_one_longer_bounded_https_request_never_retries_or_downgrades(self):
        import requests
        class SingleCallSession:
            def __init__(self):self.calls=0
            def get(self,url,**kwargs):
                self.calls+=1
                self.options=kwargs
                raise requests.exceptions.ConnectTimeout("simulated publisher timeout")
        s=SingleCallSession()
        with self.assertRaises(requests.exceptions.ConnectTimeout):
            fetch_curated_primary_page(
                "https://www.nim.org/en/press/article/konsumklima-konjunkturerwartungen-steigen-kauflaune-zieht-nicht-mit-1",
                session=s)
        self.assertEqual(s.calls,1)
        self.assertEqual(s.options["timeout"],(12,22))
        self.assertTrue(s.options["verify"])
        self.assertFalse(s.options["allow_redirects"])

    def test_single_source_timeout_is_explicit_hold_not_claim_mismatch(self):
        import requests
        now=NOW
        docs=_load_issue_manifest()
        packets=self.samples()
        allowed=next(x["url"] for x in docs["269bcc066124cf2b"]["primary_documents"])
        def single_fail(url):
            if url==allowed:raise requests.exceptions.ConnectTimeout("NIM temporarily unavailable")
            spec=next(p for item in docs.values() for p in item["primary_documents"]
                      if p["url"]==url)
            return {"text":spec["publication_date"]+" "+" ".join(spec["required_phrases"]),
                    "sha256":"f"*64,"retrieved_at":now.isoformat()}
        audits=_attach_curated_original_research(packets,now,single_fail,6)
        failed=[x for p in packets for x in p["curated_original_research"]
                if x["url"]==allowed]
        self.assertEqual(len(failed),1)
        self.assertEqual(failed[0]["retrieval_status"],
                         "SOURCE_TEMPORARY_NETWORK_TIMEOUT_HOLD")
        self.assertEqual(failed[0]["error_type"],"ConnectTimeout")
        self.assertFalse(failed[0]["claim_fact_checked"])
        self.assertEqual(len(audits),6)

    def test_tanzania_two_independent_original_issuers_keep_volume_difference_unresolved(self):
        registry=_load_issue_manifest()
        tz=next(x for x in registry.values() if x["event_id"]=="4ada865e9de2e48a")
        self.assertEqual(len(tz["primary_documents"]),2)
        self.assertEqual({doc["issuer"] for doc in tz["primary_documents"]},
                         {"Maurel & Prom (operator; primary technical corporate release)",
                          "Tanzania Ministry of Energy (Wizara ya Nishati)"})
        self.assertEqual(tz["estimate_reconciliation"]
                         ["government_reported_gross_volume_bcf"],223)
        self.assertEqual(tz["estimate_reconciliation"]
                         ["operator_preliminary_gross_volume_bcf_approx"],200)
        self.assertTrue(tz["estimate_reconciliation"]
                        ["do_not_confuse_field_estimate_with_proved_reserves"])

    def test_no_matching_news_title_never_receives_an_external_document(self):
        packets=self.samples()
        packets[0]["original_title"]="An unrelated story with same numeric event id"
        calls=[]
        audits=_attach_curated_original_research(
            packets,NOW,lambda url:calls.append(url),0)
        self.assertEqual(calls,[])
        self.assertEqual(packets[0]["curated_original_research"],[])
        self.assertTrue(any(x["status"]=="OFFICIAL_READ_ONLY_BUDGET_REACHED"
                            for x in audits))

    def test_strict_allowlist_rejects_arbitrary_urls_before_network(self):
        for url in ("http://www.federalreserve.gov/", "https://unapproved.example/file",
                    "https://attacker.com@unapproved.example/"):
            with self.assertRaises(ValueError):
                fetch_curated_primary_page(url)

    def test_issuer_pdf_is_parsed_readonly_and_not_fact_certified(self):
        writer=PdfWriter()
        writer.add_blank_page(width=595,height=842)
        buf=io.BytesIO()
        writer.write(buf)
        class Response:
            status_code=200
            headers={"Content-Type":"application/pdf"}
            content=buf.getvalue()
            text=""
            def raise_for_status(self): return None
        class Session:
            def get(self,url,**kwargs):
                self.assertion_url=url
                self.arguments=kwargs
                return Response()
        session=Session()
        source="https://www.maureletprom.fr/en/documents/download/1931/activity-for-the-first-nine-months-of-2026"
        from gib.r2_evidence_packets import fetch_curated_primary_page
        result=fetch_curated_primary_page(source,session=session)
        self.assertEqual(result["text"],"")
        self.assertEqual(result["url"],source)
        self.assertEqual(len(result["sha256"]),64)
        self.assertFalse(session.arguments["allow_redirects"])
        self.assertTrue(session.arguments["verify"])

    def test_cross_newsroom_source_must_be_exact_distinct_domain_same_window(self):
        from gib.r2_evidence_packets import _match_independent_index_for_review
        cutoff=dt.datetime(2026,10,28,23,30,tzinfo=dt.timezone.utc)
        packet=next(p for p in self.samples() if p["event_id"]=="518b083502af6be8")
        packet["source_domains"]=["www.npr.org"]
        exact="Fed leaves interest rates unchanged despite inflation in the US"
        candidate={
            "title":exact,"url":"https://www.aljazeera.com/economy/2026/10/28/fed-holds",
            "published_at":"2026-10-28T19:05:44+00:00",
            "snippet":"A news publisher reported an unchanged target range while inflation remains elevated."
        }
        hits=_match_independent_index_for_review(packet,[candidate],cutoff)
        self.assertEqual(len(hits),1)
        self.assertFalse(hits[0]["independent_fact_corroboration_verified"])
        self.assertFalse(hits[0]["article_body_retrieved"])
        same=dict(candidate,url="https://www.npr.org/similar-title")
        stale=dict(candidate,published_at="2026-10-27T08:00:00+00:00")
        vaguely_similar=dict(candidate,title="Fed leaves policy unchanged but dollar moves")
        self.assertEqual(_match_independent_index_for_review(
            packet,[same,stale,vaguely_similar],cutoff),[])
        wrong=dict(packet,original_title="Unrelated headline same event id")
        self.assertEqual(_match_independent_index_for_review(
            wrong,[candidate],cutoff),[])

    def test_fetched_page_without_claim_text_is_not_promoted(self):
        p=self.samples()
        log=_attach_curated_original_research(
            p,NOW,lambda url:{
                "text":"unrelated generic homepage with no matched claim",
                "sha256":"b"*64,"retrieved_at":NOW.isoformat()
            },6)
        self.assertEqual(len(log),6)
        self.assertTrue(all(x["status"]=="PAGE_RETRIEVED_NO_EXACT_CLAIM_MATCH"
                            for x in log))
        self.assertEqual(sum(bool(doc["matched_primary_text_phrases"])
                             for row in p for doc in row["curated_original_research"]),0)

if __name__=="__main__":
    unittest.main()
