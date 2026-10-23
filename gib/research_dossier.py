"""Produce bounded, inspectable evidence dossiers for human research review.

A retrieved page is not automatically a verified fact, and a news-index summary
is not primary-source evidence. No copyrighted news body is mirrored here.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

APPROVED = {"VERIFIED", "SOURCE_EXCERPT_MATCH_NOT_FACT_VERIFIED",
            "OFFICIAL_CONTEXT_UNVERIFIED", "ATTRIBUTED_UNVERIFIED"}

def make_dossiers(issue, max_events=3):
    dossiers=[]
    for article in (issue.get("articles") or [])[:max_events]:
        sources=article.get("sources") or []
        claims=article.get("evidence") or []
        source_ids={s.get("source_id") for s in sources}
        primary=[s for s in sources if s.get("kind")=="OFFICIAL_FEED"]
        located=[x for x in claims if x.get("source_location") not in (None, "", "feed headline/snippet")
                 and x.get("source_sha256")]
        signed=[x for x in located if x.get("verification")=="VERIFIED" and x.get("reviewer")]
        support=[]
        for c in claims:
            support.append({
                "claim_id":str(c.get("claim_id", "")),
                "text":str(c.get("text", ""))[:550],
                "source_id":c.get("source_id"),
                "source_valid":c.get("source_id") in source_ids,
                "verification":c.get("verification", "UNVERIFIED"),
                "source_location":c.get("source_location", ""),
                "retrieved_at":c.get("retrieved_at", ""),
                "source_sha256":c.get("source_sha256", ""),
                "official_excerpt":str(c.get("official_context_excerpt") or "")[:900],
                "signed_by":c.get("reviewer", ""),
            })
        notes=[]
        if not primary:notes.append("No linked primary official document for this event")
        if not located:notes.append("No located excerpt and hash for event claims")
        if len(signed)<3:notes.append("Fewer than three manually attested source claims")
        if len({s.get("publisher") for s in sources})<2:
            notes.append("Independent corroborating outlet not established")
        if not article.get("event_time_utc"):
            notes.append("Underlying event time differs from publication time or is unknown")
        dossiers.append({
            "event_id":article.get("event_id"),
            "event_title":article.get("title_original"),
            "published_at":article.get("article_published_at"),
            "event_time_utc":article.get("event_time_utc"),
            "editorial_state":"OPEN_NEEDS_HUMAN_REVIEW",
            "sources":[{
                "source_id":s.get("source_id"),
                "url":s.get("url"),
                "publisher":s.get("publisher"),
                "kind":s.get("kind"),
                "published_at":s.get("article_published_at"),
                "retrieval_status":s.get("retrieval_status", "UNRETRIEVED"),
                "retrieved_at":s.get("retrieved_at"),
                "source_sha256":s.get("source_sha256"),
            } for s in sources],
            "claims":support,
            "manually_attested_claims":len(signed),
            "review_questions":{
                "event_and_publication_dates":"Confirm event occurrence vs. article/report publishing time",
                "impact_transmission":"Which verified step links the event to economic outcomes?",
                "historical_comparator":"Which independent official historical data are comparable?",
                "counter_evidence":"What credible alternative explanation is supported?",
                "watch_next":"What scheduled publication could change the conclusion?",
            },
            "missing_evidence":notes,
            "automatically_verified":False
        })
    return dossiers

def write_review_workbook(issue, folder):
    """A physical review checklist. It is never an approval token."""
    root=Path(folder);root.mkdir(parents=True,exist_ok=True)
    dossiers=issue.get("research_dossiers") or make_dossiers(issue)
    target=root/"PRIMARY_EVIDENCE_REVIEW.md"
    lines=[
      "# Global Intelligence Brief — 一手證據及總編輯審核表",
      "",
      "**僅供 QA：未取得人工簽核，不代表任何消息已核實、可公開發布。**",
      f"刊物：{issue.get('issue_id')} · {issue.get('edition')} · {issue.get('report_date')}",
      "",
      "審稿順序：查閱官方頁面→確認數值/時間/口徑→記錄支持及反方證據"
      "→核對引文→Gemini 第一輪稿與第二輪稿逐項對照→文字總編輯→BOOX 實機。",
      "",
    ]
    for n,event in enumerate(dossiers,1):
        lines.extend([
            f"## {n:02d}｜{event.get('event_title')}",
            f"事件 ID：\`{event.get('event_id')}\`",
            f"來源發布時間：{event.get('published_at')}",
            f"事件發生時間：{event.get('event_time_utc') or '未核對'}",
            "",
            "**來源（本書僅收錄短摘要，不下載出版社受版權保護的全文）：**",
        ])
        for source in event.get("sources",[]):
            lines.append(
                f"- [{source.get('publisher')}]({source.get('url')}) · "
                f"ID \`{source.get('source_id')}\` · {source.get('kind')}"
                f" · {source.get('retrieval_status')}"
            )
        lines.extend(["", "**逐項核對：**", ""])
        for claim in event.get("claims",[]):
            lines.extend([
                f"- [ ] \`{claim.get('claim_id')}\`：{claim.get('text')}",
                f"  - 原始來源 ID：\`{claim.get('source_id')}\`；目前：{claim.get('verification')}",
                f"  - 來源定位：{claim.get('source_location') or '未提供'}",
                f"  - [ ] 數值、日期、單位、期間、調整口徑與原文一致",
                f"  - [ ] 反方／替代解釋有獨立證據",
                f"  - 審核者與日期：**尚未簽核**",
            ])
        lines.extend(["", "**仍需資料：**"])
        for missing in event.get("missing_evidence", []):
            lines.append("- "+missing)
        lines.extend([
            "",
            "總編輯判斷：**待審**",
            "實證支持／反方證據與觀察條件：**待填**",
            "---", ""
        ])
    target.write_text("\n".join(lines),encoding="utf-8")
    (root/"research_dossiers.json").write_text(
        json.dumps(dossiers,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"review_md":str(target),"dossiers_json":str(root/"research_dossiers.json"),
            "events":len(dossiers)}

def progress(issue):
    ds=issue.get("research_dossiers",[])
    return {
        "total_core_events":len(ds),
        "primary_source_linked":sum(any(x["kind"]=="OFFICIAL_FEED" for x in d["sources"]) for d in ds),
        "events_with_located_claim":sum(any(c["source_sha256"] and c["source_location"] for c in d["claims"]) for d in ds),
        "manually_reviewed_events":sum(d.get("manually_attested_claims",0)>=3 for d in ds),
        "auto_publish_permitted":False,
    }
