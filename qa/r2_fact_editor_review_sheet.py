"""Generate an internal 18-claim human-review checklist, not publishing approval."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"qa/r2_crosssource_claim_ledger_20261029.json"


def render(ledger):
    lines=[
        "# GIB R2｜2026-10-29 原始資料與編輯簽核表（只限內部）",
        "",
        "狀態：HOLD；尚無任何人員完成事實簽核。此清單並非讀者預覽或核准發刊。",
        "",
        "核查順序：定位原始文件與發布時間 → 比對數值、單位、資料期間 →",
        "檢查另一來源與不同解釋 → 區分實績、預測和因果假說 → 編輯簽核。",
        "",
    ]
    counter=0
    for dossier in ledger["dossiers"]:
        lines += [
            "## 焦點："+dossier["topic"]+"｜"+dossier["event_id"],"",
            "### 原始來源及日期","",
        ]
        for source in dossier["sources"]:
            date=source["publication_date"] or "未標定日期"
            lines.append(
                "- "+source["id"]+"：[來源 "+source["issuer"]+"]("+source["url"]+")，"
                +date+"，類別："+source["role"]
            )
        lines += ["","### 逐項主張",""]
        for claim in dossier["claims"]:
            counter+=1
            lines += [
                "#### "+claim["id"]+"｜"+claim["claim_kind"],"",
                claim["statement"],"",
                "來源："+", ".join(claim["source_ids"])+"；觀察日期："+str(claim.get("observation_date") or "未標定"),"",
                "論證限制："+claim["limitation"],"",
                "- [ ] 檔案來源、確切頁碼／表格／段落可定位",
                "- [ ] 數值、單位、資料時間、名目與實質及季調口徑已核對",
                "- [ ] 與獨立機構資料或具體反證逐項比較",
                "- [ ] 沒有把預測、調查或研究者推論偽稱為已實現事實",
                "- [ ] 編輯者填寫核對日、原始文件雜湊與簽核結果",
                "",
                "狀態：未簽核，不得標示 VERIFIED。",""
            ]
        lines += ["### 已定位之反方或限制性材料",""]
        for item in dossier["counterevidence"]:
            lines.append("- "+item["id"]+"："+item["statement"]+"；資料："+", ".join(item["source_ids"]))
        lines += ["","### 因果傳導假說（非因果證明）",""]
        for step in dossier["mechanism"]:
            lines.append("- "+str(step["step"])+"："+step["link"]+"；"+step["status"])
        lines += ["","### 可否證條件",""]
        for check in dossier["falsification"]:lines.append("- "+check)
        lines += ["","### 未完成證據",""]
        for gap in dossier["remaining_gaps"]:lines.append("- [ ] "+gap)
        lines += ["","篇章結論：HOLD，尚無獨立人員事實核查及編輯簽章。","","---",""]
    lines += [
        "## 兩輪 Gemini 與發刊狀態","",
        "- [ ] 四篇分析事實簽章",
        "- [ ] 至少一篇研究具原始來源、歷史比較、反方證據與可否證條件",
        "- [ ] 第一輪 Gemini 有實質修訂記錄（僅前兩項完成才可進行）",
        "- [ ] Python 再核對所有修訂主張、數據與引用",
        "- [ ] 第二輪 Gemini 只修復已核實問題",
        "- [ ] 完整刊物 20–24 則、閱讀時長與去重完成驗收",
        "- [ ] 編輯、使用者與裝置檢查另外完成",
        "",
        "主張："+str(counter)+"；已完成的人工簽章：0；Gemini 尚未授權執行。",
    ]
    return "\n".join(lines)+"\n"


def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: python qa/r2_fact_editor_review_sheet.py OUTPUT.md")
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    dest=Path(sys.argv[1])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(render(ledger),encoding="utf-8")
    print(json.dumps({
        "review_sheet":str(dest),
        "total_claims":sum(len(d["claims"]) for d in ledger["dossiers"]),
        "editor_verified_claims":0,"gemini_called":False,
        "release_approved":False,"status":"INTERNAL_HOLD"
    },ensure_ascii=False))

if __name__=="__main__":main()
