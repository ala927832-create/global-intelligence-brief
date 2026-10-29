"""GIB V3 Round-2 EVIDENCE PRE-FLIGHT on a real R1 source index.

The owner permitted a *test* after two independently passing G0/G1 runs.
This tool never generates drafts, asks Gemini, approves claims or emits EPUB.
Only existing, already-discovered RSS/official-source metadata is inspected.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from gib.contract import locked_contract
from gib.editorial_depth import audit_editorial_depth
from gib.evidence_review import check_claim_lineage
from gib.newsroom_v16 import canonical_issue
from gib.p2_editorial_acceptance import inspect_lead_evidence, p2_readiness
from gib.research_dossier import make_dossiers
from qa.p2_content_gate import eligible_source_rows, source_input_gate, selected_story_gate

TPE=ZoneInfo("Asia/Taipei")
UTC=dt.timezone.utc


def latest_morning_cutoff(now):
    if now.tzinfo is None:
        raise ValueError("CAPTURE_MUST_BE_TIMEZONE_AWARE")
    local=now.astimezone(TPE)
    day=local.date() if local.time()>=dt.time(7,30) else local.date()-dt.timedelta(days=1)
    return dt.datetime.combine(day,dt.time(7,30),TPE).astimezone(UTC)


def scan_source_index(rows,now,contract=None,weights=None):
    """No unearned VERIFIED status; G2 can only pass with human review evidence."""
    contract=contract or locked_contract()
    cutoff=latest_morning_cutoff(now)
    g0=source_input_gate(rows,cutoff,"morning",contract,observed_at=now)
    # The R1 structural threshold is separate from the missing on-time capture
    # archive. This check cannot retroactively certify a missed 07:30 slot.
    source_structural_blockers=[
        b for b in g0["blockers"]
        if not b.startswith(("RETROSPECTIVE_CAPTURE_", "SOURCE_SNAPSHOT_BEFORE_"))
    ]
    result={
        "kind":"GIB_V3_R2_REAL_SOURCE_EVIDENCE_PREFLIGHT_ONLY",
        "cutoff_utc":cutoff.isoformat(),
        "inspection_utc":now.astimezone(UTC).isoformat(),
        "from_live_or_archived_publisher_index_not_article_full_text":True,
        "actual_scheduled_cutoff_capture_verified":False,
        "human_editorial_signoff":False,
        "gemini_called":False,
        "generated_html":False,
        "generated_epub":False,
        "release_approved":False,
        "r1":{"source_structural_gate":g0["gate"],
              "source_structural_blockers":source_structural_blockers,
              "candidate_events":g0["distinct_evidence_bearing_events"],
              "publisher_domains":g0["original_publisher_domains"],
              "topic_groups":g0["editorial_topic_groups"]},
        "r2":{"started":False,"status":"NOT_STARTED_R1_SOURCE_FAILED",
              "blockers":["R1_SOURCE_STRUCTURE_NOT_READY"]},
    }
    if source_structural_blockers:
        return result
    eligible,_,_,_=eligible_source_rows(rows,cutoff,"morning")
    issue=canonical_issue(eligible,"morning",cutoff,
                          weights or {},require_material_relevance=False,
                          tiered_v3=True)
    selected=selected_story_gate(issue,contract)
    result["r1"]["selected_events"]=selected["unique_events"]
    result["r1"]["main_news"]=selected["main_news"]
    result["r1"]["supplementary_news"]=selected["supplementary_news"]
    result["r1"]["selected_publisher_domains"]=selected.get("selected_primary_publisher_domains",0)
    result["r1"]["selected_topic_groups"]=selected.get("selected_editorial_topics",0)
    result["r1"]["selection_blockers"]=selected["blockers"]
    result["r1"]["source_and_selection_structural_ready"]=not selected["blockers"]
    if selected["blockers"]:
        result["r2"]["status"]="NOT_STARTED_R1_SELECTION_FAILED"
        result["r2"]["blockers"]=selected["blockers"]
        return result

    # R2 trial: inspect actual selected source-bound material, NOT fabricated
    # texts. No draft or verified claims are inserted into the issue.
    analyses=audit_editorial_depth(issue,drafts=[])
    leads=inspect_lead_evidence(issue)
    dossiers=make_dossiers(issue,max_events=4)
    readiness=p2_readiness(issue)
    lineage=check_claim_lineage(issue)
    required=contract["editorial_acceptance"]["morning_content"]
    ready_analyses=sum(bool(a.get("verification")=="EDITOR_REVIEWED" and
                            a.get("analysis_ready"))
                       for a in (issue.get("analyses") or []))
    ready_research=sum(bool(study.get("verification")=="EDITOR_REVIEWED" and
                            study.get("primary_source_sha256"))
                       for study in issue.get("deep_research",[]))
    verified_leads=sum(bool(a["independently_verified_lead"]) for a in leads)
    evidence_points=sum(len(a.get("evidence") or []) for a in issue["articles"])
    signed=sum(sum(c.get("verification")=="VERIFIED" and
                   bool(c.get("reviewer")) and bool(c.get("source_sha256"))
                   for c in a.get("evidence",[])) for a in issue["articles"])

    blockers=[]
    if ready_analyses<required["distinct_substantive_analyses"]:
        blockers.append("FOUR_EVIDENCED_DISTINCT_ANALYSES_NOT_COMPLETED")
    if ready_research<required["deep_research_min"]:
        blockers.append("CURRENT_HEADLINE_PRIMARY_SOURCE_DEEP_RESEARCH_MISSING")
    if verified_leads<3:
        blockers.append("TOP_THREE_INDEPENDENTLY_VERIFIED_LEADS_MISSING")
    if signed<3:
        blockers.append("EDITOR_SIGNED_SOURCE_CLAIMS_MISSING")
    if not issue.get("editorial_drafts"):
        blockers.append("NO_SOURCE_GROUNDED_FULL_EDITORIAL_DRAFTS")
    if analyses["deep_drafts_meeting_minimum_review_standard"]<1:
        blockers.append("DEEP_EDITORIAL_DEPTH_AND_ANTI_PADDING_NOT_VERIFIED")
    if not issue.get("gemini_editorial"):
        blockers.append("TWO_PASS_MATERIAL_GEMINI_REVISION_NOT_TESTED")
    blockers.extend("CLAIM_LINEAGE_"+x for x in lineage)
    if readiness["gate"]!="P2_CONTENT_READY_FOR_OWNER_REVIEW":
        blockers.append("P2_EDITORIAL_REVIEW_STILL_HOLD")

    result["r2"]={
        "started":True,
        "status":"HOLD_G2_EVIDENCE_AND_EDITORIAL_DEPTH" if blockers else "READY_FOR_HUMAN_REVIEW_ONLY",
        "main_news":selected["main_news"],
        "supplementary_news":selected["supplementary_news"],
        "attributable_index_evidence_points":evidence_points,
        "manually_attested_verified_claims":signed,
        "required_distinct_analyses":required["distinct_substantive_analyses"],
        "completed_source_grounded_analyses":ready_analyses,
        "required_current_deep_studies_min":required["deep_research_min"],
        "completed_current_deep_studies":ready_research,
        "independently_verified_top_three_leads":verified_leads,
        "deep_editorial_depth_audit":{
            "draft_count":analyses["editorial_draft_count"],
            "qualifying_research_drafts":analyses["deep_drafts_meeting_minimum_review_standard"]
        },
        "lead_evidence_gaps":[{"event_id":x["event_id"],"gaps":x["gaps"]} for x in leads],
        "research_candidate_evidence_gaps":[{
            "event_id":d["event_id"],"missing":d["missing_evidence"]
        } for d in dossiers],
        "claim_lineage_errors":lineage,
        "existing_p2_readiness_blockers":readiness["blockers"],
        "blockers":sorted(set(blockers)),
        "no_reader_preview_until_all_g2_and_g3_gates_pass":True,
    }
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-index",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    source=Path(args.source_index)
    if not source.exists():
        raise SystemExit("R2_INPUT_SOURCE_INDEX_NOT_FOUND")
    rows=json.loads(source.read_text(encoding="utf-8"))
    now=dt.datetime.now(UTC)
    config=json.loads((Path(__file__).resolve().parents[1]/"config/sources.json").read_text(encoding="utf-8"))
    result=scan_source_index(rows,now,weights=config.get("section_weights",{}))
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "r2":result["r2"]["status"],
        "r1_candidate_events":result["r1"]["candidate_events"],
        "r1_main_news":result["r1"].get("main_news",0),
        "r1_supplementary":result["r1"].get("supplementary_news",0),
        "r2_completed_analyses":result["r2"].get("completed_source_grounded_analyses",0),
        "r2_completed_deep_studies":result["r2"].get("completed_current_deep_studies",0),
        "r2_verified_leads":result["r2"].get("independently_verified_top_three_leads",0),
        "r2_blockers":result["r2"]["blockers"],
        "human_approval":False,
        "epub_generated":False,
        "report":str(out),
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
