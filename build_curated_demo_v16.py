"""Historical, human-curated PRIMARY-source research sample only.

Combines older V1.5 substantive source-based chapters with V1.6 layout.
Not current news; not Gemini-generated; not publication approved.
"""
import datetime as dt
import json
from pathlib import Path
from gib.newsroom_v16 import canonical_issue,save_issue,audit_issue
from gib.publish_v16 import export,issue_body
ROOT=Path(__file__).resolve().parent
pkt=json.loads((ROOT/'samples/official_research_2026-10-23.json').read_text(encoding='utf-8'))
sources={x['id']:x for x in pkt['sources']}
articles=[]
for x in pkt['stories'][:3]:
    s=sources[x['source_ids'][0]]
    articles.append({'title':x['title'], 'url':s['url'], 'published_at':s['published']+'T12:00:00+00:00',
                     'snippet':x['summary'],'publisher':s['publisher'],
                     'official':True,'provider':'historical_curated_source'})
now=dt.datetime.fromisoformat('2026-10-15T09:00:00+00:00')
issue=canonical_issue(articles,'morning',now)
issue['editorial_status']='CURATED_HISTORICAL_SAMPLE'
issue['limitations']+=['僅為 2026-10-13/14 已發布官方文件的歷史研究樣本','三則主要事件，未達正式晨報八則基準']
for x in pkt['chapters'][:3]:
    secs=[]
    for sec in x['sections']:
        secs.append({'heading':sec['heading'],'body':'\n\n'.join(sec.get('paragraphs',[])),
                     'figure':sec.get('figure')})
    issue['deep_research'].append({'title':x['title'],'sections':secs,
            'verification':'PRIOR_CURATED_SAMPLE_REVIEW_REQUIRED',
            'source_ids':x['source_ids']})
edits=[]
for article in issue['articles']:
    s=next(x for x in pkt['stories'][:3] if x['title']==article['title_original'])
    edit={'event_id':article['event_id'],'source_ids':[z['source_id'] for z in article['sources']],
          'sections':{'background':s['summary'],'why_it_matters':s['why'],
                      'transmission':'\n\n'.join(s.get('explain',[])),
                      'history':'','alternative':'',
                      'watch':'\n\n'.join(s.get('watch',[])),
                      'limitations':'上述報告是 10 月 13–14 日已發布的歷史資料，不是本示範生成當天的即時新聞。'}}
    edits.append(edit)
out=ROOT/'curated_historical_qa';out.mkdir(parents=True,exist_ok=True)
save_issue(issue,out/'issue.json')
r=export(issue,edits,out)
import re
report={'status':'HISTORICAL_RESEARCH_QA_NOT_LIVE', 'stories':len(issue['articles']),
  'deep_topics':len(issue['deep_research']),
  'essential_cjk':len(re.findall(r'[\u3400-\u9fff]',issue_body(issue,edits,'essential'))),
  'deep_cjk':len(re.findall(r'[\u3400-\u9fff]',issue_body(issue,edits,'deep'))),
  'publication_gate':audit_issue(issue,require_full=True),
  'output':r}
(out/'READ_ME_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
