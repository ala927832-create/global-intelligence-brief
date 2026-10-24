"""Read-only GitHub Actions QA summary. Unverified news is not published."""
from __future__ import annotations
import html
import json
import os
import re
from pathlib import Path


def safe(x):
    return html.escape(str(x or ""), quote=True)


def main():
    obj = json.loads(Path(os.getenv("QA_RUN_PATH", "qa_run.json")).read_text(encoding="utf-8"))
    issue = json.loads(Path(obj["issue_json"]).read_text(encoding="utf-8"))
    health = issue.get("source_health", {})
    drafts = issue.get("editorial_drafts", [])
    draft_text = " ".join(
        " ".join(str(x) for x in draft.get("sections", {}).values())
        for draft in drafts
    )
    draft_hanzi = len(re.findall(r"[\u3400-\u9fff]", draft_text))
    book_hanzi = {}
    for level in ("essential", "deep"):
        filename = obj.get("epub", {}).get(level, {}).get("xhtml")
        try:
            html_text = Path(filename).read_text(encoding="utf-8") if filename else ""
            book_hanzi[level] = len(re.findall(r"[\u3400-\u9fff]",
                re.sub(r"<[^>]*>", "", html_text)))
        except OSError:
            book_hanzi[level] = 0
    depth = issue.get("editorial_depth_audit") or obj.get("editorial_depth_audit") or {}
    evidence=obj.get("primary_evidence_progress") or {}
    gemini=issue.get("gemini_editorial") or {}
    gemini_status=gemini.get("status","NOT_REQUESTED")
    gemini_stage=gemini.get("failed_stage") or "NOT_APPLICABLE"
    gemini_http=gemini.get("http_status")
    gemini_label=("雙輪完成但尚待人工審稿" if gemini_status=="REVISED_DRAFT_PENDING_REVIEW"
                  else "未啟用" if gemini_status=="NOT_REQUESTED"
                  else "未完成；請查核 API、模型權限、額度及回應")
    if gemini_status=="ERROR_NO_PAID_FALLBACK" and gemini_http:
        gemini_label+=f"（{safe(gemini_stage)}：HTTP {gemini_http}）"
    rows = [
        "# Global Intelligence Brief — 新聞試刊 QA",
        "",
        "**NOT APPROVED — 僅供內部測試，沒有對外發布。**",
        "",
        f"刊物：{safe(issue.get('edition'))} · {safe(issue.get('report_date'))}",
        "",
        "| 指標 | 實際結果 |", "|---|---:|",
        f"| 原始新聞候選 | {health.get('candidate_count', 0)} |",
        f"| 合併去重後 | {health.get('unique_count', 0)} |",
        f"| 入選新聞 | {len(issue.get('articles', []))} / 目標 8–12 |",
        f"| 完整深度研究專題 | {len(issue.get('deep_research', []))} / 目標 2–3 |",
        f"| 官方來源對應事件 | {evidence.get('primary_source_linked',0)}/{evidence.get('total_core_events',0)} |",
        f"| 來源定位事件 | {evidence.get('events_with_located_claim',0)}/{evidence.get('total_core_events',0)} |",
        f"| AI 延伸研究草稿（不等於已審定專題） | {len(drafts)} 篇，約 {draft_hanzi} 漢字 |",
        f"| 達到深讀審稿最低門檻（非出版許可） | {depth.get('deep_drafts_meeting_minimum_review_standard',0)}／{depth.get('required_depth_topics',2)} |",
        f"| Essential／Deep 實際內頁漢字數 | {book_hanzi['essential']}／{book_hanzi['deep']} |",
        f"| 晨晚報增量比較 | {'有' if health.get('has_morning_comparison') else '缺少晨報快照'} |",
        f"| Gemini 第一／二輪編輯 | {gemini_label} |",
        "",
        "## 入選新聞候選（未核實）", "",
    ]
    for k, article in enumerate(issue.get("articles", []), 1):
        s = (article.get("sources") or [{}])[0]
        rows.append(f"{k}. **{safe(article.get('title_original'))}** · {safe(s.get('publisher'))} · {safe(article.get('article_published_at'))}")
    if not issue.get("articles"):
        rows.append("沒有入選新聞。")
    rows.extend(["", "## 深讀研究的證據與內容缺口", ""])
    for topic in depth.get("research", []):
        rows.append("- **"+safe(topic.get("title"))+"**："+
                    str(topic.get("chinese_analysis_hanzi",0))+" 個分析漢字；"+
                    str(topic.get("evidence",{}).get("signed_verified_claims",0))+" 項已人工簽核的主張")
        for reason in topic.get("reasons",[])[:5]:
            rows.append("  - "+safe(reason))
    if not depth.get("research"):
        rows.append("目前尚無經 Gemini 雙輪整理的核心研究稿。")
    rows.extend(["", "## 正式發布遭拒原因", ""])
    for reason in obj.get("release_hold_reasons", []):
        rows.append("- " + safe(reason))
    if obj.get("collector_errors"):
        rows.extend(["", "## 資料來源錯誤", ""])
        for error in obj["collector_errors"][:10]:
            rows.append("- " + safe(str(error).split(" for url:")[0][:160]))
    rows.extend([
        "", "## 怎麼閱讀試刊？", "",
        "在本次 GitHub Actions 執行頁向下捲到 Artifacts，下載 gib-editorial-qa ZIP。解壓縮後可找到 Essential EPUB、Deep EPUB、XHTML 與 issue.json。",
        "",
        "EPUBCheck 通過只代表檔案格式正確，不代表新聞可信、達到閱讀深度或可以發布。",
        "",
    ])
    output = "\n".join(rows) + "\n"
    target = os.getenv("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as file:
            file.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
