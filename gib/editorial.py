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
    for a in items:
        t=a['title'].lower()
        important=sum(t.count(x) for x in ('rate','policy','decision','inflation','unexpected','sanction','shutdown','trade','supply','fomc'))
        a['score']=((weights.get(a['section'],5)/5)+min(important,3)*2
            +(4 if a['official'] else 0)+min(2,len(a['publishers'])-1)*1.5)
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
