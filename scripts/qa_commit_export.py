"""Export a safe QA status record and minimal morning comparison snapshot to a GitHub repo.

No private Zinc data, credentials, or full copyrighted articles are exported.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from gib.qa_tracker import build_record,persist_record
p=argparse.ArgumentParser();p.add_argument('--issue',required=True);p.add_argument('--output',default='qa_data');p.add_argument('--epubcheck-pass',action='store_true');args=p.parse_args()
issue=json.loads(Path(args.issue).read_text(encoding='utf-8'))
root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
record=build_record(issue,issue.get('gemini_editorial'),epubcheck=args.epubcheck_pass,boox_device=None,live_source=True)
fp=persist_record(record,root/'records')
if issue['edition']=='morning':
    snap={'issue_id':issue['issue_id'],'report_date':issue['report_date'],
      'articles':[{'event_id':x['event_id'],'title_original':x['title_original'],
       'sources':[{'url':z['url']} for z in x.get('sources',[])]} for x in issue['articles']]}
    target=root/'morning_snapshots'/f"{issue['report_date']}.json";target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'qa_record':str(fp),'newsroom_quality_passed':record['newsroom_quality_passed']},ensure_ascii=False))
