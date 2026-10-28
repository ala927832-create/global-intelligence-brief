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
from qa.opml_free_p1 import collect as collect_free_opml_rss, attach_opml_provenance
from tools.gib_style_c_rc.live_html_qa import bounds, filter_raw_before_ranking, render as render_style_c
import hashlib

ROOT=Path(__file__).resolve().parent

def run(args):
    locked_contract()
    now=dt.datetime.now(dt.timezone.utc)
    if args.as_of: now=dt.datetime.fromisoformat(args.as_of.replace('Z','+00:00'))
    config=json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8'))
    issues=ROOT/'qa_outputs';issues.mkdir(exist_ok=True)
    errors=[]
    cached_path=getattr(args,'cached_issue',None)
    source_index=getattr(args,'source_index',None)
    source_mode=getattr(args,'source_mode','legacy')
    if cached_path:
        if args.fixture or args.morning_issue or source_index:
            raise ValueError('Cached issue cannot be combined with fixture, source index or morning comparison')
        # Reuse the already attributed source list; no FreeNewsApi/GDELT calls.
        # This is HISTORICAL OFFICIAL RESEARCH QA, never live-news validation.
        issue=load_issue(cached_path)
        if issue.get('kind')!='canonical_news_evidence':
            raise ValueError('Cached issue must use canonical evidence schema')
    else:
        source_health=None
        if args.fixture:
            raw=json.loads(Path(args.fixture).read_text(encoding='utf-8'))['articles']
        elif source_index:
            raw=json.loads(Path(source_index).read_text(encoding='utf-8'))
            if not isinstance(raw,list):
                raise ValueError('Source index must be a list of source entries')
            if not getattr(args,'source_health',None):
                raise ValueError('Real-source index requires a corresponding source-health report')
            source_health=json.loads(Path(args.source_health).read_text(encoding='utf-8'))
            if source_health.get('data_origin')!='USER_OPML_DIRECT_PUBLISHER_RSS':
                raise ValueError('Source-health report is not the validated original publisher RSS feed')
        elif source_mode=='opml':
            opml_config=json.loads((ROOT/'config'/'inoreader_free_feeds.json').read_text(encoding='utf-8'))
            raw,source_health=collect_free_opml_rss(opml_config,now=now)
        else:
            raw=freenews(config,now,errors)+official_rss(config,errors)+gdelt(config,errors)
        prior=load_issue(args.morning_issue) if args.morning_issue else None
        if source_health is not None:
            # The original OPML folder names are source provenance, never news desks.
            start,end=bounds(now.astimezone(ZoneInfo('Asia/Taipei')).date(),args.edition)
            raw,window_exclusions=filter_raw_before_ranking(raw,start,end)
            now=end.astimezone(dt.timezone.utc)
            errors.extend(['OPML_WINDOW_EXCLUSIONS_'+str(len(window_exclusions))]
                         if window_exclusions else [])
        issue=canonical_issue(raw,args.edition,now,config.get('section_weights'),prior,
                              require_material_relevance=not bool(args.fixture))
        if source_health is not None:
            attach_opml_provenance(issue,raw,source_health)
            issue['source_health']['source_snapshot_origin']=source_health.get('data_origin')
            issue['source_health']['global_editorial_contract']='2026-10-23-approved-v1'
            issue['source_health']['p2_rss_gate']=source_health.get('gate')
    issue['source_health']['collector_errors']=errors
    if not issue.get('source_health',{}).get('has_morning_comparison') and args.edition=='evening':
        issue['editorial_delta_status']='HOLD_NO_COMPLETED_SAME_DAY_MORNING'
    elif args.edition=='evening':
        issue['editorial_delta_status']='CANDIDATES_ONLY_MATERIAL_CHANGE_UNVERIFIED'
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
            issue['editorial_first_pass']=ai.get('first_pass_drafts',[])
            issue['editorial_rejected_second_pass']=ai.get('second_pass_rejected_drafts',[])
            issue['gemini_editorial']={'status':ai['status'],'warnings':ai.get('warnings',[]),
                                       'draft_count':len(edits),
                                       'first_pass_draft_count':len(ai.get('first_pass_drafts',[])),
                                       'revision_ratio_by_event':ai.get('revision_ratio_by_event',{}),
                                       'failed_stage':ai.get('failed_stage'),
                                       'http_status':ai.get('http_status')}
    # Keep both editorial passages and their linked source identifiers in the
    # canonical issue, so the offline book can be reproduced and audited.
    # They remain UNVERIFIED until explicit source-level editorial approval.
    issue['editorial_drafts']=edits
    issue['editorial_depth_audit']=audit_editorial_depth(issue,edits)
    issue['editorial_status']='REVIEW_REQUIRED'
    issue['release_approved']=False
    audit=audit_issue(issue,require_full=True)
    # QA previews are generated despite release hold and prominently labeled.
    folder=issues/issue['issue_id']; folder.mkdir(parents=True,exist_ok=True)
    doc=folder/'issue.json';save_issue(issue,doc)
    review=write_review_workbook(issue,folder)
    # Rejected AI material can be rendered only in a visibly labelled QA
    # offline preview. It is NOT accepted as an editorial_draft or evidence.
    preview_edits=edits or issue.get('editorial_rejected_second_pass',[])
    output=export(issue,preview_edits,folder,qa_only=True)
    # The frozen Style C reading layout and Essential/Deep QA use the identical
    # canonical source/evidence issue, not two independent newsrooms.
    issue_hash=hashlib.sha256(doc.read_bytes()).hexdigest()
    visual_gate={'cutoff_tpe':now.astimezone(ZoneInfo('Asia/Taipei')).isoformat(),
                 'capture_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'editorial_status':'HOLD','issue_sha256':issue_hash,
                 'source_mode':'opml' if issue['source_health'].get('free_opml') else source_mode}
    visual,style_packet,style_coverage=render_style_c(
        issue,issue.get('articles',[]),{},[],visual_gate,edits=preview_edits)
    (folder/(args.edition+'-style-c-qa.html')).write_text(visual,encoding='utf-8')
    (folder/'style_c_source_packet.json').write_text(
        json.dumps(style_packet,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'style_c_alignment.json').write_text(json.dumps({
        'canonical_issue_sha256':issue_hash,
        'style_c_issue_sha256':issue_hash,
        'edition':args.edition,'source_packet_count':len(style_packet),
        'coverage_by_topic':style_coverage,'release_approved':False,
        'photo_gate':'NO_EVENT_LICENSED_PHOTOS_APPROVED',
        'editorial_status':'REVIEW_REQUIRED'},ensure_ascii=False,indent=2),encoding='utf-8')
    quality_record=build_record(issue,issue.get('gemini_editorial'),None,None,live_source=not bool(args.fixture or cached_path),fixture=bool(args.fixture or cached_path))
    record_file=persist_record(quality_record,issues/'records')
    result={'issue_json':str(doc),'epub':output,
            'style_c_html':str(folder/(args.edition+'-style-c-qa.html')),
            'canonical_issue_sha256':issue_hash,
            'source_mode':source_mode,
            'source_snapshot_origin':issue.get('source_health',{}).get('source_snapshot_origin'),
            'qa_record':str(record_file),'release_approved':False,
            'release_hold_reasons':audit['reasons']+
            issue['editorial_depth_audit']['release_blockers'],
            'editorial_depth_audit':issue['editorial_depth_audit'],
            'primary_evidence_review':review,
            'primary_evidence_progress':progress(issue),
            'collector_errors':errors,
            'gemini_status':issue.get('gemini_editorial',{}).get('status','NOT_REQUESTED'),
            'qa_rejected_preview_draft_count':len(issue.get('editorial_rejected_second_pass',[])),
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
    ap.add_argument('--source-mode',choices=['legacy','opml'],default='legacy',
                    help='OPML public RSS shares canonical newsroom; legacy retained')
    ap.add_argument('--source-index',help='One real original-publisher article_index.json, reused by morning/evening')
    ap.add_argument('--source-health',help='Matched source_health.json from same original-publisher fetch')
    ap.add_argument('--cached-issue',help='Reuse a frozen, public and unverified issue.json without re-collecting news')
    ap.add_argument('--as-of',help='UTC, used for offline historical QA')
    ap.add_argument('--gemini',action='store_true',help='explicit API opt-in, also needs env vars')
    ap.add_argument('--verify-official',action='store_true',help='bounded official-source excerpt check; not automatic truth verification')
    ap.add_argument('--morning-issue',help='canonical morning issue JSON, for evening delta check')
    run(ap.parse_args())
