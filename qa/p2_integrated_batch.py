"""One QA-only P2 batch: shared real public RSS index -> two canonical issues.

No publication, schedule, LINE, Pages, new sources or automatic fact approval.
This is an observed-source backfill rehearsal, NOT proof of on-time daily delivery.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from qa.opml_free_p1 import collect
from run_newsroom_v16 import run

TZ=ZoneInfo("Asia/Taipei")
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/inoreader_free_feeds.json"
OUTPUT=ROOT/"qa_outputs/p2_integrated"


def completed_report_date(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    local=now.astimezone(TZ)
    # Full 17:30 edition is only complete after its target time.
    return local.date() if local.time()>=dt.time(17,30) else local.date()-dt.timedelta(days=1)


def local_cutoff(day,edition):
    hour=7 if edition=="morning" else 17
    return dt.datetime.combine(day,dt.time(hour,30),TZ).astimezone(dt.timezone.utc)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_batch(report_date=None,gemini=False,source_fetcher=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    date=report_date or completed_report_date(now)
    if isinstance(date,str):
        date=dt.date.fromisoformat(date)
    if date>completed_report_date(now):
        raise ValueError("P2_DATE_IS_NOT_A_COMPLETED_MORNING_AND_EVENING_DAY")
    out=OUTPUT/date.isoformat()
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    articles,source_health=collect(cfg,fetcher=source_fetcher,now=now)
    source_index=out/"source_index.json"
    source_report=out/"source_health.json"
    source_index.write_text(json.dumps(articles,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    source_report.write_text(json.dumps(source_health,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    snapshot_hash=digest(source_index)
    deliveries={}
    earlier=None
    for edition in ("morning","evening"):
        as_of=local_cutoff(date,edition).isoformat()
        args=SimpleNamespace(
            edition=edition,fixture=None,cached_issue=None,
            source_mode="opml",source_index=str(source_index),source_health=str(source_report),
            morning_issue=earlier,as_of=as_of,gemini=gemini,verify_official=True)
        result=run(args)
        issue=json.loads(Path(result["issue_json"]).read_text(encoding="utf-8"))
        if issue["report_date"]!=date.isoformat() or issue["edition"]!=edition:
            raise ValueError("CANONICAL_ISSUE_DATE_OR_EDITION_MISMATCH")
        if not Path(result["style_c_html"]).is_file():
            raise ValueError("STYLE_C_SHARED_ISSUE_OUTPUT_MISSING")
        if result["canonical_issue_sha256"]!=digest(result["issue_json"]):
            raise ValueError("STYLE_C_CANONICAL_HASH_MISMATCH")
        editions=result["epub"]
        for level in ("essential","deep"):
            if not Path(editions[level]["epub"]).is_file():
                raise ValueError("EPUB_QA_PREVIEW_MISSING_"+edition+"_"+level)
        deliveries[edition]={
            "issue_json":result["issue_json"],
            "issue_sha256":result["canonical_issue_sha256"],
            "style_c_html":result["style_c_html"],
            "essential_epub":editions["essential"]["epub"],
            "deep_epub":editions["deep"]["epub"],
            "article_count":len(issue["articles"]),
            "distinct_domains":issue["source_health"]["distinct_domains"],
            "window_diagnostics":issue["source_health"].get("window_diagnostics",{}),
            "cutoff_snapshot":issue["source_health"].get("cutoff_snapshot",{}),
            "p2_editorial_acceptance":issue.get("p2_editorial_acceptance",{}),
            "lead_evidence_gaps":[{"event_id":z["event_id"],"gaps":z["gaps"]}
                                  for z in issue.get("p2_editorial_acceptance",{}).get("lead_evidence",[])],
            "sources_with_identified_provenance":sum(
                any(s.get("opml_source_ids") for s in a.get("sources",[]))
                for a in issue["articles"]),
            "independently_verified_claim_count":sum(
                c.get("verification")=="VERIFIED" and bool(c.get("reviewer"))
                for a in issue["articles"] for c in a.get("evidence",[])),
            "deep_research_approved_count":len(issue.get("deep_research",[])),
            "editorial_draft_count":len(issue.get("editorial_drafts",[])),
            "gemini_status":issue.get("gemini_editorial",{}).get("status","NOT_REQUESTED"),
            "editorial_delta_status":issue.get("editorial_delta_status","NOT_APPLICABLE"),
            "release_hold_reasons":result["release_hold_reasons"],
            "release_approved":False
        }
        earlier=result["issue_json"]
    assert deliveries["evening"]["issue_json"]!=deliveries["morning"]["issue_json"]
    report={
        "kind":"GIB_P2_INTEGRATED_MORNING_EVENING_QA",
        "report_date_tpe":date.isoformat(),
        "source_capture_utc":source_health.get("checked_at_utc"),
        "run_mode":"LIVE_PUBLIC_RSS_SNAPSHOT_BACKFILL_NOT_TIMELY_SCHEDULE_DELIVERY",
        "source_index_sha256":snapshot_hash,
        "source_gate":source_health["gate"],
        "source_configured":source_health["configured_sources"],
        "news_discovered_recent_7d":source_health["recent_7d_unique_article_urls"],
        "report_type":"RETROSPECTIVE_FEED_REPLAY_NOT_REAL_TIME_SCHEDULED_CAPTURE",
        "per_edition_source_time_window_complete":False,
        "paired_snapshot_model":"ONE_LATE_ARCHIVE_REPLAY_FOR_REPRODUCIBILITY_ONLY",
        "not_equivalent_to":"TWO_ISSUE_TIMELY_CAPTURE_OR_PRIMARY_SOURCE_FACT_REVIEW",
        "canonical_model":"gib.newsroom_v16.canonical_issue",
        "style_c_and_dual_reading_source":"SAME_CANONICAL_ISSUE_PER_EDITION",
        "format_layout":"FROZEN_STYLE_C_AND_V16_ESSENTIAL_DEEP_QA",
        "deep_research_standard":"REQUIRES_2_TO_3_INDEPENDENTLY_VERIFIED_RESEARCH_PIECES",
        "editorial_and_fact_check_status":"HOLD_PENDING_HUMAN_PRIMARY_SOURCE_VERIFICATION",
        "nonpublished_preview_generated":True,
        "gemini_requested":bool(gemini),
        "editions":deliveries,
        "p2_content_accepted":False,
        "p3_boox_or_ten_day_attestation":False,
        "release_approved":False,
        "next_gate":"HUMAN_EDITORIAL_EVIDENCE_REVIEW_AND_SOURCE_COMPLETENESS"
    }
    report_path=out/"P2_INTEGRATED_QA_REPORT.json"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "p2":"GENERATED_INTERNAL_QA_HOLD",
        "source_gate":report["source_gate"],
        "recent_source_articles":report["news_discovered_recent_7d"],
        "report_date":date.isoformat(),
        "morning_items":deliveries["morning"]["article_count"],
        "evening_items":deliveries["evening"]["article_count"],
        "morning_gemini":deliveries["morning"]["gemini_status"],
        "evening_gemini":deliveries["evening"]["gemini_status"],
        "release_approved":False,"report":str(report_path)
    },ensure_ascii=False))
    # Technical execution success is distinct from editorial signoff.
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report-date",help="Last fully completed date in Taipei for controlled RSS backfill")
    ap.add_argument("--gemini",action="store_true",help="Only existing confirmed free-tier Gemini integration")
    a=ap.parse_args()
    run_batch(report_date=a.report_date,gemini=a.gemini)


if __name__=="__main__":
    main()
