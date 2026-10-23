"""One evidence packet -> two editions. Never fabricate explanatory facts."""
import datetime as dt
import html
import json
import os
import shutil
import subprocess
from .epub import render_epub
from pathlib import Path
from urllib.parse import urlsplit
import mistune
import bleach
from .editorial import sig

LABELS={'macro':'全球經濟','central_banks':'央行與金融','geopolitics':'國際政策與風險',
        'asia':'亞洲經濟','technology':'科技與半導體','energy':'能源與產業',
        'corporates':'全球企業','unexpected':'其他重要資訊'}
ALLOWED_TAGS=set(bleach.sanitizer.ALLOWED_TAGS)|{'p','h1','h2','h3','h4','table','thead','tbody','tr','td','th','pre','hr','div'}

def esc(x): return html.escape(str(x or ''),quote=True)
def valid_link(x):
    try:
        p=urlsplit(x)
        return x if p.scheme in ('http','https') and p.netloc else ''
    except (ValueError,TypeError): return ''

def news_block(a,i,ai,deep):
    title=esc(a['title']);url=valid_link(a['url']);date=esc(a.get('published_at') or '日期未核實')
    label=LABELS.get(a.get('section'),'全球新聞')
    mark='官方來源' if a.get('official') else '媒體報導，需核對原文'
    parts=[f'### {i}. {title}',f'**領域：** {label}｜**發布：** {date}｜**證據類型：** {mark}',
           f'**新聞出處：** [{esc(a.get("publisher"))}]({url})' if url else '**新聞出處：** 無有效來源連結']
    if len(a.get('related_urls',[]))>1:
        parts.append('**其他報導：** '+', '.join(f'[來源 {j+1}]({u})' for j,u in enumerate(a['related_urls'][:3]) if valid_link(u)))
    note=next((x for x in ai.get('items',[]) if x.get('event_id')==sig(a['title'])),None)
    if note:
        parts.append('**為何值得了解（AI 解讀，須核對）：** '+esc(note.get('why')))
        parts.append('**接下來觀察：** '+esc(note.get('watch')))
        if deep:
            parts.append('**可能的經濟傳導：** '+esc(note.get('context')))
            parts.append('**不確定性：** '+esc(note.get('uncertainty')))
    else:
        summary=' '.join(bleach.clean(str(a.get('snippet') or ''),tags=[],attributes={},strip=True).split()[:20])
        parts.append('**來源摘要：** '+esc(summary or '目前僅有標題／來源資訊，尚不足以確認事件細節或因果。'))
        parts.append('**下一步：** 查閱來源原文並核對事件是否有更新；不依標題推測市場影響。')
        if deep: parts.append('**深讀資料限制：** 未取得足夠獨立證據，暫不生成未經核實的背景與情境分析。')
    return '\n\n'.join(parts)

def build_markdown(edition,level,items,ai,bridge,now,errors,compare_ready=True):
    day=now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d')
    scope='晨報' if edition=='morning' else '晚報'
    typ='10–15 分鐘速讀' if level=='essential' else '30–45 分鐘深讀（以證據充足程度為準）'
    lines=[f'# Global Intelligence Brief｜{scope}',f'**{day} · 台灣時間 · {typ}**',
           '> 全球財經新聞研究。標註發布日期與原始來源；不提供交易指令。',
           '## 今日三個核心問題',
           '1. 全球發生了哪些值得知道的重要事情？',
           '2. 這些事情為什麼重要、有哪些已確認的影響？',
           '3. 下一步需要關注哪些數據、政策與未確認變化？']
    if edition=='evening':
        lines.append('> 晚報主要收錄相對當日晨報新增的候選事件；已報導且無新證據的內容不重複刊登。')
        if not compare_ready:
            lines.append('> **注意：** 本日晨報紀錄缺失，無法保證增量比較完整。')
    lines.append('## Essential News｜今日優先閱讀')
    if not items:
        lines.append('本期未取得足夠的**新且有原始來源**的新聞；不為填充篇幅而重複舊聞。請檢查資料來源健康狀態。')
    for i,a in enumerate(items[:(12 if level=='deep' else 8)],1):lines.append(news_block(a,i,ai,level=='deep'))
    if level=='deep':
        lines.append('## Deep Dive｜深度研究')
        lines.append(esc(ai.get('deep_dive')) if ai.get('deep_dive') else '本期尚未取得足夠可核對的第一手資料以撰寫 30–45 分鐘深度研究。提供已查得的新聞證據，避免用推測補足篇幅。')
        lines.append('## 不同觀點與尚待驗證')
        lines.append(esc(ai.get('alternative_views')) if ai.get('alternative_views') else '目前缺少足夠的獨立研究或原始數據，不把多家媒體轉載視為多重證實。')
    lines.append('## Zinc Research Watch｜跨系統市場觀察')
    if bridge.get('status')=='VALID':
        lines.append(f'來源：Zinc Intelligence 唯讀研究快照，更新時間 `{esc(bridge.get("zinc_run_time"))}`；研究觀察不是當日財經新聞。')
        # Hard limit on number of market watch rows. No trading triggers or prices.
        watch=[w for w in bridge.get('watch',[]) if w.get('direction') not in ('NEUTRAL',)]
        if watch:
            for w in watch[:2]:
                lines.append(f'- **{esc(w["asset"])}**：研究方向 `{esc(w["direction"])}`；市場資料日 `{esc(w.get("market_date") or "未提供")}`。只作新聞查證線索，不代表有新事件或下單條件。')
        else: lines.append('目前沒有符合條件的額外市場研究焦點。')
        if bridge.get('events'):
            lines.append('**尚未公布的官方事件日程（需再核對）：**')
            for event in bridge['events'][:2]:
                u=valid_link(event.get('source_url',''))
                lines.append(f'- {esc(event["date"])}：{esc(event["title"])}（已排程、非已公布結果）'+(f' [來源]({u})' if u else ''))
    else:
        lines.append(f'本期未引用 Zinc 研究資料（來源狀態：{esc(bridge.get("status"))}）。')
    lines.append('## 接下來值得觀察')
    lines.append('關注報導後是否出現官方公告、不同可信來源及相關後續資料。沒有證據不得宣稱事件已導致特定市場變動。')
    lines.append('## 資料完整度與使用限制')
    lines.append(f'- 本期來源事件數：{len(items)}；AI 研究：{"已啟用，仍需驗證" if ai.get("items") else "未啟用或不可用，採取保守摘要"}。')
    if errors: lines.append('- 部分來源讀取失敗：'+esc('; '.join(errors[:7])[:800]))
    lines.append('- 文章標題和摘要是來源對事件的描述，不能取代原始公告與證據。')
    lines.append('- 深讀版只有在資料足夠時才可能達到預定閱讀長度，未驗證資料一律不補寫。')
    return '\n\n'.join(lines)+'\n'

def write_outputs(root,edition,items,ai,bridge,now,errors,compare_ready):
    taipei=now.astimezone(dt.timezone(dt.timedelta(hours=8)))
    date=taipei.strftime('%Y-%m-%d')
    rep=root/'reports'/date; site=root/'docs'/'archive'/date
    rep.mkdir(parents=True,exist_ok=True);site.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for level in ('essential','deep'):
        md=build_markdown(edition,level,items,ai,bridge,now,errors,compare_ready)
        name=f'{edition}-{level}'
        mdpath=rep/f'{name}.md'; mdpath.write_text(md,encoding='utf-8')
        body=mistune.create_markdown(escape=True, plugins=["table"])(md)
        safe=bleach.clean(body,tags=ALLOWED_TAGS,attributes={'a':['href','title'],'td':['align'],'th':['align']},protocols=['http','https','mailto'],strip=True)
        epubpath=rep/f'{name}.epub'
        public_epub=site/f'{name}.epub'
        epub_ready=False
        if shutil.which('pandoc'):
            try:
                render_epub(mdpath, epubpath, edition, level, date)
                # Reports contain only public news and the allowlisted Zinc bridge.
                # Publish EPUB beside HTML for direct BOOX device downloads.
                shutil.copyfile(epubpath, public_epub)
                epub_ready=True
            except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                errors.append('BOOX EPUB failed: '+type(exc).__name__)
        else:
            errors.append('BOOX EPUB unavailable: Pandoc missing')
        ebook_link=f'<a href="{name}.epub" download>BOOX 彩色 EPUB</a>' if epub_ready else '<span>EPUB 尚未生成</span>'
        label = '晨報' if edition=='morning' else '晚報'
        subtitle = 'ESSENTIAL BRIEF｜10–15 分鐘速讀' if level=='essential' else 'DEEP RESEARCH｜30–45 分鐘目標'
        brand = f'''<header class="brand"><div><div class="brand-title">◉ Global Intelligence Brief</div>
        <div class="brand-sub">全球情報簡報 · {label} · {subtitle}</div></div>
        <div class="brand-sub">{date}｜ASIA / TAIPEI</div></header>'''
        tiles = '''<div class="category-strip" aria-label="主要研究領域"><span>01 全球政經</span>
        <span>02 市場經濟</span><span>03 科技與產業</span><span>04 社會及重大風險</span></div>'''
        page=(f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
              f'<meta name="viewport" content="width=device-width,initial-scale=1">'
              f'<title>Global Intelligence Brief｜{date}｜{name}</title>'
              f'<link rel="stylesheet" href="../../assets/layout-01.css"></head><body>'
              f'{brand}{tiles}<nav class="issue-nav"><a href="../../index.html">首頁</a>'
              f'<a href="{edition}-{"deep" if level=="essential" else "essential"}.html">切換閱讀深度</a>'
              f'{ebook_link}</nav><main>{safe}</main></body></html>')
        htmlpath=site/f'{name}.html';htmlpath.write_text(page,encoding='utf-8')
        outputs.append(htmlpath)
        if epub_ready: outputs.append(public_epub)
    return outputs

def update_index(root):
    index=root/'docs'/'index.html'
    all_html=list((root/'docs'/'archive').rglob('*.html'))
    all_html.sort(reverse=True)
    def menu_item(p):
        title={
            'morning-essential':'晨報 · 10–15 分鐘速讀',
            'morning-deep':'晨報 · 30–45 分鐘深讀',
            'evening-essential':'晚報 · 10–15 分鐘速讀',
            'evening-deep':'晚報 · 30–45 分鐘深讀',
        }.get(p.stem, p.stem)
        web=esc(str(p.relative_to(root/'docs')))
        book=p.with_suffix('.epub')
        booklink=(f' · <a href="{esc(str(book.relative_to(root/"docs")))}" download>BOOX 彩色 EPUB</a>'
                  if book.is_file() else '')
        return f'<li><strong>{esc(p.parent.name)}｜{esc(title)}</strong> · <a href="{web}">HTML 閱讀</a>{booklink}</li>'
    menu='\n'.join(menu_item(p) for p in all_html[:100])
    index.write_text(f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Global Intelligence Brief</title><link rel="stylesheet" href="assets/layout-01.css"></head><body><header class="brand"><div><div class="brand-title">◉ Global Intelligence Brief</div><div class="brand-sub">全球情報簡報 · Layout 01 · BOOX Color EPUB</div></div><div class="brand-sub">07:30 MORNING / 17:30 EVENING</div></header><div class="category-strip"><span>01 全球政經</span><span>02 市場經濟</span><span>03 科技與產業</span><span>04 社會及重大風險</span></div><main><h1>全球財經晨報與晚報</h1><p>晨晚各提供速讀與深讀兩種版本。所有內容須保留來源、證據日期及不確定性。</p><ul>{menu}</ul></main></body></html>''',encoding='utf-8')
