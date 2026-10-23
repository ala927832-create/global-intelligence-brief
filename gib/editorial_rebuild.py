"""Publication-grade evidence-bound editorial pipeline.

Produces two content levels from one verified evidence packet. Structured XHTML
is the common representation for HTML and EPUB; never treat wordcount/ZIP validity
as an editorial quality guarantee.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from .epub import make_cover, validate_epub

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / 'assets' / 'editorial' / 'layout01-magazine.css'


def esc(t):
    return html.escape(str(t or ''), quote=True)


def safe_url(u):
    p = urlsplit(str(u or ''))
    return str(u) if p.scheme == 'https' and p.netloc else ''


def validate_packet(pkt):
    if pkt.get('kind') != 'evidence_bound_editorial':
        raise ValueError('Expected validated evidence-bound packet')
    if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}', str(pkt.get('date', ''))):
        raise ValueError('Invalid report date')
    ids = set()
    for s in pkt.get('sources', []):
        if s.get('id') in ids or not safe_url(s.get('url')) or not s.get('publisher') or not s.get('published'):
            raise ValueError('Source id/URL/publisher/date invalid')
        ids.add(s['id'])
    if len(ids) < 3: raise ValueError('Evidence packet needs multiple credible sources')
    for story in pkt.get('stories', []):
        if not story.get('title') or not story.get('source_ids'):
            raise ValueError('Story lacks source attribution')
        if not set(story['source_ids']).issubset(ids):
            raise ValueError('Story references unknown source')
        if not story.get('verified_facts'):
            raise ValueError('Story has no evidence')
    for chapter in pkt.get('chapters', []):
        if not set(chapter.get('source_ids', [])).issubset(ids):
            raise ValueError('Deep chapter has invalid sources')
    if not pkt.get('editorial_status') == 'CURATED_REVIEW_SAMPLE':
        raise ValueError('Sample requires explicit non-live editorial label')
    return True


def li(items, cls=''):
    if not items: return ''
    return f'<ol class="{cls}">' + ''.join(f'<li>{esc(x)}</li>' for x in items) + '</ol>'


def sources_for(ids, index):
    links=[]
    for sid in ids:
        x = index[sid]
        links.append(f'<a href="{esc(x["url"])}">{esc(x["publisher"])}／{esc(x["published"])}</a>')
    return '<p class="evidence-meta"><strong>資料來源：</strong> ' + '　·　'.join(links) + '</p>'


def figure_markup(root: Path, name: str, title: str, caption: str, epub=False):
    path=root/'assets'/'editorial'/name
    if not path.is_file(): return ''
    uri = ('../../assets/editorial/'+name) if not epub else path.resolve().as_uri()
    return f'<figure class="evidence-figure"><img src="{esc(uri)}" alt="{esc(title)}"/><figcaption>{esc(caption)}</figcaption></figure>'


def build_body(pkt, edition='morning', level='essential', root=ROOT, epub=False):
    """Structured HTML body; evidence fact list is the shared source of truth."""
    validate_packet(pkt)
    isdeep=level=='deep'
    period='晨報' if edition=='morning' else '晚報'
    t='深入研究' if isdeep else '每日精選'
    src = {x['id']:x for x in pkt['sources']}
    teaser = pkt.get('lead', '')
    label=f'{period} · {t}'
    parts=[f'''<section class="issue-opening" id="opening">
      <div class="meta-row"><span>GLOBAL INTELLIGENCE BRIEF · RESEARCH EDITION</span><span>{esc(pkt['date'])} / ASIA·TAIPEI</span></div>
      <div class="brand-heading"><div class="globe">◎</div><div><p class="brand-name">Global<br/>Intelligence Brief</p><p class="brand-zh">全球情報簡報 · {esc(label)}</p></div></div>
      <p class="tagline">EVIDENCE · CONTEXT · UNDERSTANDING</p>
      <div class="topic-strip"><div><b>01</b> 全球政經</div><div><b>02</b> 央行金融</div><div><b>03</b> 產業科技</div><div><b>04</b> 風險追蹤</div></div>
      <div class="lede"><span class="eyebrow">EDITOR'S BRIEF · 編輯導讀</span><h1>{esc(pkt['headline'])}</h1>
      <p class="deck">{esc(teaser)}</p></div>
      <div class="keybox"><h2>三項核心觀察 <small>KEY INSIGHTS</small></h2>{li(pkt['key_insights'],'insight-list')}</div>
      <p class="disclaimer"><strong>刊物狀態：</strong>官方資料研究示範；不是當日自動新聞擷取的正式 07:30／17:30 刊物。數據依所列資料發布日呈現，分析與預測分開標示。</p>
    </section>''']
    parts.append('<section id="lead-news" class="chapter"><div class="chapter-tag">01 / ESSENTIAL STORIES</div><h2>今日重要事件｜發生了什麼、為什麼重要</h2>')
    max_stories = len(pkt['stories']) if isdeep else min(4,len(pkt['stories']))
    for i, story in enumerate(pkt['stories'][:max_stories],1):
        parts.append(f'<article class="story"><p class="eyebrow">STORY {i:02d} · {esc(story["category"])} · {esc(story["published"])}</p><h3>{esc(story["title"])}</h3>')
        parts.append(f'<p class="summaryline">{esc(story["summary"])}</p>')
        parts.append('<div class="evidence-slab"><h4>已確認事實 <small>VERIFIED FACTS</small></h4><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in story['verified_facts'])+'</ul></div>')
        parts.append(f'<p><strong>為何重要｜</strong>{esc(story["why"])}</p>')
        if isdeep:
            for p in story.get('explain',[]): parts.append('<p>'+esc(p)+'</p>')
        parts.append('<div class="watchbox"><h4>接下來觀察 <small>WHAT TO WATCH</small></h4>'+li(story['watch'])+'</div>')
        parts.append(sources_for(story['source_ids'],src)+'</article>')
    parts.append('</section>')
    if isdeep:
        parts.append('<section id="deep-research" class="chapter"><div class="chapter-tag">02 / DEEP RESEARCH</div><h2>深度研究｜從事件到機制</h2>')
        for ci, chapter in enumerate(pkt['chapters'],1):
            parts.append(f'<article class="research"><p class="eyebrow">RESEARCH PAPER {ci:02d}</p><h3>{esc(chapter["title"])}</h3><p class="summaryline">{esc(chapter["question"])}</p>')
            for si, sec in enumerate(chapter.get('sections',[]),1):
                parts.append(f'<section class="research-section"><h4>{ci}.{si}　{esc(sec["heading"])}</h4>')
                for para in sec.get('paragraphs',[]): parts.append('<p>'+esc(para)+'</p>')
                if sec.get('bullets'): parts.append('<ul>'+''.join(f'<li>{esc(v)}</li>' for v in sec['bullets'])+'</ul>')
                if sec.get('figure'): parts.append(figure_markup(root,sec['figure']['file'],sec['figure']['title'],sec['figure']['caption'],epub))
                parts.append('</section>')
            parts.append('<div class="keybox"><h4>研究結論 <small>RESEARCH TAKEAWAYS</small></h4>'+li(chapter.get('conclusions',[]))+'</div>')
            parts.append('<div class="watchbox"><h4>推翻與追蹤條件 <small>WHAT WOULD CHANGE OUR VIEW</small></h4>'+li(chapter.get('falsifiers',[]))+'</div>')
            parts.append(sources_for(chapter['source_ids'],src)+'</article>')
        parts.append('</section>')
    parts.append('<section id="looking-ahead" class="chapter"><div class="chapter-tag">03 / LOOKING AHEAD</div><h2>接下來一週｜事件日程與觀察</h2>')
    for e in pkt.get('calendar',[]):
        url=safe_url(e.get('url'))
        parts.append(f'<div class="calendar-event"><div class="calendar-date">{esc(e["date"])}</div><div><b>{esc(e["name"])}</b><p>{esc(e["watch"])}</p>'+ (f'<a href="{esc(url)}">官方日程與公告</a>' if url else '') +'</div></div>')
    parts.append('</section>')
    if pkt.get('zinc_watch'):
        parts.append('<section class="chapter" id="zinc-watch"><h2>Zinc Research Watch｜唯讀市場研究線索</h2>')
        parts.append('<p>此專欄僅呈現公開、已驗證且有跨市場價值的研究觀察；未取得有效訊號時不強制填充。交易訊號不等於新聞事實。</p>')
        for x in pkt['zinc_watch']: parts.append(f'<p class="research-signal">{esc(x)}</p>')
        parts.append('</section>')
    parts.append('<section id="sources" class="chapter"><div class="chapter-tag">04 / NOTES & SOURCES</div><h2>參考資料、日期及研究限制</h2><ol class="source-list">')
    for s in pkt['sources']:
        parts.append(f'<li id="source-{esc(s["id"])}"><b>{esc(s["publisher"])}（{esc(s["published"]) }）</b>：{esc(s["title"])} <a href="{esc(s["url"])}">原始資料</a></li>')
    parts.append('</ol><p class="method">'+esc(pkt.get('methodology',''))+'</p><p class="method">正文分析屬條件推論；未取得即時行情、調查資料或原始研究支持的事項，均未宣稱為已發生事實。本期圖片中的數據依對應來源人工整理，未使用示意或合成價格。</p></section>')
    return '\n'.join(parts)


def make_html(pkt, edition, level, root=ROOT, epub=False):
    title=f'Global Intelligence Brief｜{pkt["date"]}｜{"晨" if edition=="morning" else "晚"}報｜{level}'
    body=build_body(pkt,edition,level,root,epub)
    css = '' if epub else '<link rel="stylesheet" href="../../assets/editorial/layout01-magazine.css"/>'
    return (f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" lang="zh-Hant"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{esc(title)}</title>{css}</head><body>{body}</body></html>')


def count_cjk(text):
    return len(re.findall(r'[\u3400-\u9fff]', re.sub(r'<[^>]+>', '', text)))


def export_packet(pkt, root=ROOT, edition='morning', validate_deep_min=0):
    validate_packet(pkt)
    datedir=root/'reports'/pkt['date'];datedir.mkdir(parents=True, exist_ok=True)
    site=root/'docs'/'archive'/pkt['date'];site.mkdir(parents=True, exist_ok=True)
    public_assets=root/'docs'/'assets'/'editorial'
    public_assets.mkdir(parents=True, exist_ok=True)
    for asset in (root/'assets'/'editorial').glob('*'):
        if asset.suffix in ('.css','.png'): shutil.copyfile(asset,public_assets/asset.name)
    result={}
    for level in ('essential','deep'):
        name=f'{edition}-{level}'
        htmltext=make_html(pkt,edition,level,root,epub=False)
        cjk=count_cjk(htmltext)
        if level=='deep' and cjk<validate_deep_min:
            raise ValueError(f'Deep issue insufficient content ({cjk} CJK chars); not published')
        path=site/f'{name}.html';path.write_text(htmltext,encoding='utf-8')
        ebook_html=datedir/f'{name}.epub-source.html'
        ebook_html.write_text(make_html(pkt,edition,level,root,epub=True),encoding='utf-8')
        book=datedir/f'{name}.epub'
        with tempfile.TemporaryDirectory() as temp:
            cover=Path(temp)/'cover.png';make_cover(cover,edition,level,pkt['date'])
            cmd=['pandoc',str(ebook_html),'-f','html','-t','epub3','--standalone','--toc', '--toc-depth=3',
                 '--css',str(CSS),'--epub-cover-image',str(cover),
                 '--metadata=lang:zh-TW',f'--metadata=title:{pkt["date"]} 全球情報簡報 {edition} {level}',
                 '--metadata=author:Global Intelligence Brief','-o',str(book)]
            subprocess.run(cmd,check=True,timeout=120,capture_output=True,text=True)
            validate_epub(book)
        public=site/f'{name}.epub';shutil.copyfile(book,public)
        result[name]={'html':str(path),'epub':str(book),'cjk_chars':cjk,'bytes':book.stat().st_size}
    (datedir/'issue-evidence.json').write_text(json.dumps(pkt,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
