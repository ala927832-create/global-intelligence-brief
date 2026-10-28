"""One-shot, read-only P1 gate. Never print/export Inoreader feed addresses.

Requires four repository Secrets; proves actual original-news URL ingestion, not
editorial verification. Works on GitHub push/main without user-triggered retries.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from tools.gib_style_c_rc.inoreader_source import (
    LANES, collect_export_feeds, safe_feed_diagnostics, urls_from_environment
)

def probe(urls, fetcher=None):
    diagnostics=safe_feed_diagnostics(urls)
    report={
        "kind":"GIB_INOREADER_REAL_SOURCE_GATE",
        "phase":"P1_ONLY",
        "data_origin":"GITHUB_ACTIONS_REPOSITORY_SECRETS",
        "release_approved":False,
        "editorial_facts_verified":0,
        "lanes": {lane: {"url_shape":state} for lane,state in diagnostics.items()},
    }
    if any(state!="VALID_URL_SHAPE" for state in diagnostics.values()):
        report["gate"]="BLOCKED_INVALID_FEED_VALUES"
        return report
    try:
        articles,health=collect_export_feeds(urls,fetcher=fetcher)
    except (ValueError,RuntimeError) as exc:
        # collect_export_feeds errors are sanitized in the adapter.
        report["gate"]="BLOCKED_FEED_RETRIEVAL"
        report["error_class"]=str(exc)
        return report
    for lane in LANES:
        stat=health["lane_stats"][lane]
        report["lanes"][lane].update({
            "readable_items":stat["readable_items"],
            "rejected":stat["rejected"],
            "feed_sha256":stat["feed_sha256"],
            "retrieved_at_utc":stat["retrieved_at_utc"]
        })
    report["unique_original_articles"]=len(articles)
    report["connected_lanes"]=len(health["connected_lanes"])
    report["gate"]="PASS_REAL_SOURCE_INGESTION" if all(
        health["lane_stats"][lane]["readable_items"]>0 for lane in LANES
    ) and len(articles)>0 else "BLOCKED_EMPTY_SOURCE_LANE"
    return report

def main():
    report=probe(urls_from_environment())
    dest=Path("qa_out/inoreader_p1_live_gate.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for lane,item in report["lanes"].items():
        print(f"P1_{lane}: {item['url_shape']} items={item.get('readable_items','NOT_FETCHED')}")
    print("P1_GATE:",report["gate"])
    if report.get("error_class"):
        print("P1_ERROR_CLASS:",report["error_class"])
    return 0 if report["gate"]=="PASS_REAL_SOURCE_INGESTION" else 1

if __name__=="__main__":
    raise SystemExit(main())
