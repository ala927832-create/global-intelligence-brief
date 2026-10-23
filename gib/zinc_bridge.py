"""Read-only and allowlisted: never persist the full Zinc Intelligence snapshot."""
import datetime as dt
import requests

PUBLIC_SNAPSHOT='https://raw.githubusercontent.com/ala927832-create/zinc-intelligence-v26/main/data/latest_snapshot.json'
ALLOWED_MARKETS=('lme_zinc','shfe_zinc','gold','usdjpy','dxy')

def extract_public_watch(snapshot,now):
    try:
        run=dt.datetime.fromisoformat(snapshot['run_time'].replace('Z','+00:00'))
        if run.tzinfo is None: return {'status':'UNKNOWN_DATE','watch':[],'events':[]}
        age=(now-run).total_seconds()/3600
        if age<0 or age>120: return {'status':'STALE','watch':[],'events':[]}
    except (KeyError,ValueError,TypeError): return {'status':'NO_DATE','watch':[],'events':[]}
    watch=[]
    for key in ALLOWED_MARKETS:
        value=(snapshot.get('decision_book',{}).get('markets',{}) or {}).get(key,{})
        gate=value.get('data_gate') or ''
        if not str(gate).startswith('PASS'): continue
        direction=value.get('direction')
        if direction not in ('STRONG_BULL','BULL','NEUTRAL','BEAR','STRONG_BEAR'): continue
        watch.append({'asset':key,'direction':direction,
            'evidence_alignment':str(value.get('evidence_alignment') or '')[:80],
            'market_date':str(value.get('as_of') or '')[:32],
            'kind':'RESEARCH_ONLY_NOT_NEWS'})
    events=[]
    for e in snapshot.get('market_research',{}).get('events',{}).get('upcoming',[])[:7]:
        if e.get('status') not in ('SCHEDULED_NOT_RELEASED','SCHEDULED'): continue
        events.append({'title':str(e.get('title',''))[:110],
          'date':str(e.get('date',''))[:32], 'source':str(e.get('source',''))[:40],
          'source_url':str(e.get('source_url',''))[:300],
          'status':'SCHEDULED_NOT_RELEASED'})
    return {'status':'VALID','zinc_run_time':run.isoformat(), 'watch':watch,'events':events}

def get_public_watch(now,errors):
    try:
        resp=requests.get(PUBLIC_SNAPSHOT,timeout=15,headers={'Accept':'application/json'})
        resp.raise_for_status()
        return extract_public_watch(resp.json(),now)
    except (requests.RequestException,ValueError,TypeError) as exc:
        errors.append('Zinc bridge unavailable: '+type(exc).__name__)
        return {'status':'UNAVAILABLE','watch':[],'events':[]}
