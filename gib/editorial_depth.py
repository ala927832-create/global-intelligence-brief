"""Source-weighted editorial depth audit; never an automated fact verifier.

A long Gemini answer is not a confirmed piece of reporting. This module
separates editorial structure, evidence provenance and owner sign-off.
"""
from __future__ import annotations
from collections import Counter
import re
from urllib.parse import urlsplit

DEEP_FIELDS=("background", "why_it_matters", "transmission", "history",
             "alternative", "watch", "limitations")
ESSENTIAL_FIELDS=("background", "why_it_matters", "transmission")
CJK=re.compile(r"[\u3400-\u9fff]")
SENTENCE=re.compile(r"[。！？!?；;\n]+")


def hanzi(value):
    return len(CJK.findall(str(value or "")))


def redundancy(text):
    """Detect repeated sentences, including simple copy/paste padding."""
    sentences=["".join(s.split()) for s in SENTENCE.split(text or "")
               if len("".join(s.split()))>=14]
    if not sentences:
        return 0.0
    counts=Counter(sentences)
    return round(sum(n-1 for n in counts.values())/len(sentences), 3)


def source_metrics(article):
    sources=article.get("sources") or []
    domains={urlsplit(s.get("url", "")).hostname for s in sources
             if urlsplit(s.get("url", "")).hostname}
    official={s.get("source_id") for s in sources
              if s.get("kind")=="OFFICIAL_FEED"
              and s.get("retrieval_status")=="OFFICIAL_EXCERPT_MATCH"}
    attestations=[claim for claim in article.get("evidence") or []
                  if claim.get("verification")=="VERIFIED"
                  and claim.get("reviewer")
                  and claim.get("source_sha256")
                  and claim.get("source_location") not in (None, "feed headline/snippet")]
    return {
        "domains":len(domains),
        "official_excerpt_sources":len(official),
        "signed_verified_claims":len(attestations),
        "source_ids":sorted(x for x in (s.get("source_id") for s in sources) if x),
    }


def audit_editorial_depth(issue, drafts=None):
    """Audit formatting and traceability; zero automatic publication approval."""
    drafts=issue.get("editorial_drafts", []) if drafts is None else drafts
    by_id={a.get("event_id"):a for a in issue.get("articles", [])}
    results=[]
    for draft in drafts:
        event_id=draft.get("event_id")
        article=by_id.get(event_id)
        if article is None:
            results.append({"event_id":event_id, "ready_for_deep_review":False,
                            "reasons":["Draft refers to unknown event"]})
            continue
        sections=draft.get("sections") or {}
        combined="\n".join(str(sections.get(key, "")) for key in DEEP_FIELDS)
        metrics=source_metrics(article)
        parts={key:hanzi(sections.get(key)) for key in DEEP_FIELDS}
        populated=[k for k,n in parts.items() if n>=55]
        blocked=[]
        if len(populated)<5:
            blocked.append("Less than five substantive analytic sections")
        if not all(parts.get(k,0)>=55 for k in ESSENTIAL_FIELDS):
            blocked.append("Missing explanation of background, stakes or mechanism")
        if not all(parts.get(k,0)>=55 for k in ("alternative", "limitations")):
            blocked.append("Missing counter-evidence or explicit limitations")
        if hanzi(combined)<800:
            blocked.append("Insufficient supported depth (not a target to pad)")
        if redundancy(combined)>0.18:
            blocked.append("Significant repetition rather than new reasoning")
        if metrics["domains"]<2:
            blocked.append("Fewer than two independently attributable domains")
        if metrics["official_excerpt_sources"]<1:
            blocked.append("No located official primary-source excerpt")
        if metrics["signed_verified_claims"]<3:
            blocked.append("Fewer than three manually attested, sourced facts")
        if draft.get("verification")!="EDITOR_REVIEWED":
            blocked.append("Gemini text is not an editor-approved research article")
        results.append({
            "event_id":event_id,
            "title":article.get("title_original"),
            "chinese_analysis_hanzi":hanzi(combined),
            "section_hanzi":parts,
            "substantive_sections":populated,
            "repetition_ratio":redundancy(combined),
            "evidence":metrics,
            "ready_for_deep_review":not blocked,
            "reasons":blocked,
        })
    ready=[row for row in results if row.get("ready_for_deep_review")]
    return {
        "audit_kind":"EDITORIAL_AND_LINEAGE_QA_NOT_AUTOMATIC_FACT_VERIFICATION",
        "issue_id":issue.get("issue_id"),
        "news_count":len(issue.get("articles", [])),
        "editorial_draft_count":len(results),
        "deep_drafts_meeting_minimum_review_standard":len(ready),
        "required_depth_topics":2,
        "full_issue_quality_passed":False,
        "research":results,
        "release_blockers":[
            "Requires human factual review and owner publishing approval",
            *(["8–12 qualifying news events not met"]
              if len(issue.get("articles", []))<8 else []),
            *(["Fewer than two deeply sourced, reviewed studies"]
              if len(ready)<2 else []),
        ],
        "note":"Passing a structural rubric does not verify facts or grant permission to publish.",
    }
