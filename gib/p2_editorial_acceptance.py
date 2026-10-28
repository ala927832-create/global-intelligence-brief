"""P2 global newsroom acceptance diagnostics. No automatic fact certification.

Publisher-domain diversity only indicates possible independent corroboration;
a human must compare source-specific claims and sign every verified conclusion.
"""
from __future__ import annotations
import datetime as dt
from urllib.parse import urlsplit


def assess_snapshot(source_health, cutoff):
    """Avoid treating a late RSS backfill as a historical on-time newsroom capture."""
    stamp=source_health.get("checked_at_utc") or ""
    if not stamp:
        return {"state":"CAPTURE_TIMESTAMP_MISSING","lag_minutes":None,"on_time_proven":False}
    try:
        captured=dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))
        if captured.tzinfo is None or cutoff.tzinfo is None:
            raise ValueError("timezone required")
        lag=round((captured-cutoff).total_seconds()/60,1)
    except (ValueError,TypeError,AttributeError):
        return {"state":"CAPTURE_TIMESTAMP_INVALID","lag_minutes":None,"on_time_proven":False}
    # No archive of what RSS published at cutoff is available in a late snapshot.
    state=("EARLY_SNAPSHOT_INCOMPLETE" if lag < 0
           else "RETROSPECTIVE_SNAPSHOT_NOT_COMPLETE" if lag > 45
           else "NEAR_CUTOFF_CAPTURE_REQUIRES_EDITORIAL_REVIEW")
    return {"state":state,"lag_minutes":lag,"cutoff_utc":cutoff.isoformat(),
            "capture_utc":captured.isoformat(),
            "on_time_proven":False}


def inspect_lead_evidence(issue):
    """Require real independent claim corroboration; never infer from syndicated links."""
    leads=[]
    for a in issue.get("articles",[])[:3]:
        sources=a.get("sources") or []
        domains=sorted({urlsplit(s.get("url") or "").hostname for s in sources
                        if urlsplit(s.get("url") or "").hostname})
        claims=a.get("evidence") or []
        verified=[c for c in claims if c.get("verification")=="VERIFIED"
                  and c.get("reviewer") and c.get("source_sha256")
                  and c.get("source_location") not in (None,"","feed headline/snippet")]
        excerpt=[c for c in claims if c.get("verification")=="SOURCE_EXCERPT_MATCH_NOT_FACT_VERIFIED"
                 and c.get("source_sha256")]
        gaps=[]
        if len(domains)<2:
            gaps.append("SECOND_INDEPENDENT_PUBLISHER_CLAIM_COMPARISON_MISSING")
        if not excerpt and not verified:
            gaps.append("LOCATED_PRIMARY_SOURCE_EXCERPT_MISSING")
        if not verified:
            gaps.append("NO_MANUALLY_SIGNED_VERIFIED_CLAIM")
        if not a.get("event_time_utc"):
            gaps.append("EVENT_OCCURRENCE_TIME_UNCONFIRMED")
        leads.append({
            "event_id":a.get("event_id"),
            "original_source_domains":domains,
            "possible_independent_publisher_domains":len(domains),
            "located_official_excerpt_not_fact_verified":len(excerpt),
            "manually_signed_claims":len(verified),
            "independently_verified_lead":not gaps,
            "gaps":gaps
        })
    return leads


def p2_readiness(issue):
    """Editorial HOLD remains until actual verified journalism and model revision."""
    health=issue.get("source_health") or {}
    leads=inspect_lead_evidence(issue)
    edits=issue.get("editorial_depth_audit") or {}
    status=(issue.get("gemini_editorial") or {}).get("status","NOT_REQUESTED")
    blockers=[]
    if len(issue.get("articles",[]))<8: blockers.append("WORLD_BRIEF_FEWER_THAN_8")
    if health.get("distinct_domains",0)<4: blockers.append("FEWER_THAN_FOUR_PUBLISHER_DOMAINS")
    if len(leads)<3: blockers.append("LESS_THAN_THREE_LEAD_EVENTS")
    if len(leads)<3 or any(x["gaps"] for x in leads):
        blockers.append("LEAD_CROSS_REFERENCE_AND_PRIMARY_FACT_REVIEW_INCOMPLETE")
    if edits.get("deep_drafts_meeting_minimum_review_standard",0)<1:
        blockers.append("ONE_EVIDENCED_DEEP_STUDY_MISSING")
    if status!="REVISED_DRAFT_PENDING_REVIEW":
        blockers.append("GEMINI_TWO_PASS_MATERIAL_REVISION_NOT_ACCEPTED")
    if issue.get("edition")=="evening" and not health.get("has_morning_comparison"):
        blockers.append("SAME_DAY_MORNING_BASELINE_NOT_CONFIRMED")
    if health.get("cutoff_snapshot",{}).get("state")!="ON_TIME_PERSISTED_AND_VERIFIED":
        blockers.append("PER_EDITION_REAL_TIME_SOURCE_COVERAGE_UNPROVEN")
    if issue.get("editorial_status")!="EDITOR_APPROVED":
        blockers.append("HUMAN_EDITORIAL_SIGNOFF_MISSING")
    return {
        "gate":"P2_EDITORIAL_HOLD" if blockers else "P2_CONTENT_READY_FOR_OWNER_REVIEW",
        "news_events":len(issue.get("articles",[])),
        "independent_publisher_domains":health.get("distinct_domains",0),
        "lead_evidence":leads,
        "deep_studies_review_ready":edits.get("deep_drafts_meeting_minimum_review_standard",0),
        "gemini_editorial_status":status,
        "cutoff_snapshot":health.get("cutoff_snapshot",{}),
        "blockers":sorted(set(blockers)),
        "automatic_release_approved":False,
        "p3_device_or_ten_day_approved":False
    }
