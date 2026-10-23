"""Strict editorial quality checks. Not an external fact-checker or BOOX test."""
from __future__ import annotations
import json
import re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree


def report_checks(packet, output, root):
    checks=[]
    def test(key, ok, info=''):
        checks.append({'check':key,'passed':bool(ok),'detail':str(info)})
    sources={x['id'] for x in packet.get('sources',[])}
    test('source_roster',len(sources)>=5, f'{len(sources)} distinct sources')
    test('articles_evidence_bound',len(packet.get('stories',[]))>=4 and all(
        x.get('source_ids') and set(x['source_ids']).issubset(sources) and len(x.get('verified_facts',[]))>=2 for x in packet.get('stories',[])), 'All articles have cited facts')
    test('deep_substantive_sections',len(packet.get('chapters',[]))>=3 and sum(len(x.get('sections',[])) for x in packet.get('chapters',[]))>=12, 'Research subsections')
    test('essential_length', output['morning-essential']['cjk_chars']>=1500,output['morning-essential']['cjk_chars'])
    test('deep_length', output['morning-deep']['cjk_chars']>=7500,output['morning-deep']['cjk_chars'])
    test('clear_sample_label',packet.get('editorial_status')=='CURATED_REVIEW_SAMPLE' and '不是' in packet.get('methodology',''), 'No live claim')
    pub=root/'docs'/'archive'/packet['date']
    for level in ('essential','deep'):
        text=(pub/f'morning-{level}.html').read_text(encoding='utf-8')
        test(level+'_semantic_blocks',all(x in text for x in ('issue-opening','topic-strip','keybox','watchbox','source-list')), 'Semantic editorial blocks present')
        test(level+'_cited_originals',text.count('https://')>=4, 'Links to original sources')
    epub=Path(output['morning-deep']['epub'])
    with ZipFile(epub) as z:
        names=z.namelist(); joined=' '.join(z.read(x).decode('utf-8') for x in names if x.endswith('.xhtml'))
        styles='\n'.join(z.read(x).decode('utf-8') for x in names if x.endswith('.css'))
        test('embedded_evidence_figures',sum(x.endswith('.png') for x in names)>=3,'Cover + 2 evidence figures')
        test('epub_semantic_blocks',all(x in joined for x in ('topic-strip','evidence-slab','research-section','watchbox')))
        test('no_forced_subheading_page_break',not re.search(r'page-break-before\s*:\s*always|break-before\s*:\s*page',styles), 'Long-form natural flow')
        parsable=True
        for name in names:
            if name.endswith(('.xhtml','.opf')):
                try: etree.fromstring(z.read(name))
                except etree.XMLSyntaxError: parsable=False
        test('xhtml_xml_parses',parsable, 'Well-formed XHTML/OPF')
    test('zinc_private_data_not_copied',not any(k in joined for k in ['procurement_state','demand_60d_t','current_inventory_t','LINE_CHANNEL_ACCESS_TOKEN']), 'No private keys/operational fields')
    result={'passed':sum(bool(x['passed']) for x in checks),'total':len(checks),
            'all_passed':all(x['passed'] for x in checks),'checks':checks,
            'limits':['Not a W3C EPUBCheck run','Not a BOOX NeoReader device test',
                      'Not a live FreeNewsApi.io integration test',
                      'Research sample only; not a live morning/evening delivery']}
    return result


def write_report(report,path):
    Path(path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
