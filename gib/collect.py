"""Free sources only. Network errors are visible, never filled with fabricated facts."""
import calendar
import datetime as dt
import os
import time
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = "GlobalIntelligenceBrief/1.0 (public-source research; non-commercial)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})

def timestamp(value):
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()
        if hasattr(value,"tm_year"):
            return dt.datetime.fromtimestamp(calendar.timegm(value),dt.timezone.utc).isoformat()
        text=str(value)
        if text.endswith('Z'): text=text[:-1]+'+00:00'
        try: d=dt.datetime.fromisoformat(text)
        except ValueError: d=parsedate_to_datetime(text)
        return d.replace(tzinfo=dt.timezone.utc).astimezone(dt.timezone.utc).isoformat() if d.tzinfo is None else d.astimezone(dt.timezone.utc).isoformat()
    except (ValueError,TypeError,OverflowError):
        return None

def get_json(url, params=None, headers=None, timeout=20):
    # One retry for transient provider errors; 429 waits at most 4 seconds.
    for attempt in range(2):
        try:
            r=SESSION.get(url,params=params,headers=headers,timeout=timeout)
            if r.status_code in (429,500,502,503,504) and attempt==0:
                try: delay=min(4,max(.6,float(r.headers.get('Retry-After','1'))))
                except ValueError: delay=1
                time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException,ValueError) as exc:
            if attempt: raise RuntimeError(f"{url.split('/')[2]}: {type(exc).__name__}: {exc}") from exc
            time.sleep(.6)
    return {}

def normalize(d, provider, origin=""):
    return {
        "title": str(d.get('title') or '').strip(),
        "url": str(d.get('url') or d.get('link') or '').strip(),
        "published_at": timestamp(d.get('published_at') or d.get('seendate') or d.get('pubDate') or d.get('published') or d.get('date')),
        "publisher": str(d.get('publisher') or d.get('domain') or origin or provider),
        "snippet": str(d.get('summary') or d.get('snippet') or d.get('description') or '')[:450],
        "provider": provider,
        "uuid": str(d.get('uuid') or ''),
        "official": provider=='official_rss'
    }

def freenews(config, now, errors, pause=.55):
    """Use lightweight /news discovery, then UUID details to recover publisher URL.

    Official API list examples do not guarantee a publisher URL; never silently
    discard all results as URL-less candidates. Avoid storing copyrighted body.
    """
    key=os.getenv('FREENEWS_API_KEY','').strip()
    if not key:
        errors.append('FreeNewsApi: KEY_NOT_CONFIGURED; continue with other free sources')
        return []
    cutoff=now-dt.timedelta(hours=48)
    # API has intermittently returned HTTP 500 for combined date/sort/search
    # filters. Prefer a broad supported query, then title searches, and apply
    # a strict UTC freshness filter locally. Never silently use stale articles.
    params_base={'language':'en'}
    searches=[{}]+[{'in_title':q} for q in config.get('freenews_titles',[])[:8]]
    seen={};detail_limit=int(config.get('freenews_details_daily_cap',32));detail_used=0
    for params in searches:
        try:
            data=get_json('https://api.freenewsapi.io/v1/news',params={**params_base,**params},headers={'x-api-key':key})
            if not isinstance(data,dict) or not isinstance(data.get('data'),list):
                errors.append('FreeNewsApi: unexpected /news shape');continue
            for item in data['data']:
                if not isinstance(item,dict):continue
                uuid=str(item.get('uuid') or '')
                label=uuid or str(item.get('url') or item.get('title') or '')
                if label and label not in seen:seen[label]=item
        except RuntimeError as ex:errors.append(str(ex)[:250])
        time.sleep(pause)
    if not seen:
        # Known-good, low-cost endpoint from provider's public quickstart.
        # Geographic fallback is labeled as such, not global coverage.
        try:
            data=get_json('https://api.freenewsapi.io/v1/news',
                params={'language':'en','country':'us'},headers={'x-api-key':key})
            if isinstance(data,dict) and isinstance(data.get('data'),list):
                errors.append('FreeNewsApi: US_FILTER_FALLBACK_USED; not global coverage')
                for item in data['data']:
                    if not isinstance(item,dict):continue
                    label=str(item.get('uuid') or item.get('url') or item.get('title') or '')
                    if label and label not in seen:seen[label]=item
        except RuntimeError as ex:
            errors.append('FreeNewsApi fallback: '+str(ex)[:160])
    output=[]
    for item in list(seen.values()):
        row=dict(item)
        if not (row.get('url') or row.get('original_url')) and row.get('uuid') and detail_used<detail_limit:
            try:
                detail_used+=1
                body=get_json('https://api.freenewsapi.io/v1/details',
                         params={'uuid':row['uuid']},headers={'x-api-key':key})
                doc=body.get('data',{}) if isinstance(body,dict) else {}
                if isinstance(doc,dict):
                    # Index metadata wins when details omit fields. No full body
                    # or full-text reproduction is saved to issue.json.
                    for f in ('title','url','original_url','link','description','summary','snippet','published_at','publisher'):
                        if doc.get(f):row[f]=doc[f]
                    if not row.get('snippet') and not row.get('summary'):
                        row['snippet']=str(doc.get('description') or '')[:350]
            except RuntimeError as ex:errors.append('FreeNewsApi details: '+str(ex)[:160])
            time.sleep(pause)
        if not row.get('url'):
            row['url']=row.get('original_url') or row.get('link')
        obj=normalize(row,'freenews')
        stamp=timestamp(row.get('published_at'))
        if not stamp:
            errors.append('FreeNewsApi: undated article excluded')
            continue
        article_dt=dt.datetime.fromisoformat(stamp)
        if article_dt < cutoff or article_dt > now + dt.timedelta(hours=1):
            continue
        if obj.get('url') and obj.get('title'):output.append(obj)
    if detail_used>=detail_limit:errors.append('FreeNewsApi details: bounded daily detail cap reached')
    return output

def official_rss(config, errors):
    """Parse RSS or Atom using stdlib; an unavailable feed is a visible warning."""
    output=[]
    def get_text(elem,local_names):
        for child in elem.iter():
            tag=child.tag.rsplit('}',1)[-1]
            if tag in local_names and child is not elem:
                if tag=='link' and child.get('href'): return child.get('href')
                if child.text and child.text.strip(): return child.text.strip()
        return None
    for feed in config.get('official_rss',[]):
        try:
            r=SESSION.get(feed['url'],timeout=20)
            r.raise_for_status()
            root=ET.fromstring(r.content)
            entries=[e for e in root.iter() if e.tag.rsplit('}',1)[-1] in ('item','entry')]
            if not entries: errors.append(f"Official RSS empty/broken: {feed['name']}")
            for item in entries[:25]:
                raw={"title":get_text(item,('title',)),
                     "link":get_text(item,('link',)),
                     "published":get_text(item,('pubDate','published','updated','date')),
                     "summary":get_text(item,('description','summary','content')) or ''}
                output.append(normalize(raw,'official_rss',feed['name']))
        except (requests.RequestException,ET.ParseError) as exc:
            errors.append(f"RSS {feed['name']}: {type(exc).__name__}")
    return output

def gdelt(config, errors, sleep_seconds=5):
    output=[]
    for idx,q in enumerate(config.get('gdelt_queries',[])[:3]):
        if idx: time.sleep(sleep_seconds)  # politeness for shared GDELT API
        try:
            body=get_json('https://api.gdeltproject.org/api/v2/doc/doc',{
                'query':q,'mode':'artlist','format':'json','timespan':'48h','maxrecords':40,
                'sort':'datedesc'},timeout=35)
            for x in body.get('articles',[]):
                if isinstance(x,dict): output.append(normalize(x,'gdelt'))
        except (RuntimeError,ValueError,AttributeError) as exc:
            errors.append(f"GDELT: {type(exc).__name__}: {str(exc)[:110]}")
    return output
