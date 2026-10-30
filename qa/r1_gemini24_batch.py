"""Produce 24 Gemini short briefs from frozen approved RSS, QA-only, fail closed.
No news publication or inference from unsupported metadata.
"""
import os,io,json,zipfile,re,time,html,requests
from pathlib import Path
from urllib.parse import urlsplit
from qa.p2_content_gate import eligible_source_rows
from datetime import datetime
from gib.gemini_editor_v16 import _call, unsupported_numeric_evidence
from gib.editorial import canon_url

REPO="ala927832-create/global-intelligence-brief"
SOURCE_ARTIFACT=12944730644
REPLAY_ARTIFACT=12953500095
ROOT=Path("qa_out/r1_gemini_24")

def get_artifact(n):
 token=os.environ["GH_TOKEN"]
 r=requests.get(f"https://api.github.com/repos/{REPO}/actions/artifacts/{n}/zip",
   headers={"Authorization":"Bearer "+token},timeout=(10,60))
 r.raise_for_status()
 return zipfile.ZipFile(io.BytesIO(r.content))

def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 report={"schema":"GIB_R1_GEMINI24_QA","publication":"OFF","gemini_status":"NOT_CALLED",
 "fidelity_gate":"HOLD","expert_score":None,"editorial_signoff":False}
 try:
  originals=get_artifact(SOURCE_ARTIFACT)
  replay=get_artifact(REPLAY_ARTIFACT)
  d=json.loads(originals.read("snapshot_01.json"))
  selected=json.loads(replay.read("review_01.json"))["selected"]
  eligible,*_=eligible_source_rows(d["rows"],datetime.fromisoformat(d["started_at_utc"]),"morning")
  sources={canon_url(c["url"]):c for c in eligible}
  payload=[]
  for a in selected:
   url=a["urls"][0];origin=sources.get(canon_url(url),{})
   excerpt=" ".join(str(origin.get("snippet") or origin.get("description") or "").split())
   payload.append({"index":a["position"],"title":a["title"],"url":url,
     "publisher":origin.get("source_name") or urlsplit(url).hostname,
     "excerpt":excerpt[:650],"tier":a["tier"],"topic":a["topic"]})
  assert len(payload)==24 and all(x["publisher"] and x["url"].startswith("https://") for x in payload)
  (ROOT/"originals.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2))
  if not os.environ.get("GEMINI_API_KEY"):
   report["gemini_status"]="NO_GEMINI_API_KEY"
   return
  report["gemini_status"]="STARTED"
  drafts=[]
  for start in range(0,24,6):
   group=payload[start:start+6]
   task=("你是繁體中文國際新聞編輯。僅依新聞出版者提供的原始標題和摘要做簡明新聞速讀。"
         "不要改變原作者立場，不得加入來源未寫出的事實、數字、引述或推論；"
         "若標題以聲稱、預期、可能、批評、指控等敘述，必須保留歸屬和不確定性。"
         "僅來源標題沒有摘錄時，brief 留空並標記 HEADLINE_ONLY。"
         "禁止模仿或複製來源長段文字；請用自己的繁體中文濃縮，每則40-100字。"
         "不要生成分析、相反看法或投資建議。"
         "只輸出JSON物件，欄位 briefs 陣列，每筆包含 index 數字、brief 字串、basis 字串。"
         "原始來源資訊："+json.dumps(group,ensure_ascii=False))
   raw=_call(task,os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite"))
   entries=raw.get("briefs",[])
   if len(entries)!=len(group):raise ValueError("GEMINI_BATCH_COUNT_MISMATCH")
   for base,out in zip(group,entries):
    if out.get("index")!=base["index"]:raise ValueError("INDEX_MISMATCH")
    brief=str(out.get("brief","")).strip()
    if len(base["excerpt"])<40:
     if brief:raise ValueError("AI_SUMMARIZED_HEADLINE_ONLY")
    else:
     if not 20<=len(brief)<=220:raise ValueError("LENGTH_OR_EMPTY")
     if unsupported_numeric_evidence(brief,base["title"]+" "+base["excerpt"]):
      raise ValueError("AI_ADDED_UNSUPPORTED_NUMERIC_FACT")
    drafts.append(dict(base,brief=brief,basis=out.get("basis")))
  report["gemini_status"]="GENERATED_24"
  (ROOT/"drafts.json").write_text(json.dumps(drafts,ensure_ascii=False,indent=2))
  # Independent second pass sees sources and drafts; expressly request failure findings
  critique=_call("你是獨立新聞校對編輯，逐篇比對以下24則原始摘要和AI速讀，僅針對忠實度作嚴格審查。"
     "新聞來自核准來源，不要求額外查證；不得以不同意媒體主張為理由扣分。"
     "每則檢查是否新增無來源的事實、改變主張歸屬、將可能改成確定、抹去相反觀點或誇大重要性。"
     "輸出JSON物件，欄位 reviews 陣列，每筆包含 index 數字、fidelity_score 整數、pass 布林、issues 字串陣列。"
     "必須24筆，分數非自動通過："+json.dumps(drafts,ensure_ascii=False),
     os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite"))
  reviews=critique.get("reviews",[])
  if len(reviews)!=24:raise ValueError("INCOMPLETE_CRITIQUE")
  by_idx={r["index"]:r for r in reviews}
  if len(by_idx)!=24:raise ValueError("DUPLICATED_CRITIQUE")
  for d in drafts:
   d["review"]=by_idx[d["index"]]
  (ROOT/"audit_24.json").write_text(json.dumps(drafts,ensure_ascii=False,indent=2))
  report["fidelity_average"]=round(sum(r.get("fidelity_score",0) for r in reviews)/24,2)
  report["fidelity_pass_count"]=sum(bool(r.get("pass")) for r in reviews)
  report["fidelity_gate"]="PASS" if report["fidelity_average"]>=90 and report["fidelity_pass_count"]==24 else "HOLD"
  watch=max(drafts,key=lambda x:({"geopolitics":4,"central_banks":4,"energy":4,"macro":3,"technology":3}.get(x["topic"],1),-x["index"]))
  report["watch_index"]=watch["index"]
  style="""body{max-width:850px;margin:auto;background:#f7f5ef;color:#202b38;font-family:system-ui,sans-serif;line-height:1.85;padding:28px}h1{font-size:2rem}h2{margin-top:40px;border-bottom:1px solid #bbb}article{border-bottom:1px solid #ddd;padding:16px 0}small{color:#5c6772}.watch{background:#e4ebee;border-left:5px solid #435d73;padding:18px}a{overflow-wrap:anywhere;color:#23537a}p{margin:8px 0}"""
  page=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
   '<title>GIB Gemini 24 QA</title><style>'+style+'</style><h1>Global Intelligence Brief｜24則速讀 QA</h1>',
   '<p>新聞速讀依據訂閱來源標題與節錄生成；新聞來源主張不等於獨立事實認證。本頁僅為 QA 草稿，未發刊。</p>',
   '<section class="watch"><strong>當日特別注意｜編輯候選</strong><h3>'+html.escape(watch["title"])+'</h3>',
   '<p>選題理由：該報導涉及可能跨市場的重大政策或供應風險，值得監測；此理由是獨立分析，不是原新聞主張。</p>',
   '<p>可能影響：政策、供應鏈與市場預期（潛在機制，未視為已發生的後果）。</p>',
   '<p>接下來觀察：事件後續、主管機關更新與市場變化。 </p></section>']
  for d in drafts:
   if d["index"] in (1,13):page.append("<h2>"+("主要新聞｜12則" if d["index"]==1 else "補充新聞｜12則")+"</h2>")
   page.extend(["<article><small>"+str(d["index"])+" · "+html.escape(d["publisher"])+"</small>",
     "<h3>"+html.escape(d["title"])+"</h3>",
     "<p><strong>AI 忠實速讀：</strong>"+html.escape(d["brief"] or "來源僅有標題，不擴寫內容")+"</p>",
     "<details><summary>原始來源節錄及核對</summary><p>"+html.escape(d["excerpt"] or "來源無摘要")+"</p></details>",
     '<p><a href="'+html.escape(d["url"],quote=True)+'">出版者原文</a></p></article>'])
  page.extend(["<h2>獨立觀點及延伸分析</h2>","<p>此 QA 批次未生成獨立研究全文；不得把沒有來源支持的分析混入新聞速讀。</p>","</html>"])
  (ROOT/"reader.html").write_text("\\n".join(page))
 except Exception as e:
  report["gemini_status"]="ERROR_"+type(e).__name__
  report["error_stage"]="GEMINI_OR_AUDIT"
 finally:
  (ROOT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
  print("GEMINI24_QA",json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":main()
