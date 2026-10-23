"""Primary-source excerpt matching, not automated truth certification.

Only a small explicit allowlist of public institutions is fetched. Matching an
excerpt against a genuine fetched primary page proves location/provenance, not
that a whole model-written interpretation is true.
"""
from __future__ import annotations
import datetime as dt, hashlib, html, re
from html.parser import HTMLParser
from urllib.parse import urlsplit
import requests

APPROVED_HOSTS={
    'www.federalreserve.gov','www.bls.gov','www.boj.or.jp','www.ecb.europa.eu',
    'www.imf.org','www.eia.gov','www.worldbank.org','www.bea.gov',
    'www.census.gov', 'www.treasury.gov'
}
MAX_BYTES=800_000
class VisibleText(HTMLParser):
    def __init__(self): super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg') and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def normalize_text(text):return re.sub(r'\s+',' ',html.unescape(text or '')).strip()

def fetch_official_page(url,session=None):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in APPROVED_HOSTS or p.port not in (None,443):
        raise ValueError('not an approved HTTPS official source')
    s=session or requests.Session()
    r=s.get(url,timeout=18,allow_redirects=False,headers={'User-Agent':'GIB-ResearchVerification/1.0'})
    r.raise_for_status()
    if r.status_code in (301,302,303,307,308):raise ValueError('redirect requires revalidation')
    if len(r.content)>MAX_BYTES:raise ValueError('source document exceeds bounded fetch size')
    ctype=r.headers.get('Content-Type','').lower()
    if not any(x in ctype for x in ('text/html','application/xhtml','text/plain','application/xml','text/xml')):
        raise ValueError('unsupported official document type')
    parser=VisibleText();parser.feed(r.text)
    value=normalize_text(' '.join(parser.parts)) if 'html' in ctype else normalize_text(r.text)
    return {'url':url,'text':value,'sha256':hashlib.sha256(r.content).hexdigest(),
            'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat()}

def review_official_excerpts(issue,fetcher=fetch_official_page,max_documents=8):
    checked=0; report=[]; cache={}
    for article in issue.get('articles',[]):
        eligible={s['source_id']:s for s in article.get('sources',[]) if s.get('kind')=='OFFICIAL_FEED' and
                  urlsplit(s['url']).hostname in APPROVED_HOSTS}
        for c in article.get('evidence',[]):
            src=eligible.get(c.get('source_id'))
            if not src:continue
            url=src['url']
            try:
                if url not in cache:
                    if checked>=max_documents:continue
                    checked+=1;cache[url]=fetcher(url)
                page=cache[url]
                excerpt=normalize_text(c.get('support_excerpt',''))
                # Index snippets are often too short or not verbatim; never infer a match.
                if len(excerpt)>=45 and excerpt.casefold() in page['text'].casefold():
                    # Source-bounded context retained with original provenance.
                    # This proves a text match, NOT that a causal claim is true.
                    pos=page['text'].casefold().find(excerpt.casefold())
                    context=page['text'][max(0,pos-260):min(len(page['text']),pos+len(excerpt)+480)]
                    c.update(verification='SOURCE_EXCERPT_MATCH_NOT_FACT_VERIFIED',
                       source_location='exact snippet in retrieved official web text',
                       source_sha256=page['sha256'],retrieved_at=page['retrieved_at'],
                       official_context_excerpt=context[:900])
                    src.update(retrieval_status='OFFICIAL_EXCERPT_MATCH',
                               retrieved_at=page['retrieved_at'],
                               source_sha256=page['sha256'])
                    report.append({'claim_id':c['claim_id'],'status':'EXCERPT_MATCH'})
                else:report.append({'claim_id':c['claim_id'],'status':'UNVERIFIED_NO_EXACT_MATCH'})
            except (requests.RequestException,ValueError) as ex:
                report.append({'claim_id':c['claim_id'],'status':'SOURCE_FETCH_FAILED','reason':type(ex).__name__})
    issue.setdefault('source_health',{})['primary_source_review']={'fetched_count':checked,'claims':report}
    # Explicit manual sign-off still required after exact excerpt location.
    return report

def check_claim_lineage(issue):
    violations=[]
    for article in issue.get('articles',[]):
        refs={s.get('source_id') for s in article.get('sources',[])}
        for claim in article.get('evidence',[]):
            if claim.get('source_id') not in refs:violations.append('unbound claim: '+str(claim.get('claim_id')))
            if claim.get('verification')=='VERIFIED' and (not claim.get('reviewer') or not claim.get('source_sha256')):
                violations.append('unattested VERIFIED claim: '+str(claim.get('claim_id')))
    return violations
