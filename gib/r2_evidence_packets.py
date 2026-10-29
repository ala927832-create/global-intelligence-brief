"""GIB V3 R2: evidence-first dossiers, BEFORE editorial drafting or Gemini.

Only real already-approved source-index rows and bounded, explicitly allowlisted
official source pages. Never transform index descriptions into verified facts,
counterclaims, causal conclusions, research prose or publication approval.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from collections import Counter
from copy import deepcopy
from urllib.parse import urlsplit

from gib.newsroom_v16 import canonical_issue
from gib.evidence_review import APPROVED_HOSTS, review_official_excerpts, fetch_official_page
from qa.p2_content_gate import eligible_source_rows, source_input_gate, selected_story_gate
from qa.r2_evidence_preflight import latest_morning_cutoff


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


def build_packets(rows, now, weights=None, fetcher=None, max_documents=6):
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
    output["analysis_packets"] = packets
    # Deep subjects must be tied to current sourced headlines. Shortlisting
    # them is NEVER equivalent to finished research or original evidence.
    deep = sorted(packets, key=lambda d: (
        -len(d["primary_official_context_not_fact_verified"]),
        -len(d["source_domains"]), d["event_id"]))
    output["current_deep_research_shortlist"] = [{
        "event_id": d["event_id"],
        "topic": d["topic"],
        "title": d["original_title"],
        "published_at": d["article_publication_utc"],
        "linked_source_count": len(d["linked_sources"]),
        "official_context_excerpt_count": len(d["primary_official_context_not_fact_verified"]),
        "research_documented": False,
        "historical_comparator_verified": False,
        "counterevidence_verified": False,
        "editor_signed": False
    } for d in deep[:2]]
    output["status"] = "HOLD_R2_EVIDENCE_BEFORE_GEMINI"
    output["focus_distinct_topics"] = len({d["topic"] for d in packets})
    output["focus_with_located_primary_context"] = sum(
        bool(d["primary_official_context_not_fact_verified"]) for d in packets)
    output["focus_with_confirmed_contrary_evidence"] = 0
    output["focus_with_verified_causal_data"] = 0
    output["focus_with_signed_claims"] = sum(d["signed_verified_claims"] >= 3 for d in packets)
    output["missing_evidence_by_event"] = [{
        "event_id": d["event_id"], "reasons": d["blockers"]} for d in packets]
    return output
