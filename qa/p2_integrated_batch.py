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
from qa.p2_source_fusion import collect_existing_free_sources, fuse_with_original_opml
from run_newsroom_v16 import run
from qa.p2_content_gate import source_input_gate, selected_story_gate
from gib.newsroom_v16 import canonical_issue
from gib.contract import locked_contract
from tools.gib_style_c_rc.live_html_qa import filter_raw_before_ranking, bounds

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


def run_batch(report_date=None,gemini=False,source_fetcher=None,now=None,extra_fetchers=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    date=report_date or completed_report_date(now)
    if isinstance(date,str):
        date=dt.date.fromisoformat(date)
    if date>completed_report_date(now):
        raise ValueError("P2_DATE_IS_NOT_A_COMPLETED_MORNING_AND_EVENING_DAY")
    out=OUTPUT/date.isoformat()
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    opml_articles,opml_health=collect(cfg,fetcher=source_fetcher,now=now)
    # Synthetic fixture tests never make real network calls unless a controlled
    # supplementary fetcher is explicitly supplied. Main QA uses already
    # approved original free providers (official RSS, GDELT, FreeNewsApi).
    providers=(collect_existing_free_sources(
        json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8")),
        now,fetchers=extra_fetchers)
        if source_fetcher is None or extra_fetchers is not None else {})
    articles,source_health=fuse_with_original_opml(
        opml_articles,opml_health,providers,now)
    source_index=out/"source_index.json"
    source_report=out/"source_health.json"
    source_index.write_text(json.dumps(articles,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    source_report.write_text(json.dumps(source_health,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    snapshot_hash=digest(source_index)
    # V3: strict live RSS preflight, BEFORE Gemini, HTML, EPUB or owner preview.
    # Controlled source_fetcher fixtures are strictly internal integration tests,
    # NEVER owner-facing editions and NEVER eligible for publication approval.
    if source_fetcher is None:
        contract=locked_contract()
        morning_cutoff=local_cutoff(date,"morning")
        first=source_input_gate(articles,morning_cutoff,"morning",contract)
        selected=None
        if not first["blockers"]:
            day_start,day_end=bounds(date,"morning")
            inside,_=filter_raw_before_ranking(articles,day_start,day_end)
            issue_probe=canonical_issue(inside,"morning",morning_cutoff,
                                        json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8")
                                                   ).get("section_weights"),require_material_relevance=True)
            selected=selected_story_gate(issue_probe,contract)
        if first["blockers"] or (selected and selected["blockers"]):
            blockers=first["blockers"]+(selected["blockers"] if selected else [])
            # Explicitly DO NOT call run(), Gemini, pandoc, HTML or EPUB.
            hold={
                "kind":"GIB_P2_V3_SOURCE_FIRST_FAIL_CLOSED_DIAGNOSTIC",
                "report_date_tpe":date.isoformat(),
                "run_mode":"LIVE_PUBLIC_RSS_BACKFILL_DIAGNOSTICS_ONLY",
                "stage":"G0_SOURCE_INPUT" if first["blockers"] else "G1_STORY_SELECTION",
                "gate":"HOLD_NO_READER_PREVIEW",
                "source_gate":source_health.get("gate"),
                "p2_original_opml_source_gate":source_health.get("original_opml_p1_gate"),
                "source_index_sha256":snapshot_hash,
                "source_configured":source_health.get("configured_sources"),
                "source_index_total":len(articles),
                "first_source_gate":first,
                "selected_news_gate":selected,
                "blockers":blockers,
                "diagnosis":"SOURCE_OR_RANKING_PIPELINE_DEFECT_NOT_WORLD_NEWS_SHORTAGE",
                "editions":{},"nonpublished_preview_generated":False,
                "gemini_requested":False,"gemini_called":False,
                "p2_content_accepted":False,"release_approved":False,
                "owner_review_required_now":False,
                "next_action":"INTERNAL_SOURCE_AND_EDITORIAL_FIX_ONLY_NO_INCOMPLETE_PREVIEW"
            }
            report_path=out/"P2_V3_CONTENT_HOLD.json"
            report_path.write_text(json.dumps(hold,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(json.dumps({"p2":"HOLD_SOURCE_FIRST_NO_PREVIEW",
                              "stage":hold["stage"],
                              "source_candidates":first["distinct_evidence_bearing_events"],
                              "selected_news":selected["unique_events"] if selected else None,
                              "blockers":blockers,"gemini_called":False,
                              "reader_preview_generated":False,
                              "diagnostics":str(report_path)},ensure_ascii=False))
            return hold
    deliveries={}
    earlier=None
    for edition in ("morning","evening"):
        as_of=local_cutoff(date,edition).isoformat()
        args=SimpleNamespace(
            edition=edition,fixture=None,cached_issue=None,
            strict_reader_gate=False, # G0/G1 already checked in batch above; fixture internal only
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
        "p2_original_opml_source_gate":source_health.get("original_opml_p1_gate"),
        "p2_existing_free_sources":source_health.get("p2_external_source_fusion",{}),
        "p2_source_index_total":source_health.get("p2_total_source_index_items"),
        "p2_source_index_opml_count":source_health.get("p2_original_opml_index_items"),
        "p2_source_index_additional_count":source_health.get("p2_external_net_new_index_items"),
        "source_configured":source_health["configured_sources"],
        "news_discovered_recent_7d":source_health["recent_7d_unique_article_urls"],
        "report_type":"RETROSPECTIVE_FEED_REPLAY_NOT_REAL_TIME_SCHEDULED_CAPTURE",
        "per_edition_source_time_window_complete":False,
        "paired_snapshot_model":"ONE_LATE_ARCHIVE_REPLAY_FOR_REPRODUCIBILITY_ONLY",
        "not_equivalent_to":"TWO_ISSUE_TIMELY_CAPTURE_OR_PRIMARY_SOURCE_FACT_REVIEW",
        "canonical_model":"gib.newsroom_v16.canonical_issue",
        "style_c_and_dual_reading_source":"SAME_CANONICAL_ISSUE_PER_EDITION",
        "format_layout":"FROZEN_STYLE_C_AND_V16_ESSENTIAL_DEEP_QA",
        "deep_research_standard":"REQUIRES_1_TO_2_CURRENT_HEADLINE_LINKED_EVIDENCED_RESEARCH_PIECES",
        "editorial_and_fact_check_status":"HOLD_PENDING_HUMAN_PRIMARY_SOURCE_VERIFICATION",
        "nonpublished_preview_generated":True,
        "fixture_only_not_for_owner":bool(source_fetcher is not None),
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
