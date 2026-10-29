"""V1.6: canonical, source-attributed newsroom evidence, NOT a fact verification oracle.

Output is immutable issue.json candidate. News lists alone must never be labelled VERIFIED.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
from urllib.parse import urlsplit
from .editorial import cluster, rank, diversified, diversified_v3, sig, material_news_candidate
from .subscription_news_policy import news_evidence_policy

TOPICS = {
    'macro': '全球宏觀', 'central_banks': '央行與金融',
    'geopolitics': '國際政治', 'asia':'亞洲經濟', 'technology':'科技與 AI',
    'energy':'能源與產業', 'corporates':'企業經營','unexpected':'全球其他事件'
}

def _id(url):
    return 'src_'+hashlib.sha256(url.encode()).hexdigest()[:12]

def _date(raw):
    try:
        d=dt.datetime.fromisoformat(raw.replace('Z','+00:00'))
        if d.tzinfo is None: return None
        return d.astimezone(dt.timezone.utc)
    except (ValueError,AttributeError,TypeError):return None

def article_sources(item):
    urls=[item.get('url')]+item.get('related_urls',[])
    uniq=[]
    for url in urls:
        p=urlsplit(url or '')
        if p.scheme!='https' or not p.netloc or url in uniq: continue
        uniq.append(url)
    return [{'source_id':_id(url), 'url':url,
             'publisher': (urlsplit(url).hostname or 'unknown'),
             'article_published_at': item.get('published_at'),
             'kind':'OFFICIAL_FEED' if item.get('official') and url==item.get('url') else 'NEWS_ARTICLE',
             'retrieval_status':'INDEX_ONLY',
             'discovery_provider':item.get('provider','UNKNOWN_SOURCE_INDEX'),
             'discovery_providers':list(item.get('discovery_providers') or [item.get('provider','UNKNOWN_SOURCE_INDEX')]),
             'evidence_status':'ATTRIBUTED_NOT_INDEPENDENTLY_VERIFIED'} for url in uniq]

def canonical_issue(raw, edition, now, weights=None, prior=None, max_items=12, require_material_relevance=False, tiered_v3=False):
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    if edition not in ('morning','evening'):raise ValueError('edition must be morning/evening')
    grouped=rank(cluster(raw,now,cutoff_hours=72 if edition=='morning' else 40),weights or {})
    prior=prior or {}
    previously=prior.get('articles',[])
    old={x.get('event_id'):x for x in previously}
    # Material updates are not inferred from word-count or number of reprints.
    candidates=[]
    for a in grouped:
        eid=sig(a['title'])
        prior_event=old.get(eid)
        urls=set(a.get('related_urls',[]))
        if edition=='evening' and prior_event:
            earlier=set(x.get('url') for x in prior_event.get('sources',[]))
            fresh_official=a.get('official') and bool(urls-earlier)
            if not fresh_official: continue
        candidates.append(a)
    # Verify source eligibility BEFORE the 12-story cap.
    # Earlier six of twelve selected candidates were dropped afterwards
    # because URLs were non-HTTPS/missing, wasting slots.
    eligible=[a for a in candidates if article_sources(a) and _date(a.get('published_at'))
              and (not require_material_relevance or material_news_candidate(a))]
    # V3 morning has two distinct editorial tiers. Preserve the old
    # 12-story mode for retrospective legacy fixtures and evening.
    tiered=bool(tiered_v3 and edition=="morning")
    chosen=(diversified_v3(eligible,top_n=24,max_per_section=8) if tiered
            else diversified(eligible,max_items,max_per_section=4))
    tier_main_count=(max(10,len(chosen)-12) if len(chosen)>=20 else 0) if tiered else 0
    rows=[]
    updates=[]
    for index,a in enumerate(chosen):
        sources=article_sources(a)
        if not sources: continue
        date=_date(a.get('published_at'))
        subscribed=news_evidence_policy(a)
        change_kind=('OFFICIAL_UPDATE_UNVERIFIED' if sig(a['title']) in old else 'NEW_REPORTED_EVENT') if edition=='evening' else 'MORNING_CANDIDATE'
        rows.append({
          'change_kind':change_kind,
          'editorial_tier':('main' if index<tier_main_count else 'supplement') if tiered else None,
          'event_id':sig(a['title']), 'topic':a['section'], 'topic_label':TOPICS.get(a['section'],'全球新聞'),
          'title_original':a['title'], 'event_time_utc':None,
          'article_published_at':date.isoformat() if date else None,
          'news_source_policy':subscribed,
          'news_reporting_eligible':subscribed['subscription_news_eligible'],
          'news_summary_generation_allowed':(
              len(str(a.get('snippet') or '').strip())>=50),
          'analysis_requires_independent_verification':True,
          'headline_summary':a.get('snippet','')[:450], 'rank_score':a.get('score',0),
          'sources': sources, 'evidence': [{
            'claim_id':sig(a['title'])+'-reported-01',
            'text':a.get('snippet','')[:450] or a['title'],
            'source_id':sources[0]['source_id'],
            'support_excerpt':a.get('snippet','')[:450] or a['title'],
            'verification':'ATTRIBUTED_UNVERIFIED',
            'source_location':'feed headline/snippet',
            'note':'來源所聲稱內容，尚未與原始全文核對，禁止標示 VERIFIED'
          }],
          'source_count':len(sources), 'interpretations':[],
          'editorial_note':('訂閱媒體原始報導可作新聞；補充分析與因果主張仍需查證'
                           if subscribed['subscription_news_eligible'] else
                           '候選新聞；研究與核實前不可推定因果關係')
        })
        if edition=='evening':updates.append({'event_id':sig(a['title']),'event_title':a['title'],
          'change_kind':change_kind,'summary':(a.get('snippet','') or '原始消息尚無摘要')[:300]+'（來源聲稱，尚未逐項核實）'})
    health={
      'candidate_count':len(raw), 'unique_count':len(grouped),
      'material_candidate_count':len(eligible),
      'unrelated_candidate_excluded':len(candidates)-len(eligible),
      'selected_count':len(rows),
      'subscribed_news_count':sum(x['news_reporting_eligible'] for x in rows),
      'subscribed_headline_only_count':sum(
          x['news_reporting_eligible'] and not x['news_summary_generation_allowed']
          for x in rows),
      'subscribed_news_not_conditional_on_ai_debate':True,
      'editorial_tiering_mode':'V3_TWO_LEVEL_NEWS_ONLY_NOT_EDITOR_APPROVED' if tiered else 'LEGACY',
      'selected_main_count':sum(x.get('editorial_tier')=='main' for x in rows),
      'selected_supplement_count':sum(x.get('editorial_tier')=='supplement' for x in rows),
      'fresh_dated_count':sum(bool(x['article_published_at']) for x in rows),
      'distinct_domains':len({s['publisher'] for x in rows for s in x['sources']}),
      'has_morning_comparison':bool(prior.get('issue_id')) if edition=='evening' else True
    }
    return {'schema_version':'1.6','kind':'canonical_news_evidence',
            'issue_id':now.strftime('%Y%m%dT%H%M%SZ')+'-'+edition,
            'edition':edition,'report_date':now.astimezone(dt.timezone(dt.timedelta(hours=8))).date().isoformat(),
            'as_of_utc':now.isoformat(),'editorial_status':'SOURCE_CANDIDATES_UNVERIFIED',
            'articles':rows,'deep_research':[], 'event_updates':updates,'source_health':health,
            'zinc_watch':[], 'limitations':[ '新聞索引與摘要不是原始新聞的逐項事實核實',
                '來源不足時禁止自行擴寫成30–45分鐘長文',
                '人工審核與實際來源測試前不得啟用無人值守正式發布']}

def audit_issue(issue, require_full=False):
    errors=[]; articles=issue.get('articles',[])
    ids=set()
    for a in articles:
        if not a.get('event_id') or a['event_id'] in ids: errors.append('duplicate/empty event_id')
        ids.add(a.get('event_id'))
        links={s['source_id'] for s in a.get('sources',[])}
        if not links: errors.append('article without sources')
        for s in a.get('sources',[]):
            if urlsplit(s.get('url','')).scheme!='https':errors.append('non-HTTPS article URL')
        for c in a.get('evidence',[]):
            if c.get('source_id') not in links:errors.append('claim references unknown source')
            if c.get('verification')=='VERIFIED' and c.get('source_location') in (None,'feed headline/snippet'):
                errors.append('index snippet cannot be VERIFIED')
    if require_full:
        if len(articles)<8:errors.append('Fewer than 8 primary edition news items')
        if issue['source_health']['distinct_domains']<4:errors.append('Insufficient source diversity')
        if issue.get('editorial_status')!='EDITOR_APPROVED':errors.append('Requires explicit editorial approval')
        if len(issue.get('deep_research',[]))<1:errors.append('At least one independently evidenced deep research study required')
        if issue.get('edition')=='evening' and not issue.get('source_health',{}).get('has_morning_comparison'):
            errors.append('Evening requires the completed morning issue for change detection')
        for a in articles[:3]:
            if not any(c.get('verification')=='VERIFIED' and c.get('source_location') not in (None,'feed headline/snippet') for c in a.get('evidence',[])):
                errors.append('Lead story lacks primary-evidence verification: '+a.get('event_id',''))
    return {'passed':not errors,'reasons':errors,'candidate_count':len(articles),
            'can_publish_automatic':not errors and bool(require_full)}

def load_issue(p):
    with open(p,encoding='utf-8') as f:return json.load(f)

def save_issue(issue,p):
    with open(p,'w',encoding='utf-8') as f:json.dump(issue,f,ensure_ascii=False,indent=2)
