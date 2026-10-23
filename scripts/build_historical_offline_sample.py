"""Build a sourced HISTORICAL sample into a one-download offline EPUB.

This is a layout and navigation acceptance fixture, NOT a current briefing and
NOT automatic primary-source verification. The official cited sample dates are
retained and no articles or source claims are fabricated.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from gib.editorial import sig
from gib.publish_v16 import export

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=ROOT/"samples"/"official_research_2026-10-23.json"

def source_id(url):
    return "src_"+hashlib.sha256(url.encode()).hexdigest()[:12]

def transform(original):
    records={x["id"]:x for x in original["sources"]}
    articles=[]
    for i,story in enumerate(original["stories"]):
        references=[]
        for ref in story.get("source_ids",[]):
            if ref not in records:continue
            src=records[ref]
            references.append({
                "source_id":source_id(src["url"]),
                "url":src["url"],"publisher":src["publisher"],
                "article_published_at":src["published"],
                "kind":"HISTORICAL_CURATED_OFFICIAL_SOURCE",
                "retrieval_status":"CITED_NOT_RECHECKED_THIS_RUN"
            })
        if not references: continue
        claim_rows=[
           {"claim_id":sig(story["title"])+f"-hist-{j}",
            "text":fact,"source_id":references[0]["source_id"],
            "support_excerpt":fact,
            "verification":"CURATED_CITED_NOT_AUTO_VERIFIED",
            "source_location":"Historical curated report; primary link below"}
           for j,fact in enumerate(story.get("verified_facts",[]),1)
        ]
        articles.append({
            "event_id":sig(story["title"]),"change_kind":"HISTORICAL_REFERENCE_ONLY",
            "topic":"macro" if i==0 else "central_banks" if i==1 else "geopolitics",
            "topic_label":story.get("category","背景研究"),
            "title_original":story["title"],
            "event_time_utc":None,
            "article_published_at":story["published"]+"T00:00:00+00:00",
            "headline_summary":story.get("summary",""),
            "rank_score":0,"sources":references,"evidence":claim_rows,
            "source_count":len(references),"interpretations":[],
            "editorial_note":"歷史研究樣本，並非今日即時新聞"
        })
    deep=[]
    for ch in original["chapters"][:3]:
        sections=[]
        for sec in ch["sections"]:
            paragraphs=list(sec.get("paragraphs",[]))
            bullet_lines=["• "+line for line in sec.get("bullets",[])]
            sections.append({
                "heading":sec["heading"],
                "body":"\n\n".join(paragraphs+bullet_lines),
                "figure":sec.get("figure")
            })
        deep.append({"title":ch["title"],"sections":sections})
    return {
        "schema_version":"1.6",
        "kind":"historical_cited_offline_reading_fixture",
        "issue_id":"HISTORICAL-20261023-morning",
        "edition":"morning","report_date":"2026-10-23",
        "as_of_utc":"2026-10-23T08:00:00+00:00",
        "editorial_status":"QA_CURATED_HISTORICAL_NOT_LIVE",
        "articles":articles,"deep_research":deep,
        "event_updates":[],"zinc_watch":[],
        "source_health":{
          "candidate_count":len(original["stories"]),
          "unique_count":len(original["stories"]),
          "selected_count":len(articles),
          "distinct_domains":len({x["publisher"] for a in articles for x in a["sources"]}),
          "has_morning_comparison":True,
        },
        "limitations":[
          "這是版面與離線導航試讀，不是當天完整新聞。",
          "新聞數量不足正式 8–12 則門檻，絕不可用於自動發布。",
          "一手來源引用未在此離線工作流程重新逐項查證。"
        ]
    }

def main():
    original=json.loads(SAMPLE.read_text(encoding="utf-8"))
    issue=transform(original)
    folder=ROOT/"qa_outputs"/"historical-offline-reader-demo"
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"issue.json").write_text(json.dumps(issue,ensure_ascii=False,indent=2),encoding="utf-8")
    result=export(issue,[],folder,qa_only=True)
    print(json.dumps({"status":"HISTORICAL_OFFLINE_DEMO_NOT_FOR_PUBLICATION",
        "selected_news":len(issue["articles"]),
        "deep_research_chapters":len(issue["deep_research"]),
        "one_download_full_book":result["offline_complete"]["epub"],
        "other_outputs":result},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
