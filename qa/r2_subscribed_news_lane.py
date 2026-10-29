"""R2 internal headline/attribution acceptance from existing subscriber source index.

Does NOT turn on publication or produce reader-facing HTML/EPUB. AI opinions,
absence of independent corroboration and debates cannot reject the RSS news
source. Extra analytical statements require separate evidence.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path

from gib.contract import locked_contract
from gib.newsroom_v16 import canonical_issue
from gib.subscription_news_policy import is_subscribed_news
from qa.p2_content_gate import eligible_source_rows, source_input_gate, selected_story_gate
from qa.r2_evidence_preflight import latest_morning_cutoff

ROOT=Path(__file__).resolve().parents[1]


def inspect(rows, now, weights=None):
    cutoff=latest_morning_cutoff(now)
    valid,rejected,start,end=eligible_source_rows(rows,cutoff,"morning")
    g0=source_input_gate(rows,cutoff,"morning",observed_at=now)
    issue=canonical_issue(valid,"morning",cutoff,weights=weights or {},
                          tiered_v3=True,require_material_relevance=False)
    selected=selected_story_gate(issue)
    stories=[]
    for item in issue["articles"]:
        src=item["sources"][0]
        origin=item.get("news_source_policy") or {}
        # Internal NEWS row: only copy original title and publisher excerpt.
        # Neither a contrary view nor an unverified AI inference is inserted.
        stories.append({
            "event_id":item["event_id"],
            "tier":item["editorial_tier"],
            "topic":item["topic"],
            "source_original_title":item["title_original"],
            "source_article_url":src["url"],
            "source_publisher":origin.get("source_name") or src["publisher"],
            "source_published_utc":item["article_published_at"],
            "user_inoreader_subscribed":bool(origin.get("subscription_news_eligible")),
            "inoreader_source_id":origin.get("source_id"),
            "inoreader_original_folder":origin.get("source_group"),
            "source_publisher_excerpt_only":(item["headline_summary"]
                     if len(item["headline_summary"].strip())>=50 else ""),
            "summary_mode":origin.get("summary_policy")
                     or ("ATTRIBUTED_NON_SUBSCRIBED_PUBLISHER_EXCERPT"),
            "no_ai_rebuttal_used_as_news_veto":True,
            "additional_analysis_claims_verified":False,
            "gemini_called":False,
        })
    sub_rows=[x for x in valid if is_subscribed_news(x)]
    return {
        "kind":"GIB_R2_SUBSCRIBED_SOURCE_NEWS_LANE_QA_NOT_READER_ARTIFACT",
        "owner_news_policy":"SUBSCRIBED_ORIGINAL_SOURCE_COUNTS_AS_NEWS_AND_ANALYSIS_IS_SEPARATE",
        "cutoff_utc":cutoff.isoformat(),
        "inspection_utc":now.astimezone(dt.timezone.utc).isoformat(),
        "original_opml_feeds_configured":24,
        "dated_subscribed_news_eligible_before_ranking":len(sub_rows),
        "dated_subscribed_headline_only_before_ranking":sum(
             not (x.get("snippet") or "").strip() or
             len((x.get("snippet") or "").strip())<50 for x in sub_rows),
        "raw_candidate_rows":len(rows),
        "g0_g1_structure_pass":not [
            x for x in g0["blockers"] if not x.startswith(
                ("RETROSPECTIVE_CAPTURE_","SOURCE_SNAPSHOT_BEFORE_"))
        ] and not selected["blockers"],
        "selected_total":len(stories),
        "selected_subscription_news":sum(x["user_inoreader_subscribed"] for x in stories),
        "selected_subscription_headline_only":sum(
             x["user_inoreader_subscribed"] and x["summary_mode"]=="HEADLINE_ONLY_LINK_NO_AI_SUMMARY"
             for x in stories),
        "headline_news_entries":stories,
        "source_gate_rejections":dict(rejected),
        "selected_story_structural_blockers":selected["blockers"],
        "source_capture_timeliness_not_proven":not g0["is_timely_cutoff_snapshot_proven"],
        "rebuttal_or_independent_ai_opinion_can_remove_subscribed_news":False,
        "analysis_research_quality_gate":"SEPARATE_REQUIRES_SOURCED_CAUSAL_AND_COUNTEREVIDENCE_REVIEW",
        "ai_brief_generation_from_title_only_forbidden":True,
        "gemini_called":False,
        "html_or_epub_generated":False,
        "public_news_release_enabled":False,
        "p2_editorial_final_pass":False,
        "owner_publishing_approval":False,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-index",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    raw=json.loads(Path(args.source_index).read_text(encoding="utf-8"))
    if not isinstance(raw,list):raise SystemExit("SOURCE_INDEX_NOT_ARRAY")
    cfg=json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8"))
    result=inspect(raw,dt.datetime.now(dt.timezone.utc),
                   weights=cfg.get("section_weights") or {})
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "news_lane":"SOURCE_ATTRIBUTED_SUBSCRIBED_NEWS_NOT_RESEARCH",
        "qualified_subscriber_news_candidates":result["dated_subscribed_news_eligible_before_ranking"],
        "selected_subscribed_news":result["selected_subscription_news"],
        "selected_headline_only_no_ai_summary":result["selected_subscription_headline_only"],
        "selected_total":result["selected_total"],
        "selected_structural_blockers":result["selected_story_structural_blockers"],
        "analysis_allowed_without_evidence":False,
        "gemini_called":False,
        "release_approved":False
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
