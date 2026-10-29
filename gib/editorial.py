"""Transparent, deterministic editorial ranking and update detection."""
import datetime as dt
import difflib
import hashlib
import re
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

KEYWORDS={
'macro':['gdp','inflation','recession','economic growth','unemployment','jobs','cpi','pmi'],
'central_banks':['federal reserve','interest rate','treasury','yield','bond','central bank','boj','ecb','fed'],
'geopolitics':['war','conflict','sanction','tariff','embargo','military','geopolitic'],
'asia':['china','taiwan','japan','korea','asia','yen','yuan'],
'technology':['ai ','artificial intelligence','chip','semiconductor','tsmc','nvidia'],
'energy':['oil','gas','energy','power','grid','electricity','metals','steel','zinc'],
'corporates':['earnings','merger','acquisition','bankruptcy','default'],
'unexpected':['climate','earthquake','shipping','port','pandemic','cyberattack']
}

def normalized_title(title):
    return ' '.join(re.findall(r'[\w\u4e00-\u9fff]+',title.lower()))

def canon_url(url):
    try:
        x=urlsplit(url)
        if x.scheme not in ('https','http') or not x.netloc: return ''
        clean=[(k,v) for k,v in parse_qsl(x.query) if not (k.startswith('utm_') or k in ('fbclid','gclid'))]
        return urlunsplit((x.scheme,x.netloc.lower(),x.path.rstrip('/'),urlencode(clean),'')).lower()
    except ValueError: return ''

def classify(title):
    t=title.lower()
    hits={k:sum(1 for kw in words if kw in t) for k,words in KEYWORDS.items()}
    return max(hits,key=hits.get) if max(hits.values())>0 else 'unexpected'


MATERIAL_TOPIC=re.compile(
    r"\b(?:federal reserve|central bank|inflation|cpi|gdp|recession|"
    r"econom(?:y|ic|ics)|trade|tariff|sanction|interest rates?|"
    r"treasury|bond|yield|unemployment|jobs|employment|wages?|"
    r"manufactur\w*|industr\w*|semiconductor|microchip|chipmaker|"
    r"energy|refiner\w*|petroleum|oil|diesel|natural gas|"
    r"supply chain|logistics|shipping|port congestion|"
    r"electricity|power grid|currency|yen|dollar|bank|"
    r"financial|fiscal|budget|earnings|merger|acquisition|"
    r"technology|artificial intelligence|\bai\b|"
    r"geopolitic\w*|military conflict|war on|"
    r"climate|earthquake|pandemic|wildfire|global health|"
    r"election|presidential|president|prime minister|parliament|"
    r"government|cabinet|legislature|congress|senate|supreme court|"
    r"diplomac\w*|ceasefire|peace talks|refugee\w*|humanitarian|"
    r"united nations|security council|world health organization|"
    r"protest\w*|migration|immigration|human rights|"
    r"hurricane|typhoon|cyclone|flood\w*|drought|"
    r"disease outbreak|public health|vaccine|"
    r"space mission|satellite|cyberattack|cyber attack|"
    r"export|import|output|production|growth|freight)\b",
    flags=re.I)
# World news can be published in Chinese; it is not restricted to English
# economic/industrial terminology or the user's manufacturing interests.
GLOBAL_CJK_MATERIAL=(
    "選舉","總統","國會","內閣","政府政策","外交","國際協議","停火",
    "戰爭","人道危機","難民","通膨","央行","貨幣政策","經濟成長",
    "金融市場","人工智慧","半導體","能源安全","氣候變遷",
    "公共衛生","重大疫情","地震","颱風","國際制裁","聯合國"
)

SPORTS_LEISURE=re.compile(
    r"\b(?:football|basketball|soccer|nfl|nba|nhl|"
    r"mlb|motogp|formula one|f1 race|grand prix|"
    r"home opener|umpire|touchdown|quarterback|"
    r"trophy|receivers? after week|championship hopes|"
    r"penalised|penalized|australian open|"
    r"warriors fans|premier league|tennis match|"
    r"rugby|goalscorer|athlete|world cup qualifiers?)\b",
    flags=re.I)

def material_news_candidate(a):
    """Require a recognizable global-affairs/economic hook; exclude obvious sports.
    This is a precision triage rule, not an assessment of news truth or viewpoint.
    An official release is eligible if it avoids unambiguously non-news sports terms.
    """
    title=str(a.get('title',''))
    if SPORTS_LEISURE.search(title):return False
    return bool(a.get('official') or MATERIAL_TOPIC.search(title)
                or any(term in title for term in GLOBAL_CJK_MATERIAL))

def same_repeated_story_title(left,right):
    """Merge strong syndication variants without equating all oil/geopolitics news."""
    a=normalized_title(left).split()
    b=normalized_title(right).split()
    if not a or not b:return False
    if difflib.SequenceMatcher(None,' '.join(a),' '.join(b)).ratio()>=.85 and min(len(a),len(b))>=5:
        return True
    # Identical 8-word reporting lead is strong evidence of a rewritten
    # headline. This is deliberately conservative for distinct policy events.
    if min(len(a),len(b))>=10 and a[:8]==b[:8]:
        return len(set(a)&set(b))/max(1,len(set(a)|set(b)))>=.48
    return False

def cluster(articles,now,cutoff_hours=48):
    out=[]
    for a in articles:
        title=(a.get('title') or '').strip()
        url=canon_url(a.get('url') or '')
        if not title or not url: continue
        pub=a.get('published_at')
        if pub:
            try:
                d=dt.datetime.fromisoformat(pub.replace('Z','+00:00'))
                if d.tzinfo is None: d=d.replace(tzinfo=dt.timezone.utc)
                if d>now+dt.timedelta(hours=3) or d<now-dt.timedelta(hours=cutoff_hours): continue
            except ValueError: pub=None
        norm=normalized_title(title)
        similar=next((b for b in out if canon_url(b['url'])==url or
                  (same_repeated_story_title(title,b['title']) and len(norm)>=18)),None)
        if similar:
            k=(a.get('publisher') or a.get('provider') or '')
            if k and k not in similar['publishers']: similar['publishers'].append(k)
            if url not in similar['related_urls']: similar['related_urls'].append(url)
            if a.get('official'):
                similar['official']=True
                if not similar.get('published_at') and pub: similar['published_at']=pub
            continue
        b={**a,'url':url,'published_at':pub,'section':classify(title),
           'publishers':[a.get('publisher') or a.get('provider') or 'unknown'],
           'related_urls':[url], 'official':bool(a.get('official'))}
        out.append(b)
    return out

def rank(items,weights):
    """Transparent newsworthiness heuristic; never treat title ranking as fact check.

    Global policy / material cross-border impact and independently attributable
    official releases outrank incidental spot prices and opinion-only pieces.
    Keep transparency in the issue evidence rather than silently deleting
    disfavoured outlets or viewpoints.
    """
    for a in items:
        t=a['title'].lower()
        important=sum(t.count(x) for x in
            ('rate','policy','decision','inflation','unexpected','sanction',
             'shutdown','trade','supply','fomc'))
        global_signals=sum(bool(x in t) for x in
            ('federal reserve','central bank','imf','world bank','g7','g20',
             'global','international','tariff','national election',
             'central government','major outage','supply chain'))
        narrow_signals=sum(bool(re.search(x,t)) for x in
            (r'\b(?:today|daily) gold (?:price|rate)',r'\blocal gold price',
             r'\bhoroscope',r'\bstock pick'))
        speculative=sum(bool(x in t) for x in
            ('opinion:', 'op-ed', 'commentary:', 'rumor:', 'unconfirmed:',
             'price prediction'))
        a['editorial_rank_signals']={
            'global_relevance':global_signals,
            'narrow_listing':narrow_signals,
            'commentary_or_speculation':speculative,
            'official_source':bool(a.get('official')),
        }
        a['score']=round((weights.get(a['section'],5)/5)
            +min(important,3)*2
            +(4 if a.get('official') else 0)
            +min(2,len(a['publishers'])-1)*1.5
            +min(global_signals,3)*2.5
            -narrow_signals*5
            -speculative*3,2)
    return sorted(items,key=lambda a:(-a['score'],a.get('published_at') or ''))

def sig(title):
    return hashlib.sha256(normalized_title(title).encode()).hexdigest()[:16]

def label_updates(items,seen,edition,now):
    """An official *new* URL may update an event; syndication alone never does."""
    seen=seen or []
    for a in items:
        matches=[e for e in seen if e.get('key')==sig(a['title']) or
                 difflib.SequenceMatcher(None,normalized_title(e.get('title','')),normalized_title(a['title'])).ratio()>=.85]
        a['status']='NEW' if not matches else 'REPORTED'
        if matches:
            old=max(matches,key=lambda e:e.get('last_seen',''))
            old_urls=set(old.get('urls',[]))
            # Consider distinct, newly published *official* notices only.
            if a.get('official') and a.get('url') not in old_urls and a.get('published_at'):
                try:
                    d=dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00'))
                    last=dt.datetime.fromisoformat(old['last_seen'])
                    if d>last: a['status']='NEW_OFFICIAL_NOTICE'
                except (ValueError,KeyError,TypeError): pass
            elif len(a.get('publishers',[]))>int(old.get('source_count',1)):
                a['status']='MORE_SOURCES' # not necessarily a material update
    if edition=='evening':
        return [x for x in items if x['status'] in ('NEW','NEW_OFFICIAL_NOTICE')]
    return items

def diversified(items,top_n=12,max_per_section=4):
    out=[];counts={}
    for a in items:
        section=a.get('section','unexpected')
        if counts.get(section,0)>=max_per_section: continue
        out.append(a);counts[section]=counts.get(section,0)+1
        if len(out)>=top_n: break
    return out


def diversified_v3(items, top_n=24, max_per_section=8):
    """Evidence-neutral source-index coverage selection for V3 R1.

    Keep the highest-ranking items while reserving enough slots for distinct
    reporting themes and publisher domains when qualifying candidates exist.
    This does NOT certify an outlet's headline position, truth or article text.
    """
    by_section={}
    by_domain={}
    for item in items:
        by_section.setdefault(item.get("section","unexpected"),item)
        domain=urlsplit(item.get("url","")).hostname
        if domain: by_domain.setdefault(domain,item)
    reserved=[]
    def add(item):
        key=canon_url(item.get("url",""))
        if key and all(canon_url(x.get("url",""))!=key for x in reserved):
            reserved.append(item)
    for item in list(by_section.values())[:4]:
        add(item)
    for item in list(by_domain.values())[:4]:
        add(item)
    counts={}
    for item in reserved:
        section=item.get("section","unexpected")
        counts[section]=counts.get(section,0)+1
    for item in items:
        if len(reserved)>=top_n: break
        section=item.get("section","unexpected")
        if counts.get(section,0)>=max_per_section: continue
        old=len(reserved);add(item)
        if len(reserved)>old: counts[section]=counts.get(section,0)+1
    # Restore ranked order so low-scoring coverage representatives do not
    # automatically become top headlines; editorial signoff remains separate.
    by_url={canon_url(x.get("url","")):i for i,x in enumerate(items)}
    return sorted(reserved,key=lambda a:by_url.get(canon_url(a.get("url","")),10**9))[:top_n]

def next_seen(old,items,now,limit=500):
    existing={x['key']:x for x in old if x.get('key')}
    for x in items:
        k=sig(x['title']); existing[k]={'key':k,'title':x['title'],
              'last_seen':now.isoformat(),'source_count':len(x['publishers']),
              'urls':list(x.get('related_urls',[]))[:8]}
    recent=now-dt.timedelta(days=21)
    live=[]
    for item in existing.values():
        try:
            if dt.datetime.fromisoformat(item['last_seen'])>=recent: live.append(item)
        except (KeyError,ValueError): pass
    return sorted(live,key=lambda x:x['last_seen'],reverse=True)[:limit]
