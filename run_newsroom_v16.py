"""V1.6 standalone QA entrypoint. Safe by default; NEVER pushes LINE/Pages."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from gib.collect import freenews,gdelt,official_rss
from gib.newsroom_v16 import canonical_issue,audit_issue,save_issue,load_issue
from gib.gemini_editor_v16 import research_and_revise
from gib.contract import locked_contract
from gib.evidence_review import review_official_excerpts, check_claim_lineage
from gib.editorial_depth import audit_editorial_depth
from gib.research_dossier import make_dossiers, write_review_workbook, progress
from gib.qa_tracker import build_record, persist_record
from gib.publish_v16 import export

ROOT=Path(__file__).resolve().parent

def run(args):
    locked_contract()
    now=dt.datetime.now(dt.timezone.utc)
    if args.as_of: now=dt.datetime.fromisoformat(args.as_of.replace('Z','+00:00'))
    config=json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8'))
    issues=ROOT/'qa_outputs';issues.mkdir(exist_ok=True)
    errors=[]
    cached_path=getattr(args,'cached_issue',None)
    if cached_path:
        if args.fixture or args.morning_issue:
            raise ValueError('Cached issue cannot be combined with fixture or morning comparison')
        # Reuse the already attributed source list; no FreeNewsApi/GDELT calls.
        # This is HISTORICAL OFFICIAL RESEARCH QA, never live-news validation.
        issue=load_issue(cached_path)
        if issue.get('kind')!='canonical_news_evidence':
            raise ValueError('Cached issue must use canonical evidence schema')
    else:
        if args.fixture:
            raw=json.loads(Path(args.fixture).read_text(encoding='utf-8'))['articles']
        else:
            raw=freenews(config,now,errors)+official_rss(config,errors)+gdelt(config,errors)
        prior=None
        if args.morning_issue:prior=load_issue(args.morning_issue)
        issue=canonical_issue(raw,args.edition,now,config.get('section_weights'),prior)
    issue['source_health']['collector_errors']=errors
    if getattr(args,'verify_official',False) and not args.fixture:
        try:review_official_excerpts(issue)
        except Exception as exc:errors.append('Official evidence: '+type(exc).__name__)
    issue['source_health']['claim_lineage_errors']=check_claim_lineage(issue)
    issue['research_dossiers']=make_dossiers(issue)
    # Two paid-independent opt-in Gemini requests only, never automatically enables billing.
    edits=[]
    if args.gemini:
        if not (os.getenv('ENABLE_GEMINI')=='1' and os.getenv('GEMINI_FREE_TIER_CONFIRMED')=='1'):
            errors.append('Gemini disabled (free-tier confirmation not set)')
        else:
            ai=research_and_revise(issue)
            edits=ai.get('edits',[])
            issue['gemini_editorial']={'status':ai['status'],'warnings':ai.get('warnings',[]),
                                       'draft_count':len(edits),
                                       'failed_stage':ai.get('failed_stage'),
                                       'http_status':ai.get('http_status')}
    # Keep both editorial passages and their linked source identifiers in the
    # canonical issue, so the offline book can be reproduced and audited.
    # They remain UNVERIFIED until explicit source-level editorial approval.
    issue['editorial_drafts']=edits
    issue['editorial_depth_audit']=audit_editorial_depth(issue,edits)
    issue['editorial_status']='REVIEW_REQUIRED'
    audit=audit_issue(issue,require_full=True)
    # QA previews are generated despite release hold and prominently labeled.
    folder=issues/issue['issue_id']; folder.mkdir(parents=True,exist_ok=True)
    doc=folder/'issue.json';save_issue(issue,doc)
    review=write_review_workbook(issue,folder)
    output=export(issue,edits,folder,qa_only=True)
    quality_record=build_record(issue,issue.get('gemini_editorial'),None,None,live_source=not bool(args.fixture or cached_path),fixture=bool(args.fixture or cached_path))
    record_file=persist_record(quality_record,issues/'records')
    result={'issue_json':str(doc),'epub':output,'qa_record':str(record_file),'release_approved':False,
            'release_hold_reasons':audit['reasons']+
            issue['editorial_depth_audit']['release_blockers'],
            'editorial_depth_audit':issue['editorial_depth_audit'],
            'primary_evidence_review':review,
            'primary_evidence_progress':progress(issue),
            'collector_errors':errors,
            'gemini_status':issue.get('gemini_editorial',{}).get('status','NOT_REQUESTED'),
            'gemini_failed_stage':issue.get('gemini_editorial',{}).get('failed_stage'),
            'gemini_http_status':issue.get('gemini_editorial',{}).get('http_status'),
            'gemini_connected_and_called':bool(issue.get('gemini_editorial',{}).get('status')=='REVISED_DRAFT_PENDING_REVIEW')}
    (issues/(issue['issue_id']+'-QA.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--edition',choices=['morning','evening'],required=True)
    ap.add_argument('--fixture',help='offline test fixture (not a live feed)')
    ap.add_argument('--cached-issue',help='Reuse a frozen, public and unverified issue.json without re-collecting news')
    ap.add_argument('--as-of',help='UTC, used for offline historical QA')
    ap.add_argument('--gemini',action='store_true',help='explicit API opt-in, also needs env vars')
    ap.add_argument('--verify-official',action='store_true',help='bounded official-source excerpt check; not automatic truth verification')
    ap.add_argument('--morning-issue',help='canonical morning issue JSON, for evening delta check')
    run(ap.parse_args())
