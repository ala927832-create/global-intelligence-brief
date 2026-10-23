"""One-command independent global morning/evening briefing pipeline."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from gib.collect import official_rss,freenews,gdelt
from gib.editorial import cluster,rank,label_updates,next_seen,sig,diversified
from gib.zinc_bridge import get_public_watch
from gib.ai import maybe_research
from gib.render import write_outputs,update_index

ROOT=Path(__file__).resolve().parent
TZ=ZoneInfo('Asia/Taipei')

def load_json(p,fallback):
    try:
        if p.is_file():return json.loads(p.read_text(encoding='utf-8'))
    except (json.JSONDecodeError,UnicodeError): pass
    return fallback

def run(edition,root=ROOT,now=None,fixture=None,use_zinc=True):
    now=now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    errors=[]
    conf=load_json(root/'config'/'sources.json',{})
    state=load_json(root/'data'/'state.json',{'seen':[]})
    if fixture:
        src=load_json(Path(fixture),{})
        raw=src.get('articles',[])
        bridge=src.get('zinc',{'status':'UNAVAILABLE','watch':[],'events':[]})
    else:
        raw=[]
        raw+=freenews(conf,now,errors)
        raw+=official_rss(conf,errors)
        raw+=gdelt(conf,errors)
        bridge=get_public_watch(now,errors) if use_zinc else {'status':'DISABLED','watch':[],'events':[]}
    combined=rank(cluster(raw,now),conf.get('section_weights',{}))
    all_labeled=label_updates(combined,state.get('seen',[]),edition,now)
    compare_ready=(edition!='evening' or state.get('last_morning_at','')[:10]==now.astimezone(TZ).date().isoformat())
    if edition=='evening' and not compare_ready:
        # Honest fallback if morning was missed: provide candidate articles without claiming to be new.
        selected=diversified(combined,conf.get('top_n',12))
    else:
        selected=diversified(all_labeled,conf.get('top_n',12))
    ai=maybe_research(selected,errors)
    paths=write_outputs(root,edition,selected,ai,bridge,now,errors,compare_ready)
    update_index(root)
    state['seen']=next_seen(state.get('seen',[]),combined,now)
    date=now.astimezone(TZ).date().isoformat()
    state[f'last_{edition}_at']=now.isoformat()
    if edition=='morning':state['last_morning_event_ids']=[sig(x['title']) for x in selected]
    (root/'data').mkdir(parents=True,exist_ok=True)
    (root/'data'/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    # Persist only the public allowlisted story metadata; never copy the original Zinc snapshot.
    fact_list=[{'title':a['title'],'url':a['url'],'publisher':a.get('publisher'),
      'published_at':a.get('published_at'),'section':a['section'],'score':a['score'],
      'official':a['official'],'event_id':sig(a['title'])} for a in selected]
    report={'edition':edition,'generated_at':now.isoformat(),'date':date,
            'events':fact_list,'source_health':{'warnings':errors,'total_candidates':len(raw),
            'unique':len(combined),'selected':len(selected)},
            'zinc_bridge_status':bridge.get('status'),'reports':[str(x.relative_to(root)) for x in paths]}
    (root/'data'/'last_run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--edition',choices=['morning','evening'],required=True)
    p.add_argument('--fixture',default=None,help='Offline fixture JSON for tests/demo; does not hit news APIs')
    p.add_argument('--no-zinc',action='store_true')
    p.add_argument('--legacy-preview',action='store_true',help='Deliberately allow OLD brief-only rendering for offline integration checks; not approved for editorial publication')
    args=p.parse_args()
    if not args.legacy_preview:
        raise SystemExit('QUALITY_HOLD: Legacy Markdown publisher is not release-approved. Run build_sample.py for the rebuilt evidence-bound editorial EPUB, or complete live source-depth acceptance before publication.')
    result=run(args.edition,fixture=args.fixture,use_zinc=not args.no_zinc)
    print(json.dumps({'edition':result['edition'],'date':result['date'],
                      'selected':len(result['events']),'warnings':result['source_health']['warnings'],
                      'reports':result['reports']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
