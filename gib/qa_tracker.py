"""Ten trading-session evidence log. QA metrics cannot be converted into release permission."""
from __future__ import annotations
import datetime as dt,json
from pathlib import Path
from .contract import locked_contract
from .evidence_review import check_claim_lineage

def day_ok(local_day,closed_dates=()):
    """Require a real US-market session, not merely a weekday.

    XNYS is an explicit global-finance QA proxy, independent of original Zinc.
    If the calendar cannot be checked, conservatively do not count the date.
    """
    if local_day in set(closed_dates):return False
    try:
        import exchange_calendars as xc
        import pandas as pd
        return bool(xc.get_calendar('XNYS').is_session(pd.Timestamp(local_day)))
    except (ImportError,ValueError,TypeError,OverflowError):
        return False

def build_record(issue,gemini=None,epubcheck=None,boox_device=None,live_source=False,fixture=False):
    locked_contract()
    health=issue.get('source_health',{})
    verified=sum(1 for a in issue.get('articles',[]) for c in a.get('evidence',[]) if c.get('verification')=='VERIFIED' and c.get('reviewer'))
    article_count=len(issue.get('articles',[]))
    fresh=sum(bool(a.get('article_published_at')) for a in issue.get('articles',[]))
    gemini=gemini or {}
    record={
      'report_date':issue['report_date'],'edition':issue['edition'],'issue_id':issue['issue_id'],
      'origin':'LIVE' if live_source and not fixture else 'FIXTURE_OR_OFFLINE',
      'market_calendar':'XNYS',
      'market_session_confirmed':day_ok(issue['report_date']),
      'sources_count':health.get('distinct_domains',0),'articles_count':article_count,
      'articles_with_dates':fresh,'event_updates':len(issue.get('event_updates',[])),
      'verified_claims':verified,'claim_violations':check_claim_lineage(issue),
      'deep_research_count':len(issue.get('deep_research',[])),
      'gemini_two_rounds':gemini.get('status')=='REVISED_DRAFT_PENDING_REVIEW',
      'epubcheck_passed':epubcheck is True,'boox_real_device_passed':boox_device is True,
      'editorial_approved':issue.get('editorial_status')=='EDITOR_APPROVED',
      'collector_error_count':len(health.get('collector_errors',[]))
    }
    record['newsroom_quality_passed']=(
      record['origin']=='LIVE' and record['market_session_confirmed'] and 8<=article_count<=12 and fresh==article_count
      and record['sources_count']>=4 and verified>=3 and not record['claim_violations']
      and record['gemini_two_rounds'] and record['deep_research_count'] in (2,3)
      and record['epubcheck_passed'] and record['editorial_approved']
    )
    return record

def persist_record(record,dirpath):
    p=Path(dirpath);p.mkdir(parents=True,exist_ok=True)
    name=f"{record['report_date']}-{record['edition']}.json"
    path=p/name;path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');return path

def rollup(folder,holidays=(),required_days=10,device_signoff=False,owner_release_approval=False):
    locked_contract()
    folder=Path(folder)
    records=[]
    for p in sorted(folder.glob('*.json')):
        try: r=json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,OSError):continue
        if isinstance(r,dict) and r.get('edition') in ('morning','evening'):records.append(r)
    dates=sorted({r['report_date'] for r in records if day_ok(r['report_date'],holidays)})
    completed=[];failed=[]
    for day in dates:
        sessions={x['edition']:x for x in records if x['report_date']==day}
        if not all(x in sessions for x in ('morning','evening')):failed.append({'day':day,'reason':'MISSING_EDITION'});continue
        if not all(sessions[x].get('newsroom_quality_passed') for x in ('morning','evening')):
            failed.append({'day':day,'reason':'QUALITY_NOT_PASSED'});continue
        completed.append(day)
    # A real-device check is separately attested; never guessed from XHTML/EPUB tests.
    ready=(len(completed)>=required_days and device_signoff and owner_release_approval)
    return {'completed_trading_days':len(completed),'required_days':required_days,'days':completed,
            'failed_days':failed,'boox_signoff':bool(device_signoff),
            'owner_release_approval':bool(owner_release_approval), 'production_ready':ready,
            'release_policy':'Always OFF unless explicitly approved by owner after real ten-day & device QA'}
