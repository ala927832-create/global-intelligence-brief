"""Offline source-faithful reading preview from six immutable RSS snapshots.
No LLM paraphrase from a headline; use publisher snippet as source excerpt.
"""
from pathlib import Path
from html import escape
from urllib.parse import urlsplit

def render(issue, eligible, output):
    lookup={r.get("url"):r for r in eligible}
    items=issue["selected"]
    assert len(items)==24
    lines=['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1">',
    '<title>GIB QA — 今日閱讀</title><style>',
    'body{font-family:system-ui,"Noto Sans TC",sans-serif;background:#f7f5f0;color:#232a31;margin:auto;max-width:840px;padding:32px 22px;line-height:1.8}',
    'h1{font-size:2rem}h2{border-bottom:1px solid #ccc;padding-bottom:8px;margin-top:38px}',
    '.story{border-bottom:1px solid #d6d8da;padding:18px 0}.meta{color:#5a6269;font-size:.9rem}',
    '.watch{background:#e9eef2;padding:18px;border-left:4px solid #455d77}',
    '.label{font-size:.8rem;font-weight:700;letter-spacing:.04em;color:#394d64}',
    'a{color:#234f83;overflow-wrap:anywhere}h3{font-size:1.17rem;line-height:1.5}',
    '</style></head><body><h1>Global Intelligence Brief｜編輯 QA 閱讀預覽</h1>',
    '<p>本頁是原始訂閱來源的標題與節錄，不是 AI 已核對的獨立事實，也不是正式刊物。</p>']
    relevance={"geopolitics":4,"central_banks":4,"energy":4,"macro":3,"technology":3,"asia":2,"corporates":2,"unexpected":1}
    first=max(items,key=lambda a:(relevance.get(a.get("topic"),1),a.get("rank_score",0),-a["position"]))
    watch_domain={"geopolitics":"地緣政治、能源安全與國際貿易","central_banks":"貨幣政策、利率與匯率","energy":"能源供應、運輸與生產成本","macro":"總體經濟、利率與市場預期","technology":"科技產業、資本支出與供應鏈"}.get(first.get("topic"),"國際政策與產業")
    watch_why="具有跨領域影響的政策或供應變動，應優先追蹤；這是編輯關注理由，不代表推測的後果已發生。"
    watch_next="觀察原報導後續更新、相關機構公告與市場反應；保留未確定事項的條件語氣。"
    lines+=['<section class="watch"><div class="label">當日特別注意｜編輯候選</div>',
      '<h3>'+escape(first["title"])+'</h3>',
      '<p><strong>選題理由：</strong>'+escape(watch_why)+'</p>',
      '<p><strong>可能影響領域：</strong>'+escape(watch_domain)+'</p>',
      '<p><strong>後續觀察：</strong>'+escape(watch_next)+'</p></section>']
    with_excerpt=0
    for i,a in enumerate(items):
        if i==0 or i==12:
            lines.append('<h2>'+('主要新聞｜12則' if i==0 else '補充新聞｜12則')+'</h2>')
        link=a["urls"][0]
        origin=lookup.get(link,{})
        snippet=' '.join(str(origin.get("snippet") or origin.get("description") or "").split())
        has_excerpt=len(snippet)>=40
        if has_excerpt:with_excerpt+=1
        lines+=['<article class="story"><div class="label">'+str(i+1).zfill(2)+'</div>',
         '<h3>'+escape(a["title"])+'</h3>',
         '<div class="meta">來源：'+escape(str(origin.get("source_name") or urlsplit(link).hostname))+
         ' ｜分類：'+escape(str(a.get("topic") or '未分類'))+'</div>',
         '<p><strong>'+( '原始來源節錄（非 AI 改寫）' if has_excerpt else '資料限制')+'</strong>：'+
          escape(snippet[:500] if has_excerpt else '目前僅能核對原始標題，沒有足夠文字製作忠實摘要。')+'</p>',
         '<a href="'+escape(link,quote=True)+'">原始報導</a></article>']
    lines+=['<h2>不同觀點與延伸分析</h2>',
      '<p>此 QA 版本沒有從來源以外推測反方主張；本區保留獨立分析版位，不修改上述新聞。</p>',
      '</body></html>']
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(lines),encoding="utf-8")
    return {"html_path":str(output),"article_count":len(items),
      "publisher_excerpt_count":with_excerpt,"headline_only_count":len(items)-with_excerpt,
      "ai_paraphrase_generated":False,"counter_views_isolated":True,
      "special_watch_present":True,"watch_position":first["position"],"watch_why":watch_why,"watch_domain":watch_domain,"watch_next":watch_next}
