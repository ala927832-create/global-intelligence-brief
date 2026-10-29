"""GIB V3 R2: evidence-first dossiers, BEFORE editorial drafting or Gemini.

Only real already-approved source-index rows and bounded, explicitly allowlisted
official source pages. Never transform index descriptions into verified facts,
counterclaims, causal conclusions, research prose or publication approval.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

import requests
from gib.newsroom_v16 import canonical_issue
from gib.evidence_review import (
    APPROVED_HOSTS, MAX_BYTES, VisibleText, normalize_text,
    review_official_excerpts, fetch_official_page
)
from qa.p2_content_gate import eligible_source_rows, source_input_gate, selected_story_gate
from qa.r2_evidence_preflight import latest_morning_cutoff


# Dedicated, narrowly pre-approved original-research document URLs.
# NOT an extension of the 24 RSS feeds or official_rss source providers.
R2_PRIMARY_HOSTS = frozenset({
    "www.federalreserve.gov", "www.bankofcanada.ca",
    "www.nim.org", "www.maureletprom.fr", "nishati.go.tz", "www.nishati.go.tz"
})
R2_MANIFEST = (Path(__file__).resolve().parents[1] /
               "config/r2_primary_research_links_20261029.json")


def fetch_curated_primary_page(url, session=None):
    """Bounded original research document, no redirect/crawl/full-text archive."""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in R2_PRIMARY_HOSTS
            or parsed.port not in (None, 443)
            or parsed.username or parsed.password):
        raise ValueError("R2_ORIGINAL_DOCUMENT_NOT_ALLOWLISTED")
    client = session or requests.Session()
    response = client.get(
        # A publisher occasionally needs longer TLS connection setup.
        # One bounded HTTPS request only; never disable TLS, redirect, repeat
        # failed calls automatically, or expand approved document count.
        url, timeout=(12, 22), allow_redirects=False, verify=True,
        headers={"User-Agent": "GIB-R2-Source-Verification/1.0",
                 "Accept": "text/html,text/plain,application/xhtml+xml,application/pdf"})
    response.raise_for_status()
    if response.status_code in (301, 302, 303, 307, 308):
        raise ValueError("R2_REDIRECT_REQUIRES_SEPARATE_VALIDATION")
    if len(response.content) > MAX_BYTES:
        raise ValueError("R2_DOCUMENT_TOO_LARGE")
    kind = response.headers.get("Content-Type", "").lower()
    if not any(t in kind for t in ("text/html","application/xhtml","text/plain","application/pdf")):
        raise ValueError("R2_UNSUPPORTED_PRIMARY_DOCUMENT_TYPE")
    if "application/pdf" in kind:
        # Original issuer PDF only, <=800KB and <=8 pages: do not store or
        # mirror the copyrighted full PDF/text in the evidence artifact.
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(response.content), strict=False)
        if reader.is_encrypted or len(reader.pages) > 8:
            raise ValueError("R2_PDF_ENCRYPTED_OR_TOO_MANY_PAGES")
        body = normalize_text(" ".join(
            (page.extract_text() or "") for page in reader.pages))[:80000]
    else:
        parsed_text = VisibleText()
        if "html" in kind:
            parsed_text.feed(response.text)
            body = normalize_text(" ".join(parsed_text.parts))
        else:
            body = normalize_text(response.text)
    return {
        "url": url, "text": body,
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat()
    }


def _load_issue_manifest():
    # Hardcoded manifest path; no user-controlled file or arbitrary URL fetch.
    with R2_MANIFEST.open(encoding="utf-8") as file:
        data = json.load(file)
    if data.get("schema") != "GIB_R2_CURRENT_ISSUE_PRIMARY_RESEARCH_URLS_V1":
        raise ValueError("R2_RESEARCH_MANIFEST_SCHEMA_NOT_APPROVED")
    return {x["event_id"]: x for x in data["selected_events"]}


def _attach_curated_original_research(packets, now, fetcher, budget):
    """Locate explicitly identified primary content and record EXACT proof limits.

    A page-text match is evidence of document provenance only. It does not
    certify the original newspaper's interpretation, economic transmission,
    causation, authenticity of other outlets or an independent counterclaim.
    """
    registry = _load_issue_manifest()
    audits = []
    used = 0
    for packet in packets:
        packet["curated_original_research"] = []
        manifest = registry.get(packet["event_id"])
        if not manifest or manifest["exact_news_title"] != packet["original_title"]:
            continue
        packet["research_subject"] = manifest["research_subject"]
        packet["counterevidence_question"] = manifest["counterevidence_search"]
        packet["causal_mechanism_to_validate"] = manifest["causal_mechanism_to_test"]
        for spec in manifest["primary_documents"]:
            row = {
                "url": spec["url"], "issuer": spec["issuer"],
                "source_kind": spec["source_kind"],
                "source_location_hint": spec.get("locator_hint"),
                "manifest_publication_date_not_independently_checked":
                    spec["publication_date"],
                "retrieval_status": "NOT_FETCHED",
                "source_document_sha256": None,
                "retrieved_at_utc": None,
                "matched_primary_text_phrases": [],
                "unmatched_primary_text_phrases": [],
                "original_document_date_located": False,
                "contrasting_position_located": False,
                "observation_located_not_causality_proven": False,
                "human_reviewed": False, "claim_fact_checked": False
            }
            packet["curated_original_research"].append(row)
            try:
                source_date = dt.date.fromisoformat(spec["publication_date"])
                if source_date > now.astimezone(dt.timezone.utc).date():
                    row["retrieval_status"] = "PRIMARY_SOURCE_DATED_IN_FUTURE"
                    audits.append({"event_id": packet["event_id"],
                                   "url":spec["url"],"status":row["retrieval_status"]})
                    continue
            except (ValueError, KeyError):
                row["retrieval_status"] = "PRIMARY_SOURCE_DATE_INVALID"
                audits.append({"event_id": packet["event_id"],
                               "url":spec["url"],"status":row["retrieval_status"]})
                continue
            if used >= budget:
                row["retrieval_status"] = "OFFICIAL_READ_ONLY_BUDGET_REACHED"
                audits.append({"event_id": packet["event_id"],"url": spec["url"],
                               "status":row["retrieval_status"]})
                continue
            used += 1
            try:
                page = fetcher(spec["url"])
                original = normalize_text(page["text"])
                if not original or len(page["sha256"]) < 32:
                    raise ValueError("R2_EMPTY_OR_UNHASHED_DOCUMENT")
                lower = original.casefold()
                d = source_date
                possible_dates = [
                    d.isoformat(),
                    f"{d.strftime('%B')} {d.day}, {d.year}",
                    f"{d.day} {d.strftime('%B')} {d.year}",
                    f"{d.strftime('%b')} {d.day}, {d.year}",
                    f"{d.day}th {d.strftime('%b')}, {d.year}",
                    f"{d.day} Oktoba, {d.year}",
                    f"{d.day} Oktoba {d.year}"
                ]
                row["original_document_date_located"] = any(
                    date.casefold() in lower for date in possible_dates)
                for phrase in spec["required_phrases"]:
                    fragment = normalize_text(phrase)
                    if len(fragment) >= 12 and fragment.casefold() in lower:
                        row["matched_primary_text_phrases"].append(fragment)
                    else:
                        row["unmatched_primary_text_phrases"].append(fragment)
                # The presence of an alternate stance or observation in
                # a *single original issuer* is not an independently confirmed
                # opposing explanation or causal mechanism.
                opposite = normalize_text(
                    manifest.get("contrasting_original_source_phrase"))
                measured = normalize_text(
                    manifest.get("original_observation_phrase"))
                row["contrasting_position_located"] = bool(
                    opposite and opposite.casefold() in lower)
                row["observation_located_not_causality_proven"] = bool(
                    measured and measured.casefold() in lower)
                row["source_document_sha256"] = page["sha256"]
                row["retrieved_at_utc"] = page["retrieved_at"]
                row["retrieval_status"] = (
                    "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
                    if row["matched_primary_text_phrases"]
                    else "PAGE_RETRIEVED_NO_EXACT_CLAIM_MATCH")
                row["primary_document_directly_accessed"] = True
            except requests.exceptions.SSLError:
                # Explicit TLS failure rather than a generic missing source.
                # Do NOT retry via HTTP or disable certificate validation.
                row["retrieval_status"] = "SOURCE_TLS_CERTIFICATE_REJECTED"
                row["error_type"] = "SSLError"
                row["claim_fact_checked"] = False
            except (requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout) as error:
                # Distinguish a temporary source outage from false facts or
                # a claim mismatch. Never promote this into verified evidence.
                row["retrieval_status"] = "SOURCE_TEMPORARY_NETWORK_TIMEOUT_HOLD"
                row["error_type"] = type(error).__name__
                row["claim_fact_checked"] = False
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                row["retrieval_status"] = "SOURCE_FETCH_OR_MATCH_FAILED"
                row["error_type"] = type(error).__name__
            audits.append({
                "event_id": packet["event_id"], "url": spec["url"],
                "status": row["retrieval_status"],
                "matched_claim_phrases": len(row["matched_primary_text_phrases"])
            })
    return audits



def _original_source_feed_matches(packet, index_rows, cutoff):
    """Locate a curated issuer URL already carried by the original RSS index.

    RSS discovery is distinct from fetching a full, hashable official page.
    An exact issuer URL and valid source timestamp support provenance, not
    independent editorial certification. Crucially, do not apply G0's 50-char
    news-excerpt threshold: many official RSS feeds only provide short titles.
    """
    manifest=_load_issue_manifest().get(packet.get("event_id"))
    if not manifest or manifest.get("exact_news_title")!=packet.get("original_title"):
        return []
    expected={d["url"] for d in manifest.get("primary_documents",[])}
    hits=[]
    seen=set()
    begin=cutoff-dt.timedelta(hours=14)
    for item in index_rows:
        url=item.get("url")
        if url not in expected or url in seen:
            continue
        if not item.get("official"):
            continue
        try:
            source_date=dt.datetime.fromisoformat(
                str(item.get("published_at") or "").replace("Z","+00:00"))
            if source_date.tzinfo is None or not begin<source_date<=cutoff:
                continue
        except (TypeError,ValueError):
            continue
        seen.add(url)
        hits.append({
            "issuer_url":url,
            "original_source_feed_title":str(item.get("title") or "")[:250],
            "source_discovery_id":item.get("source_id"),
            "source_published_at_utc":source_date.astimezone(dt.timezone.utc).isoformat(),
            "discovery_provider":item.get("provider"),
            "source_excerpt_sha256":_sha(item.get("snippet") or ""),
            "official_feed_url_matched":True,
            "claim_fact_checked":False,
            "article_body_retrieved_from_feed":False
        })
    return hits




def _needs_two_distinct_primary_issuers(manifest):
    """Only explicit two-origin disputes require two original issuers."""
    return bool(((manifest or {}).get("estimate_reconciliation") or {}).get(
        "numerical_discrepancy_must_not_be_silently_resolved"))


def _distinct_primary_issuer_domains(docs):
    """Two pages on one institution domain do not make two issuers."""
    return {urlsplit(d.get("url") or "").hostname for d in docs
            if urlsplit(d.get("url") or "").scheme=="https" and
               urlsplit(d.get("url") or "").hostname}


def _source_stated_quantity_comparison(packet, registry):
    """A paired *source-stated* numeric discrepancy, not a resolved reserve.

    Each participating observation must appear literally in two successfully
    matched, independently published, hashed primary documents. Never use a
    prefilled manifest number alone as evidence.
    """
    spec=registry.get(packet.get("event_id")) or {}
    context=spec.get("estimate_reconciliation") or {}
    if not context or not context.get("numerical_discrepancy_must_not_be_silently_resolved"):
        return None
    source_docs=[doc for doc in packet.get("curated_original_research",[])
                 if doc.get("retrieval_status") ==
                 "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
                 and doc.get("original_document_date_located")
                 and doc.get("source_document_sha256")]
    operator=next((doc for doc in source_docs
                   if doc.get("source_kind")=="OPERATING_COMPANY_PRIMARY_PDF_RELEASE"
                   and any("approximately 200 bcf gross" in t.lower()
                           for t in doc.get("matched_primary_text_phrases",[]))),None)
    government=next((doc for doc in source_docs
                     if doc.get("source_kind")=="TANZANIA_GOVERNMENT_PRIMARY_RELEASE"
                     and any("billion 223" in t.lower()
                             for t in doc.get("matched_primary_text_phrases",[]))),None)
    if not operator or not government:
        return {
            "status":"HOLD_SOURCE_QUANTITY_PAIR_NOT_LOCATED",
            "independently_located_issuer_documents":len({urlsplit(d["url"]).hostname for d in source_docs}),
            "numbers_not_silently_reconciled":True,
            "classification_not_assumed":True
        }
    a=context["government_reported_gross_volume_bcf"]
    b=context["operator_preliminary_gross_volume_bcf_approx"]
    if not (a==223 and b==200):
        return {"status":"HOLD_MANIFEST_QUANTITY_MISMATCH",
                "numbers_not_silently_reconciled":True}
    # Difference is an arithmetic description of TWO reported estimates,
    # not a gas resource revision, and must never be labeled certified reserves.
    return {
        "status":"TWO_ORIGINAL_ISSUER_VOLUME_ESTIMATES_LOCATED_REQUIRES_RECONCILIATION",
        "government_source_stated_bcf":a,
        "operator_source_stated_approx_gross_bcf":b,
        "absolute_reported_estimate_difference_bcf_approx":abs(a-b),
        "units":"billion cubic feet (reported estimates, not certified reserves)",
        "government_source":{"url":government["url"],
                             "source_sha256":government["source_document_sha256"],
                             "source_date_not_editor_certified":government["manifest_publication_date_not_independently_checked"]},
        "operator_source":{"url":operator["url"],
                           "source_sha256":operator["source_document_sha256"],
                           "source_date_not_editor_certified":operator["manifest_publication_date_not_independently_checked"]},
        "same_underlying_volume_basis_proven":False,
        "resource_classification_verified":False,
        "difference_explained":False,
        "independent_claim_reviewer_signed":False,
        "causal_prediction_permitted":False
    }



def _match_independent_index_for_review(packet, all_eligible_rows, cutoff):
    """Exact same-window *potential* publisher match, NOT verified corroboration.

    Do not count unlocated source articles or similarly themed but unrelated
    news stories as an independent assertion. Only previously identified
    source-index titles can be selected, with a different original domain.
    """
    registry=_load_issue_manifest()
    spec=registry.get(packet["event_id"])
    if not spec or spec.get("exact_news_title")!=packet["original_title"]:
        return []
    trusted_titles=set(spec.get("independent_original_news_index_titles") or [])
    if not trusted_titles: return []
    original=set(packet.get("source_domains") or [])
    hits=[]
    seen=set()
    start=cutoff-dt.timedelta(hours=14)
    for row in all_eligible_rows:
        if row.get("title") not in trusted_titles:
            continue
        url=row.get("url") or ""
        host=urlsplit(url).hostname
        if (urlsplit(url).scheme!="https" or not host or
                host in original or (host,url) in seen):
            continue
        try:
            stamp=dt.datetime.fromisoformat(
                str(row.get("published_at","")).replace("Z","+00:00"))
            if stamp.tzinfo is None or not start<stamp<=cutoff:
                continue
        except (TypeError,ValueError):
            continue
        seen.add((host,url))
        hits.append({
            "source_index_title":row["title"],
            "original_news_url":url,
            "publisher_domain":host,
            "article_published_at_utc":stamp.astimezone(dt.timezone.utc).isoformat(),
            "source_excerpt_sha256":_sha(str(row.get("snippet") or "")[:350]),
            "source_excerpt_short":str(row.get("snippet") or "")[:350],
            "independent_fact_corroboration_verified":False,
            "article_body_retrieved":False,
            "claim_by_claim_reconciliation":"REQUIRES_HUMAN_SOURCE_REVIEW"
        })
    return hits


def _sha(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _publisher_domains(sources):
    return sorted({urlsplit(s.get("url", "")).hostname for s in sources
                   if urlsplit(s.get("url", "")).scheme == "https"
                   and urlsplit(s.get("url", "")).hostname})


def choose_focus(issue, count=4):
    """Choose four DIFFERENT editorial topics among actual main stories.

    Prefer material news with directly linked authorized official sources, but
    never replace original index texts, claim new proof, or force a fourth topic.
    """
    mains = [x for x in issue.get("articles", []) if x.get("editorial_tier") == "main"]
    eligible = sorted(enumerate(mains), key=lambda p: (
        -int(any(s.get("kind") == "OFFICIAL_FEED" and
                 urlsplit(s.get("url", "")).hostname in APPROVED_HOSTS
                 for s in p[1].get("sources", []))),
        -min(len(_publisher_domains(p[1].get("sources", []))), 3),
        p[0]))
    chosen = []
    topics = set()
    for _, article in eligible:
        if article.get("topic") not in topics:
            chosen.append(article)
            topics.add(article.get("topic"))
        if len(chosen) == count:
            break
    return chosen


def _snapshot(article):
    """Preserve bounded publisher source excerpts, not copyrighted articles."""
    sources = article.get("sources") or []
    return {
        "event_id": article.get("event_id"),
        "topic": article.get("topic"),
        "original_title": article.get("title_original"),
        "article_publication_utc": article.get("article_published_at"),
        "event_occurrence_utc": article.get("event_time_utc"),
        "source_excerpt": str(article.get("headline_summary") or "")[:450],
        "source_excerpt_sha256": _sha(article.get("headline_summary")),
        "source_index_status": "SOURCE_ATTRIBUTED_UNVERIFIED",
        "linked_sources": [{
            "source_id": s.get("source_id"),
            "url": s.get("url"),
            "original_domain": urlsplit(s.get("url", "")).hostname,
            "publisher": s.get("publisher"),
            "publication_utc": s.get("article_published_at"),
            "kind": s.get("kind"),
            "retrieval_status": s.get("retrieval_status"),
            "primary_document_sha256": s.get("source_sha256"),
            "retrieved_at_utc": s.get("retrieved_at")
        } for s in sources],
        "source_domains": _publisher_domains(sources)
    }


def _dossier(article):
    index = _snapshot(article)
    claims = article.get("evidence") or []
    official_excerpts = []
    for c in claims:
        if c.get("verification") in (
                "SOURCE_EXCERPT_MATCH_NOT_FACT_VERIFIED",
                "OFFICIAL_CONTEXT_UNVERIFIED"):
            official_excerpts.append({
                "claim_id": c.get("claim_id"),
                "source_id": c.get("source_id"),
                "source_location": c.get("source_location"),
                "primary_document_sha256": c.get("source_sha256"),
                "retrieved_at_utc": c.get("retrieved_at"),
                "excerpt": str(c.get("official_context_excerpt") or "")[:900],
                "verification": c.get("verification")
            })
    verified_claims = [c for c in claims if c.get("verification") == "VERIFIED"
                       and c.get("reviewer") and c.get("source_sha256")
                       and c.get("source_location") not in (None, "", "feed headline/snippet")]
    blocked = []
    if not article.get("event_time_utc"):
        blocked.append("EVENT_OCCURRENCE_DATE_NOT_INDEPENDENTLY_ESTABLISHED")
    if not official_excerpts:
        blocked.append("MATCHED_PRIMARY_DOCUMENT_EXCERPT_NOT_LOCATED")
    if len(index["source_domains"]) < 2:
        blocked.append("SECOND_PUBLISHER_SOURCE_NOT_LOCATED")
    # Two publishers may both syndicate the same agency story. An additional
    # domain alone NEVER counts as independent confirmation.
    blocked.extend([
        "SOURCE_BY_SOURCE_INDEPENDENT_CORROBORATION_NOT_REVIEWED",
        "COUNTEREVIDENCE_WITH_SOURCE_LOCATION_NOT_VERIFIED",
        "CAUSAL_MECHANISM_AND_DATA_SERIES_NOT_VERIFIED"])
    if len(verified_claims) < 3:
        blocked.append("THREE_MANUALLY_ATTESTED_FACT_CLAIMS_MISSING")
    return {
        **index,
        "candidate_claims": [{
            "claim_id": c.get("claim_id"),
            "source_id": c.get("source_id"),
            "claimed_text": str(c.get("text") or "")[:450],
            "verification": c.get("verification"),
            "located_source": c.get("source_location"),
            "reviewer": c.get("reviewer"),
            "document_sha256": c.get("source_sha256"),
        } for c in claims],
        "primary_official_context_not_fact_verified": official_excerpts,
        "potential_counterevidence": [],  # Do NOT manufacture a dissenting claim.
        "causal_mechanism_evidence": [],
        "independently_corroborated_claims": 0,
        "signed_verified_claims": len(verified_claims),
        "research_question_templates": {
            "underlying_primary_document": "Identify the signed official release, dataset, exact table/page and observation date",
            "principal_claim": "Which statement can be matched exactly and what is the unit, baseline and attribution?",
            "opposing_explanation": "Which distinct published primary source or dataset contradicts/qualifies the claim?",
            "causal_mechanism": "What measurable sequence connects the stated event to the hypothesized outcome?",
            "falsification": "Which dated series or subsequent disclosure would overturn the preferred hypothesis?",
        },
        "evidence_ready_for_gemini": False,
        "blockers": blocked,
    }


def build_packets(rows, now, weights=None, fetcher=None, max_documents=6, curated_fetcher=None):
    """Extract four analysis dossiers + two studies from the SAME real R1 index.

    A passed count gate permits *research triage*, not drafting. Fetcher can be
    injected by deterministic tests; live runs use the official allowlist only.
    """
    cutoff = latest_morning_cutoff(now)
    gate = source_input_gate(rows, cutoff, "morning", observed_at=now)
    eligible, _, _, _ = eligible_source_rows(rows, cutoff, "morning")
    issue = canonical_issue(eligible, "morning", cutoff,
                            weights or {}, tiered_v3=True,
                            require_material_relevance=False)
    selected = selected_story_gate(issue)
    source_blockers = [x for x in gate["blockers"]
                       if not x.startswith(("RETROSPECTIVE_CAPTURE_",
                                            "SOURCE_SNAPSHOT_BEFORE_"))]
    blockers = source_blockers + selected["blockers"]
    output = {
        "kind": "GIB_R2_FOUR_ANALYSIS_AND_TWO_STUDY_EVIDENCE_PACKET",
        "captured_source_window_cutoff_utc": cutoff.isoformat(),
        "retrospective_not_cutoff_capture": True,
        "source_index_rows": len(rows),
        "g0_distinct_candidates": gate["distinct_evidence_bearing_events"],
        "g1_selected_events": selected["unique_events"],
        "g1_main_news": selected["main_news"],
        "g1_supplementary_news": selected["supplementary_news"],
        "structural_r1_blockers": blockers,
        "analysis_packets": [],
        "current_deep_research_shortlist": [],
        "primary_source_fetch_results": [],
        "independent_fact_signoff": False,
        "gemini_first_pass_allowed": False,
        "gemini_second_pass_allowed": False,
        "gemini_called": False,
        "generated_reader_files": False,
        "release_approved": False
    }
    if blockers:
        output["status"] = "HOLD_R1_STRUCTURE_BEFORE_R2_EVIDENCE_COLLECTION"
        return output
    chosen = choose_focus(issue)
    if len(chosen) < 4:
        output["status"] = "HOLD_FEWER_THAN_FOUR_DISTINCT_FOCUS_TOPICS"
        output["structural_r1_blockers"].append("FOUR_FOCUS_EDITORIAL_TOPICS_NOT_AVAILABLE")
        return output
    # Apply bounded official lookup only to the four selected events; no
    # broad web crawling, redirects, paid sources or protected article bodies.
    focus_issue = deepcopy(issue)
    focus_issue["articles"] = [deepcopy(x) for x in chosen]
    official_fetcher = fetcher if fetcher is not None else fetch_official_page
    output["primary_source_fetch_results"] = review_official_excerpts(
        focus_issue, fetcher=official_fetcher, max_documents=max_documents)
    packets = [_dossier(x) for x in focus_issue["articles"]]
    for item in packets:
        item["original_issuer_urls_found_in_current_rss_source_index"] = (
            _original_source_feed_matches(item, rows, cutoff))
        item["additional_publisher_index_matches_not_fact_verified"] = (
            _match_independent_index_for_review(item, eligible, cutoff))
        item["independent_publisher_source_comparison_status"] = (
            "SOURCE_INDEX_CANDIDATE_NEEDS_CLAIM_REVIEW" if
            item["additional_publisher_index_matches_not_fact_verified"]
            else "NO_SECOND_INDEPENDENT_NEWS_INDEX_CANDIDATE")
    output["potential_additional_independent_publisher_sources"] = sum(
        len(p["additional_publisher_index_matches_not_fact_verified"])
        for p in packets)
    output["original_issuer_urls_also_seen_in_current_rss"] = sum(
        len(p["original_issuer_urls_found_in_current_rss_source_index"])
        for p in packets)
    already_fetched = focus_issue.get("source_health", {}).get(
        "primary_source_review", {}).get("fetched_count", 0)
    # Use original issuer documents not already indexed by the news feeds.
    # This does not add RSS sources or imply independent claim verification.
    original_fetcher = curated_fetcher or fetch_curated_primary_page
    output["curated_primary_research_audit"] = _attach_curated_original_research(
        packets, now, original_fetcher, max(0, max_documents - already_fetched))
    output["curated_primary_documents_located"] = sum(
        item["retrieval_status"] ==
        "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
        for packet in packets for item in packet.get("curated_original_research", []))
    output["curated_primary_claim_phrases_matched"] = sum(
        len(item["matched_primary_text_phrases"])
        for packet in packets for item in packet.get("curated_original_research", []))
    output["focus_with_located_primary_context"] = sum(
        bool(d["primary_official_context_not_fact_verified"]) or any(
            row["retrieval_status"] == "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
            for row in d.get("curated_original_research", []))
        for d in packets)
    # Evidence gaps are updated only when a real original document and
    # appropriate source-specific text were actually located in the batch.
    for packet in packets:
        located = [d for d in packet.get("curated_original_research", [])
                   if d["retrieval_status"] ==
                   "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"]
        if located:
            packet["blockers"] = [b for b in packet["blockers"]
                                  if b != "MATCHED_PRIMARY_DOCUMENT_EXCERPT_NOT_LOCATED"]
            packet["primary_document_links_grounded"] = len(located)
            packet["primary_document_dates_located"] = sum(
                d["original_document_date_located"] for d in located)
            if not any(d["original_document_date_located"] for d in located):
                packet["blockers"].append("PRIMARY_DOCUMENT_PUBLICATION_DATE_NOT_LOCATED")
            if packet.get("source_domains"):
                packet["blockers"] = [b for b in packet["blockers"]
                    if b != "SECOND_PUBLISHER_SOURCE_NOT_LOCATED"]
                packet["blockers"].append(
                    "SECOND_PUBLISHER_INDEPENDENT_CLAIM_COMPARISON_PENDING")
        contrasting = [d for d in located if d["contrasting_position_located"]]
        observations = [d for d in located
                        if d["observation_located_not_causality_proven"]]
        packet["contrasting_position_source_documents"] = [
            {"url":d["url"],"source_document_sha256":d["source_document_sha256"],
             "status":"SOURCE_POSITION_LOCATED_NOT_INDEPENDENTLY_VERIFIED"}
            for d in contrasting]
        packet["observational_data_source_documents"] = [
            {"url":d["url"],"source_document_sha256":d["source_document_sha256"],
             "status":"SOURCE_OBSERVATION_NOT_CAUSAL_PROOF"}
            for d in observations]
        if contrasting:
            packet["blockers"] = [b for b in packet["blockers"]
                if b != "COUNTEREVIDENCE_WITH_SOURCE_LOCATION_NOT_VERIFIED"]
            packet["blockers"].append(
                "COUNTERPOSITION_LOCATED_BUT_INDEPENDENT_VALIDATION_PENDING")
    output["focus_with_located_contrasting_positions"] = sum(
        bool(d["contrasting_position_source_documents"]) for d in packets)
    output["focus_with_located_observations_not_causal_proofs"] = sum(
        bool(d["observational_data_source_documents"]) for d in packets)
    # Distinguish an actual two-issuer primary-source comparison from
    # repeated documents by the same issuer (e.g. two Bank of Canada pages).
    output["cross_issuer_original_document_pairs_ready_for_review"] = 0
    for packet in packets:
        docs=[d for d in packet.get("curated_original_research",[])
              if d["retrieval_status"] ==
              "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
              and d.get("source_document_sha256") and d.get("original_document_date_located")]
        # An issuer's press release and governor's statement are TWO
        # documents but ONE publishing institution, despite differing labels.
        # Exact verified document host is the conservative issuer identity.
        distinct_sources=_distinct_primary_issuer_domains(docs)
        two_issuers=len(distinct_sources)>=2
        packet["cross_issuer_primary_source_comparison"]={
            "distinct_issuers_with_dated_primary_matches":len(distinct_sources),
            "distinct_original_domains":len(distinct_sources),
            "two_independent_primary_issuers_located":bool(two_issuers),
            "source_claims_need_manual_reconciliation":True,
            "contradiction_or_difference_explained":False,
            "fact_verification_signed":False,
            "status":("TWO_PRIMARY_ISSUERS_READY_FOR_MANUAL_RECONCILIATION"
                      if two_issuers else "MISSING_SECOND_DISTINCT_PRIMARY_ISSUER")
        }
        if two_issuers:
            output["cross_issuer_original_document_pairs_ready_for_review"]+=1
        else:
            # A central-bank rate decision has ONE authoritative decision
            # maker, not two independently issuing central banks. Its factual
            # decision can be matched to that primary release, while the
            # consequence and interpretation still require source-by-source
            # independent corroboration. An explicit two-issuer comparison
            # remains mandatory only for genuinely conflicting estimates.
            manifest=_load_issue_manifest().get(packet["event_id"],{})
            needs_two=_needs_two_distinct_primary_issuers(manifest)
            if needs_two:
                packet["blockers"].append(
                    "REQUIRED_SECOND_PRIMARY_ESTIMATE_ISSUER_NOT_LOCATED")
            packet["cross_issuer_primary_source_comparison"]["status"]=(
                "TWO_PRIMARY_ESTIMATE_ISSUERS_REQUIRED" if needs_two
                else "ONE_AUTHORITATIVE_ORIGIN_NEEDS_INDEPENDENT_CLAIM_CHECK")
        packet["cross_issuer_primary_source_comparison"][
            "claim_by_claim_external_comparison_completed"]=False
    registry=_load_issue_manifest()
    for packet in packets:
        packet["source_stated_quantity_comparison"] = (
            _source_stated_quantity_comparison(packet,registry))
    output["matched_cross_issuer_numeric_comparisons_pending_review"] = sum(
        bool(d.get("source_stated_quantity_comparison") and
             d["source_stated_quantity_comparison"]["status"] ==
             "TWO_ORIGINAL_ISSUER_VOLUME_ESTIMATES_LOCATED_REQUIRES_RECONCILIATION")
        for d in packets)
    output["analysis_packets"] = packets
    # Deep subjects must be tied to current sourced headlines. Shortlisting
    # them is NEVER equivalent to finished research or original evidence.
    manifest = _load_issue_manifest()
    deep = sorted(packets, key=lambda d: (
        -manifest.get(d["event_id"],{}).get("deep_research_candidate_priority",0)
         if d.get("primary_document_links_grounded",0) else 0,
        -sum(item["retrieval_status"] ==
             "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
             for item in d.get("curated_original_research", [])),
        -len(d["source_domains"]), d["event_id"]))
    output["current_deep_research_shortlist"] = [{
        "event_id": d["event_id"],
        "topic": d["topic"],
        "title": d["original_title"],
        "published_at": d["article_publication_utc"],
        "linked_source_count": len(d["linked_sources"]),
        "official_context_excerpt_count": len(d["primary_official_context_not_fact_verified"]),
        "curated_original_document_matches": sum(
            row["retrieval_status"] ==
            "ORIGINAL_DOCUMENT_EXCERPT_MATCH_NOT_FACT_VERIFIED"
            for row in d.get("curated_original_research", [])),
        "selection_rationale":manifest.get(d["event_id"],{}).get("priority_rationale"),
        "research_documented": False,
        "historical_comparator_verified": False,
        "counterevidence_verified": False,
        "editor_signed": False
    } for d in deep[:2]]
    output["status"] = "HOLD_R2_EVIDENCE_BEFORE_GEMINI"
    output["focus_distinct_topics"] = len({d["topic"] for d in packets})
    # SOURCE DOCUMENT matching is not an independent validated counterclaim.
    output["focus_with_confirmed_contrary_evidence"] = 0
    output["focus_with_verified_causal_data"] = 0
    output["focus_with_signed_claims"] = sum(d["signed_verified_claims"] >= 3 for d in packets)
    output["missing_evidence_by_event"] = [{
        "event_id": d["event_id"], "reasons": d["blockers"]} for d in packets]
    return output
