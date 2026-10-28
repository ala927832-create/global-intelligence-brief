"""Frozen 6-section editorial publishing: one issue.json to two reflowable EPUB3 books.

The exporter produces QA-labeled artefacts, not approved news. It never infers
quality from file generation, word count or the mere existence of source URLs.
"""
from __future__ import annotations
import html, json, re, shutil, subprocess, tempfile
from pathlib import Path
from zipfile import ZipFile
from .contract import locked_contract
from .epub import make_cover, validate_epub

ROOT=Path(__file__).resolve().parents[1]
CSS=ROOT/'assets'/'editorial'/'newsroom-v16.css'

def h(v):return html.escape(str(v or ''),quote=True)
def paras(v):return ''.join(f'<p>{h(s)}</p>' for s in re.split(r'\n\s*\n',str(v or '')) if s.strip())
def source_grounded_digest(article):
    """Only quote-or-paraphrase text already bound to this source record.

    A headline/snippet is never a complete article or independent fact proof.
    Editorial source summaries and attributed key points may supplement it,
    but only with a matching source_id to block invented provenance.
    """
    sources={x.get('source_id') for x in article.get('sources',[]) if x.get('source_id')}
    digest=article.get('source_digest') or {}
    details=[]
    for row in digest.get('points',[]) if isinstance(digest,dict) else []:
        if isinstance(row,dict) and row.get('source_id') in sources and row.get('text'):
            details.append(str(row['text']).strip())
    for row in article.get('reported_key_points',[]):
        if isinstance(row,dict) and row.get('source_id') in sources and row.get('text'):
            details.append(str(row['text']).strip())
    if not details and article.get('headline_summary'):
        details=[str(article['headline_summary']).strip()]
    # Remove exact repeats, and never combine headlines into invented conclusions.
    return list(dict.fromkeys(x for x in details if x))

def source_grounded_fallback(article):
    """Readable evidence-bound digest when no model edit was produced."""
    points=source_grounded_digest(article)
    if not points:
        return ('<div class="context"><h4>來源目前公開的資訊</h4>'
                '<p>來源索引只有新聞標題，沒有可供可靠整理的正文或摘要；'
                '請透過下方原文來源閱讀，系統不會自行補寫事實。</p></div>')
    source=article.get('sources',[{}])[0]
    link='<a href="'+h(source.get('url'))+'">閱讀原始報導</a>' if source.get('url') else ''
    return ('<div class="context"><h4>來源報導重點（尚未獨立完成查核）</h4><ul>'+
            ''.join('<li>'+h(x)+'</li>' for x in points)+'</ul>'+
            ('<p class="source-note">'+link+' · '+h(source.get('publisher'))+
             ' · '+h(article.get('article_published_at'))+'</p>' if link else '')+
            '<p class="source-note">整理範圍止於來源現有的摘要與附帶資料；'
            '沒有全文的事件不能冒稱已完成全文重點整理。</p></div>')

def heading(num,name,title):
    return f'<p class="section-number">{num}｜{h(name)}</p><h2>{h(title)}</h2>'

def anchor_id(item):
    """Stable, trusted local fragment derived from the verified event identifier."""
    raw=str(item.get("event_id",""))
    clean=re.sub(r"[^a-zA-Z0-9_-]","",raw)[:72]
    return clean or "missing-id"

def source_anchor(source):
    raw=str(source.get("source_id",""))
    return "src-"+re.sub(r"[^a-zA-Z0-9_-]","",raw)[:74]

def reading_index(items, isdeep, draft_ids=()):
    # Pandoc's HTML5 reader strips IDs on <nav> and <article>. Its EPUB3
    # converter preserves IDs on semantic classed <div> elements instead.
    # Keep all navigation resources embedded; no runtime network required.
    rows=['<div class="offline-reading-index" aria-label="本書離線導覽">',
          '<h2 id="reading-index">本書閱讀路線｜離線可用</h2>',
          '<p>先從全球快訊了解全貌，再點選本書的深入解析。'
          '延伸研究與來源摘要均已包含在本 EPUB，只有查閱外部網站才需要網路。</p>',
          '<ol class="reading-path">']
    for idx,item in enumerate(items,1):
        key=anchor_id(item)
        jump=(f'<a class="jump-deep" href="#analysis-{key}">→ 事件解析</a>' if idx<=5
              else '<span class="small-note">全球短訊</span>')
        if isdeep and item.get('event_id') in draft_ids:
            jump+=f' <a class="jump-deep" href="#research-{key}">→ 深入研究草稿</a>'
        rows.append('<li><span class="index-number">'+f"{idx:02d}"+'</span> '
          +f'<a href="#brief-{key}">{h(item.get("title_original"))}</a> '
          +jump+'</li>')
    rows.extend(['</ol>', '<p class="offline-mode">完整研究：'
        +('<a href="#deep-research">跳至深度研究</a>' if isdeep else '請使用同一期的 Deep Research 離線合輯')
        +'　·　<a href="#sources">來源與證據清單</a></p></div>'])
    return ''.join(rows)

def issue_body(issue, edits=None, level='essential'):
    contract=locked_contract()
    if level not in ('essential','deep'):raise ValueError('unsupported reading level')
    edit_by_id={e['event_id']:e for e in (edits or [])}
    items=issue.get('articles',[])
    draft_ids={e['event_id'] for e in (edits or [])
               if len(''.join(str(z) for z in e.get('sections',{}).values()))>=120}
    # Original research topic anchors are navigable even without AI drafts.
    draft_ids.update(str(topic.get('event_id')) for topic in issue.get('deep_research',[])
                     if topic.get('event_id'))
    isdeep=(level=='deep')
    period='晨報' if issue['edition']=='morning' else '晚報'
    targets=contract.get('versions') or []
    idx=1 if isdeep else 0
    active_target=(targets[idx].get('minutes') if issue['edition']=='morning'
                   else targets[idx].get('evening_minutes',targets[idx].get('minutes'))) if len(targets)>idx else None
    reading_target=(' · '+h(active_target)+' 分鐘目標（人工閱讀未驗收）' if active_target else '')
    qa=issue.get('editorial_status')!='EDITOR_APPROVED'
    result=['''<header class="issue-header" id="cover">
     <p class="overline">GLOBAL INTELLIGENCE BRIEF · LAYOUT 01</p>
     <div class="brand">Global<br/>Intelligence Brief</div>
     <p class="brand-sub">全球財經'''+period+((' · 深讀研究 QA' if qa else ' · 深讀研究') if isdeep else (' · 新聞閱讀 QA' if qa else ' · 新聞閱讀'))+reading_target+'''</p>
     <div class="issue-meta">'''+h(issue['report_date'])+' · Asia/Taipei · '+h(issue['as_of_utc'])+'''</div>
     <div class="topic-nav"><span>國際政經</span><span>全球經濟</span><span>科技產業</span><span>市場觀察</span></div>
     </header>''']
    if qa:
        result.append('<p class="quality-label"><strong>QA／非正式刊物：</strong>資料與研究尚未通過發行審核；'+
         '新聞索引並非已查證事實，未完成實機／EPUBCheck／10 交易日驗收。</p>')
        if issue.get('gemini_editorial',{}).get('status')=='SECOND_PASS_NO_MATERIAL_EDIT':
            result.append('<p class="quality-label"><strong>雙輪編輯未通過：</strong>'+
                '本書所見的研究文字僅供人工比對。第二輪沒有提供足夠的實質修訂，'+
                '不能認定完成深度研究，也不得作為正式發布內容。</p>')
    result.append(reading_index(items,isdeep,draft_ids))
    if isdeep:
        topic_count=len(issue.get('deep_research') or [])
        if topic_count:
            links='　'.join('<a href="#research-topic-'+str(i+1)+'">專題 '+str(i+1)+'</a>'
                           for i in range(topic_count))
            result.append('<div class="in-book-link"><strong>直接閱讀深度研究：</strong> '+
                          links+' · <a href="#deep-research">進入專題章節</a></div>')
        else:
            result.append('<p class="quality-label">本次尚未建立通過來源證據審查的獨立研究專題；'
                          '下方保留來源導讀，不以重複摘要冒稱 40–50 分鐘深讀。</p>')
    # 01. Executive Brief
    result.append('<section class="opening" id="executive">'+heading('01','Executive Brief','本期三個最值得追蹤的主題'))
    result.append('<p class="intro">本期挑選重要的世界動態，呈現來源、背景及不確定性。'+
      ('晚報以晨報之後出現的實質新消息及新的官方證據為重點。' if issue['edition']=='evening' else
       '晨報著重夜間全球變化與今天已知的關鍵議程。')+'</p>')
    for i,x in enumerate(items[:3],1):
        e=edit_by_id.get(x['event_id']) or {}
        title=e.get('headline_zh') or x['title_original']
        lead=e.get('brief_zh') or x.get('headline_summary') or '尚待來源核實'
        result.append(f'<div class="executive-point"><span class="point-no">{i:02d}</span>'
            +f'<strong><a href="#analysis-{anchor_id(x)}">{h(title)}</a></strong>'
            +f'<p>{h(lead)}</p></div>')
    if len(items)<3: result.append('<p class="quality-label">未能取得三項有充分來源的焦點，不以虛構內容補足。</p>')
    if issue['edition']=='evening':
        result.append('<p class="source-note">本期增量比對：'+('已與早報證據快照比較。' if issue.get('source_health',{}).get('has_morning_comparison') else '未提供晨報快照，不能宣稱當日新聞增量。')+'</p>')
    result.append('</section>')
    # 02. The World in Brief
    result.append('<section class="world-section" id="world">'+heading('02','The World in Brief','全球精選新聞與來源'))
    if not items:result.append('<p>尚無符合有效來源及日期條件的消息。</p>')
    for i,x in enumerate(items,1):
        source=x['sources'][0]
        result.append(f'<div class="brief"><p class="brief-index">{i:02d} · {h(x["topic_label"])} · {h(x.get("article_published_at") or "日期不詳")}</p>')
        e=edit_by_id.get(x['event_id']) or {}
        title=e.get('headline_zh') or x['title_original']
        lead=e.get('brief_zh') or x.get('headline_summary') or '原始摘要不足'
        result.append(f'<h3 id="brief-{anchor_id(x)}">{h(title)}</h3><p class="article-deck">{h(lead)}</p>')
        if e.get('headline_zh') and title!=x['title_original']:
            result.append(f'<p class="source-note">原始標題：{h(x["title_original"])}　·　中文由 AI 編輯，尚待核實</p>')
        target=f'#analysis-{anchor_id(x)}' if i<=5 else '#sources'
        result.append(f'<p class="in-book-link"><a href="{target}">→ 本書深入閱讀／核查來源</a>'
                      f'　·　<a href="#{source_anchor(source)}">來源索引</a></p></div>')
    result.append('</section>')
    # 03. Essential Analysis
    result.append('<section class="focus" id="analysis">'+heading('03','Essential Analysis','重要事件｜背景、意義與傳導機制'))
    for i,x in enumerate(items[:5],1):
        edit=edit_by_id.get(x['event_id']);s=edit.get('sections',{}) if edit else {}
        title=(edit or {}).get('headline_zh') or x['title_original']
        result.append(f'<div class="focus-piece"><p class="eyebrow">ANALYSIS {i:02d} · {h(x["topic_label"])}</p><h3 id="analysis-{anchor_id(x)}">{h(title)}</h3>')
        if (edit or {}).get('brief_zh'):
            result.append('<p class="lead">'+h(edit['brief_zh'])+'</p>')
        for key,title in [('background','事件背景'),('why_it_matters','為何值得了解'),('transmission','可能影響機制')]:
            if s.get(key):result.append(f'<div class="context"><h4>{title}</h4>{paras(s[key])}</div>')
        if s.get('alternative'):result.append('<div class="evidence"><strong>替代解釋</strong>'+paras(s['alternative'])+'</div>')
        if s.get('limitations'):result.append('<div class="evidence"><strong>證據限制</strong>'+paras(s['limitations'])+'</div>')
        if not edit or not any(s.get(key) for key in ('background','why_it_matters','transmission')):
            result.append(source_grounded_fallback(x))
        first=x["sources"][0]
        follow=(f'　·　<a href="#research-{anchor_id(x)}">閱讀本書深入研究</a>'
                if isdeep and x['event_id'] in draft_ids else '')
        result.append(f'<p class="source-note"><a href="#{source_anchor(first)}">本書證據與引用說明</a>'
                      +follow+'　·　<a href="#reading-index">返回索引</a></p></div>')
    if len(items)<3:result.append('<p class="quality-label">重點事件不足 3 項，不符合正式速讀內容門檻。</p>')
    result.append('</section>')
    # 04. Deep Research. Frozen chapter remains in both editions; substantive deep content only in deep edition.
    result.append('<section class="longread" id="deep-research">'+heading('04','Deep Research','專題研究｜歷史、數據、替代觀點與推翻條件'))
    if not isdeep:
        result.append('<p>此章節的完整研究僅在同一期 Deep Research EPUB 展開。速讀版不以重複文字或未經驗證推論填充篇幅。</p>')
    elif issue.get('deep_research'):
        for i,topic in enumerate(issue['deep_research'],1):
            topic_anchor=(f' id="research-topic-{i}"')
            if topic.get('event_id'):
                topic_anchor=topic_anchor[:-1]+'><span id="research-'+anchor_id(topic)+'"></span'
            result.append(f'<div class="dossier"><p class="eyebrow">RESEARCH {i:02d} · 待人工簽核</p><h3{topic_anchor}>{h(topic["title"])}</h3>')
            if topic.get('question'):
                result.append('<p class="lead">'+h(topic['question'])+'</p>')
            if topic.get('source_ids'):
                result.append('<p class="source-note">研究來源識別碼：'+h(', '.join(topic['source_ids']))+'</p>')
            for sec in topic.get('sections',[]):
                result.append(f'<div class="dossier-section"><h4>{h(sec["heading"])}</h4>{paras(sec.get("body",""))}')
                fig=sec.get('figure') or {}
                if fig.get('file'):
                    path=ROOT/'assets'/'editorial'/fig['file']
                    if path.is_file():result.append(f'<figure class="research-figure"><img src="{h(path.as_uri())}" alt="{h(fig.get("title") or "數據圖")} "/><figcaption>{h(fig.get("caption") or "")}</figcaption></figure>')
                result.append('</div>')
            if topic.get('conclusions'):
                result.append('<div class="evidence"><h4>研究結論（待人工簽核）</h4><ul>'+
                              ''.join('<li>'+h(x)+'</li>' for x in topic['conclusions'])+'</ul></div>')
            if topic.get('falsifiers'):
                result.append('<div class="watch"><h4>可推翻條件與觀察項目</h4><ul>'+
                              ''.join('<li>'+h(x)+'</li>' for x in topic['falsifiers'])+'</ul></div>')
            result.append('</div>')
    else:
        # Helpful offline long-form draft navigation, with strict attribution:
        # AI editorial text is interpretation, never primary-source verification.
        draft_items=[(x,edit_by_id.get(x.get('event_id'))) for x in items[:3]]
        draft_items=[(x,e) for x,e in draft_items
            if e and len(''.join(str(z) for z in e.get('sections',{}).values()))>=120]
        if draft_items:
            result.append('<p class="quality-label">下列是依新聞來源整理的 AI 延伸研究草稿，未取得完整一手證據；'
                          '不得冒稱已完成的 30–45 分鐘正式深度研究。</p>')
            for i,(x,e) in enumerate(draft_items,1):
                headline=e.get('headline_zh') or x['title_original']
                result.append(f'<div class="dossier">'
                    f'<p class="eyebrow">RESEARCH WORKING DRAFT {i:02d} · 待驗證</p><h3 id="research-{anchor_id(x)}">{h(headline)}</h3>')
                if e.get('brief_zh'):
                    result.append('<p class="lead">'+h(e['brief_zh'])+'</p>')
                sections=e.get('sections',{})
                # The book already includes background, importance and
                # transmission in Essential Analysis. Do not paste the same
                # paragraphs again; true deep reading must ADD evidence.
                result.append('<p class="source-note">本篇銜接前面的事件解析，以下只列出'
                              '新增的歷史對照、反面解釋、可驗證觀察及研究限制；'
                              '若無額外證據，內容將保持較短，並明確標示未完成。</p>')
                distinct_sections=[('history','歷史脈絡與可比性'),
                                   ('alternative','替代解釋與反方論證'),
                                   ('watch','未來應查證的證據'),
                                   ('limitations','資料限制與反證條件')]
                for key,label in distinct_sections:
                    if sections.get(key):
                        result.append(f'<div class="dossier-section"><h4>{label}</h4>{paras(sections[key])}</div>')
                result.append(f'<p class="source-note"><a href="#{source_anchor(x["sources"][0])}">'
                              '回看本書來源與證據</a>　·　<a href="#reading-index">返回索引</a></p></div>')
        else:
            result.append('<p class="quality-label">本期尚無 2–3 項具備原始證據、歷史資料與反方材料的深入研究，不能標示為完成的 30–45 分鐘深度刊物。</p>')
    result.append('</section>')
    # 05. What Changed & What to Watch
    result.append('<section class="follow" id="watch">'+heading('05','What Changed & What to Watch','新證據、判斷變化與未來一週'))
    if issue['edition']=='evening' and not issue.get('source_health',{}).get('has_morning_comparison'):
        result.append('<p class="quality-label">未完成今日早報快照比對，不能宣稱任何事件為新進展。</p>')
    updates=issue.get('event_updates',[])
    for change in updates:result.append(f'<div class="watch"><h4>{h(change.get("event_title","新證據"))}</h4>{paras(change.get("summary",""))}</div>')
    n=0
    for x in items[:5]:
        s=(edit_by_id.get(x['event_id']) or {}).get('sections',{})
        if s.get('watch'):
            result.append(f'<div class="watch"><h4>{h(x["title_original"])}</h4>{paras(s["watch"])}</div>');n+=1
    for ev in issue.get('upcoming_events',[]):
        result.append(f'<div class="watch"><h4>{h(ev.get("date"))}｜{h(ev.get("title"))}</h4>{paras(ev.get("watch"))}</div>');n+=1
    if not n and not updates:result.append('<p>目前沒有經驗證的新增追蹤條件，等待官方公告及後續資料。</p>')
    if issue.get('zinc_watch'):
        result.append('<h3>Zinc Research Watch｜唯讀跨市場觀察</h3>')
        for row in issue['zinc_watch'][:2]:
            result.append(f'<div class="evidence"><strong>{h(row.get("asset"))}</strong>　{h(row.get("market_date"))}<p>{h(row.get("observation"))}</p></div>')
        result.append('<p class="source-note">Zinc 的技術研究不等於已驗證新聞；不包含私人庫存、採購或交易資料。</p>')
    result.append('</section>')
    # 06. Sources & Evidence
    result.append('<section class="sources" id="sources">'+heading('06','Sources & Evidence','原始來源、資料時間、證據與限制')+'<ol>')
    seen=set()
    for x in items:
        for s in x['sources']:
            if s['source_id'] in seen:continue
            seen.add(s['source_id'])
            result.append(f'<li id="{source_anchor(s)}">{h(s.get("article_published_at") or "原始日期未核實")} '
                          f'· {h(s["publisher"])} · ID {h(s["source_id"])}<br/>{h(x["title_original"])}'
                          f'<p class="source-note">本書已收錄摘要與研究；<a href="{h(s["url"])}">'
                          '原始網站來源（需要網路）</a>僅供日後進一步核實。</p></li>')
        for claim in x.get('evidence',[]):
            result.append(f'<li><b>主張 {h(claim.get("claim_id"))}</b> · {h(claim.get("verification"))}'
                          f' · {h(claim.get("source_location"))}<br/>{h(claim.get("text"))}')
            # Include a *bounded* relevant official evidence window for offline
            # inspection, never the publisher article or entire official report.
            context=str(claim.get('official_context_excerpt') or '').strip()
            if context:
                result.append('<div class="evidence">'
                    '<strong>已收錄的官方文件定位片段（不等於事實核准）</strong>'
                    +'<p>'+h(context[:260])+'</p>'
                    +'<p class="source-note">文件讀取：'+h(claim.get('retrieved_at'))
                    +' · SHA-256：'+h(str(claim.get('source_sha256') or '')[:14])
                    +'</p></div>')
            result.append('</li>')
    supplemental=issue.get('research_source_manifest') or []
    if supplemental:
        result.append('</ol><h3>深讀研究補充原始資料（尚待人工簽核）</h3><ol>')
        for row in supplemental[:20]:
            url=str(row.get('source') or '')
            if not url.startswith('https://') or len(url)>500:
                continue
            result.append('<li>'+h(row.get('kind') or '研究補充資料')+
                ' · <a href="'+h(url)+'">官方資料原址（離線閱讀不需開啟）</a></li>')
    result.append('</ol><p class="method">來源文章、新聞索引、Gemini 編輯解釋分開標示。來源網址存在不代表所有主張已被核實。'
        +' 只摘要與引用連結，不重製有版權的新聞全文。</p></section>')
    text='\n'.join(result)
    # Pandoc's HTML reader can discard id attributes on HTML5 <nav>/<article>
    # even while EPUBCheck succeeds. Native <div id> preserves EPUB fragments.
    # Convert only structural wrappers; never change the frozen six headings.
    text=re.sub(r'<article\b','<div',text).replace('</div>','</div>')
    text=re.sub(r'<nav\b','<div',text).replace('</div>','</div>')
    # Protect the frozen editorial contract in the output as well.
    for name in (x['name'] for x in contract['sections']):
        if text.count('｜'+h(name)) != 1:raise RuntimeError('Frozen section structure violated: '+name)
    return text

def as_xhtml(issue,edits=None,level='essential',css_file=None):
    title=f'Global Intelligence Brief {issue["report_date"]} {issue["edition"]} {level}'
    css=f'<link rel="stylesheet" href="{h(css_file)}"/>' if css_file else ''
    return f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" lang="zh-Hant"><head><meta charset="utf-8"/><title>{h(title)}</title>{css}</head><body>{issue_body(issue,edits,level)}</body></html>'

def export(issue,edits=None,out=None,qa_only=True):
    if not qa_only:raise PermissionError('Publishing remains locked pending 10 real trading days, EPUBCheck, BOOX device approval and owner release authorization')
    folder=Path(out or ROOT/'qa_outputs'/issue['issue_id']);folder.mkdir(parents=True,exist_ok=True)
    if not shutil.which('pandoc'):raise RuntimeError('Pandoc required')
    results={}
    for level in ('essential','deep'):
        stem=f'{issue["edition"]}-{level}'
        xhtml=folder/(stem+'.xhtml');xhtml.write_text(as_xhtml(issue,edits,level),encoding='utf-8')
        epub=folder/(stem+'.epub')
        with tempfile.TemporaryDirectory() as tmp:
            cover=Path(tmp)/'cover.png';make_cover(cover,issue['edition'],level,issue['report_date'])
            args=['pandoc',str(xhtml),'-f','html','-t','epub3','--standalone','--toc','--toc-depth=2',
                '--css',str(CSS),'--epub-cover-image',str(cover),'--metadata=lang:zh-TW',
                '--metadata=title:Global Intelligence Brief '+issue['report_date']+' '+stem,
                '--metadata=author:Global Intelligence Brief','-o',str(epub)]
            subprocess.run(args,capture_output=True,text=True,check=True,timeout=100)
        validate_epub(epub)
        with ZipFile(epub) as z:
            if not any(n.endswith('.xhtml') for n in z.namelist()):raise ValueError('EPUB missing XHTML')
        results[level]={'xhtml':str(xhtml),'epub':str(epub),'bytes':epub.stat().st_size}
    # Deep edition already embeds the short brief and all in-book reading.
    # A stable descriptive alias communicates the one-download offline use case,
    # without duplicating the EPUB or downloading external publisher articles.
    results['offline_complete']={**results['deep'],'description':'整本離線合輯：速讀→解析→研究→來源'}
    return results
