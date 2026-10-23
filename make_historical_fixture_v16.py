"""Regenerate the local October 13/14 historic fixture from bundled curated sample.
Never describes the result as current news.
"""
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parent
packet=json.loads((root/'samples'/'official_research_2026-10-23.json').read_text(encoding='utf-8'))
sources={x['id']:x for x in packet['sources']}
articles=[]
for story in packet['stories']:
    src=sources[story['source_ids'][0]]
    if not re.fullmatch(r'20\d\d-\d\d-\d\d',src['published']):continue
    articles.append({'title':story['title'], 'url':src['url'],
        'published_at':src['published']+'T12:00:00+00:00',
        'publisher':src['publisher'], 'snippet':story['summary'],
        'official':True,'provider':'historical_curated_sample'})
(root/'samples'/'historical_articles_v16.json').write_text(json.dumps({
 'note':'OCT 13–14 HISTORICAL QA ONLY. Not current news, intentionally fails publication thresholds.',
 'articles':articles},ensure_ascii=False,indent=2),encoding='utf-8')
print('Wrote historical articles:',len(articles))
