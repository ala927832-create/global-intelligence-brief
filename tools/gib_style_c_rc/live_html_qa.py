"""Style C real-source HTML QA bridge. MANUAL/QA ONLY; no EPUB/LINE/Pages/Gemini."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, html, io, json, urllib.parse, urllib.request
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image
from gib.collect import freenews, official_rss, gdelt
from gib.newsroom_v16 import canonical_issue, save_issue, load_issue, audit_issue
from gib.evidence_review import check_claim_lineage
from tools.gib_style_c_rc.inoreader_source import collect_export_feeds, urls_from_environment, attach_provenance

TPE=ZoneInfo("Asia/Taipei")
ESC=lambda x: html.escape(str(x or ""),quote=True)
HOST="upload.wikimedia.org"
DESKS={"macro":"Economy","central_banks":"Central Banks","geopolitics":"World","asia":"Asia",
       "technology":"Technology","energy":"Energy","corporates":"Business","unexpected":"Other"}
PHOTOS=[
 {"id":"data-centre","filename":"datacenter.jpg","url":"https://upload.wikimedia.org/wikipedia/commons/d/d1/Data_Center.jpg","author":"Gideonwills44","date":"2016-08-24","licence":"CC BY-SA 4.0","page":"https://commons.wikimedia.org/wiki/File:Data_Center.jpg"},
 {"id":"eu","filename":"eu.jpg","url":"https://upload.wikimedia.org/wikipedia/commons/c/c0/Berlaymont_Building_-_European_Comission_-_20261010.jpg","author":"Foolxter","date":"2026-10-10","licence":"CC BY-SA 4.0","page":"https://commons.wikimedia.org/wiki/File:Berlaymont_Building_-_European_Comission_-_20261010.jpg"},
 {"id":"refinery","filename":"refinery.jpg","url":"https://upload.wikimedia.org/wikipedia/commons/a/a5/Bayway_Refinery%2C_New_Jersey.jpg","author":"Quintin Soloviev","date":"2026-01-31","licence":"CC BY 4.0","page":"https://commons.wikimedia.org/wiki/File:Bayway_Refinery,_New_Jersey.jpg"}]

def digest(b): return hashlib.sha256(b).hexdigest()
def atutc(v): return dt.datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(dt.timezone.utc)
def bounds(date,edition):
    if edition=="morning":
        start=dt.datetime.combine(date-dt.timedelta(days=1),dt.time(17),TPE)
        end=dt.datetime.combine(date,dt.time(7),TPE)
    else:
        start=dt.datetime.combine(date,dt.time(7),TPE)
        end=dt.datetime.combine(date,dt.time(17),TPE)
    return start,end

def filter_raw_before_ranking(raw,start,end):
    """Apply the edition's time window before ranking and its top-story cap."""
    accepted=[];excluded=[]
    lower=start.astimezone(dt.timezone.utc);upper=end.astimezone(dt.timezone.utc)
    for item in raw:
        try:
            val=dt.datetime.fromisoformat(str(item['published_at']).replace('Z','+00:00'))
            if val.tzinfo is None: raise ValueError('missing timezone')
            stamp=val.astimezone(dt.timezone.utc)
        except (KeyError,TypeError,ValueError,AttributeError):
            excluded.append({'title':item.get('title'),'reason':'NO_VALID_SOURCE_TIMESTAMP'})
            continue
        if not lower<=stamp<=upper:
            excluded.append({'title':item.get('title'),'reason':'OUTSIDE_CUTOFF_WINDOW'})
            continue
        accepted.append(item)
    return accepted,excluded

def get_photo(row,local,allow_network):
    """Only genuinely decoded, licensed-context photographs are embedded; no fake fallback."""
    p=local/row["filename"]
    state={"id":row["id"],"author":row["author"],"licence":row["licence"],"source":row["page"],"status":"MISSING"}
    if not p.exists() and allow_network:
        u=urllib.parse.urlparse(row["url"])
        if u.scheme=="https" and u.hostname==HOST and u.port is None:
            try:
                req=urllib.request.Request(row["url"],headers={"User-Agent":"GIB-HTML-QA/1.0"})
                with urllib.request.urlopen(req,timeout=18) as response:raw=response.read(12_000_001)
                if len(raw)<=12_000_000:
                    local.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(raw)
            except Exception:pass
    if not p.exists():return "",state
    try:
        raw=p.read_bytes()
        if len(raw)>12_000_000:raise ValueError("too large")
        with Image.open(io.BytesIO(raw)) as x:
            if x.format not in ("JPEG","PNG","WEBP"):raise ValueError("invalid format")
            x.verify()
        with Image.open(io.BytesIO(raw)) as x:
            x=x.convert("RGB")
            x.thumbnail((1300,1300),Image.Resampling.LANCZOS)
            sink=io.BytesIO()
            x.save(sink,format="JPEG",quality=82,optimize=True)
        b=sink.getvalue()
        return "data:image/jpeg;base64,"+base64.b64encode(b).decode("ascii"),{
            **state,"status":"EMBEDDED_QA_RIGHTS_REVIEW_PENDING","original_sha256":digest(raw),
            "embedded_sha256":digest(b),"bytes":len(b)}
    except Exception as exc:return "",{**state,"status":"INVALID_"+type(exc).__name__}

def filter_window(issue,morning,start,end):
    prior_ids={x.get("event_id") for x in (morning or {}).get("articles",[])}
    prior_urls={s.get("url") for x in (morning or {}).get("articles",[]) for s in x.get("sources",[])}
    keep=[];excluded=[]
    for x in issue.get("articles",[]):
        try:stamp=atutc(x["article_published_at"])
        except (KeyError,TypeError,ValueError):
            excluded.append({"event_id":x.get("event_id"),"reason":"INVALID_DATE"});continue
        if not start.astimezone(dt.timezone.utc)<=stamp<=end.astimezone(dt.timezone.utc):
            excluded.append({"event_id":x.get("event_id"),"reason":"OUTSIDE_EDITORIAL_WINDOW"});continue
        if issue["edition"]=="evening":
            newer=any(s.get("url") not in prior_urls for s in x.get("sources",[]))
            if x.get("event_id") in prior_ids and not newer:
                excluded.append({"event_id":x.get("event_id"),"reason":"NO_NEW_SOURCE"});continue
            x["update_type"]="NEW_SOURCE_UNVERIFIED" if x.get("event_id") in prior_ids else "NEW_REPORTED_ITEM_UNVERIFIED"
        else:x["update_type"]="MORNING_CANDIDATE_UNVERIFIED"
        keep.append(x)
    return keep,excluded

def render(issue,stories,photos,photo_status,gate):
    cards=[];articles=[];packet=[]
    for idx,x in enumerate(stories):
        sid="item-"+ESC(x.get("event_id") or idx)
        title=ESC(x.get("title_original"));desc=ESC(x.get("headline_summary") or "Only source headline available; details require verification.")
        desk=ESC(DESKS.get(x.get("topic"),"Other"))
        stamp=ESC(x.get("article_published_at"))
        cards.append(f'<article class="card"><div class="kicker">{desk.upper()} · {stamp}</div><h3><a href="#{sid}">{title}</a></h3><p>{desc}</p><a href="#{sid}">Read source-attributed brief →</a></article>')
        li=[]
        for s in x.get("sources",[]):
            url=s.get("url","")
            if not url.startswith("https://"):continue
            li.append(f'<li><a href="{ESC(url)}" target="_blank" rel="noopener noreferrer">{ESC(s.get("publisher") or "Original source")}</a> · {ESC(s.get("retrieval_status") or "INDEX_ONLY")}</li>')
            packet.append({"event_id":x.get("event_id"),"title":x.get("title_original"),
                           "published_at":x.get("article_published_at"),"url":url,
                           "source_id":s.get("source_id"),"retrieval_status":s.get("retrieval_status"),
                           "claim_review":"ATTRIBUTED_UNVERIFIED"})
        articles.append(f'<article class="full" id="{sid}"><div class="kicker">{desk.upper()} · {stamp}</div><h2>{title}</h2><p class="deck">{desc}</p><h3>What the source index reports</h3><p>{desc}</p><h3>Evidence boundaries</h3><p>This is a sourced index summary, not an independently checked or licensed full original. Background and counter-evidence require editor review.</p><h3>Difference from the morning issue</h3><p>{ESC(x.get("update_type"))}</p><h3>Source packet</h3><ul>{"".join(li)}</ul><a href="#front">Back to front page ↑</a></article>')
    selected=stories[:5]
    day5="".join(f'<li><a href="#item-{ESC(x.get("event_id"))}">{ESC(x.get("title_original"))}</a></li>' for x in selected)
    lead=stories[0] if stories else None
    lead_title=ESC(lead.get("title_original") if lead else "Source coverage insufficient")
    lead_desc=ESC(lead.get("headline_summary") if lead else "No candidate passed the publication-window filter.")
    photo_cards=[]
    for row in PHOTOS:
        data=photos.get(row["id"])
        if not data:continue
        caption=f'Archive/context, not this news event · {row["author"]} · {row["date"]} · {row["licence"]}'
        photo_cards.append(f'<figure><img src="{data}" alt="Historical editorial context photo"><figcaption>{ESC(caption)} · <a href="{ESC(row["page"])}" target="_blank" rel="noopener noreferrer">Source and licence</a></figcaption></figure>')
    lead_photo_id={"energy":"refinery","technology":"data-centre","asia":None,"geopolitics":None,"central_banks":None,"macro":None,"corporates":None}.get(lead.get("topic") if lead else None)
    available_photos={row["id"]:card for row,card in zip((r for r in PHOTOS if photos.get(r["id"])),photo_cards)}
    hero_visual=available_photos.get(lead_photo_id,"")
    hero_visual=hero_visual if hero_visual else '<div class="placeholder"><b>Photo review pending</b><p>No historical or event photo is presented as verified.</p></div>'
    coverage=Counter(DESKS.get(x.get("topic"),"Other") for x in stories)
    coverage_text=" · ".join(f'{ESC(k)}: {v}' for k,v in sorted(coverage.items()))
    css="""*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f2ea;color:#1a3043;font:16px/1.7 Georgia,'Noto Serif TC',serif}body.boox{background:#f0eee4;color:#153647}a{color:inherit}header,main,footer{max-width:1220px;margin:auto}header{border-top:5px solid #123b57;border-bottom:1px solid #bcc9c9;padding:12px 24px;background:#fffdf7}.mast{font-size:clamp(29px,4vw,52px);font-weight:bold}.micro,.kicker,nav,.flag,figcaption{font:700 11px Arial,sans-serif;letter-spacing:.5px}.kicker{color:#95713e}nav{display:flex;gap:17px;border-top:1px solid #cad1d0;padding-top:12px;flex-wrap:wrap}nav button{margin-left:auto;background:transparent;border:1px solid #a9bdb8;color:inherit;padding:6px}main{padding:20px 24px}.flag{background:#eee0c9;padding:11px 14px;color:#63431d}.hero{display:grid;grid-template-columns:1.3fr 1fr .76fr;gap:24px;margin-top:24px;padding-bottom:24px;border-bottom:2px solid #163d55}.hero h1{font-size:clamp(34px,3.4vw,53px);line-height:1.12;margin:8px 0}.deck{font-size:19px}.hero aside{border-left:1px solid #c6d0cf;padding-left:14px}.hero li{border-bottom:1px solid #b9c6c7;padding:8px 0}figure{margin:0}img{width:100%;max-height:330px;object-fit:cover}figcaption{font-weight:400;font-size:10px;color:#516773}.placeholder{background:#dfe8e5;padding:50px 15px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{border-top:1px solid #bcc9c9;padding-top:11px}.card h3{font-size:21px;line-height:1.26}.card p{font-size:15px}h2{font-size:29px;margin-top:36px;border-bottom:2px solid #163d55;padding-bottom:8px}.full{max-width:780px;margin:55px auto 0;border-top:3px solid #163d55;padding-top:24px}.full h2{border:0;font-size:36px;margin:8px 0}.full h3{font-size:19px}.full p{font-size:18px}.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.qa{background:#fffdf7;padding:15px;margin-top:26px}footer{font:12px Arial,sans-serif;color:#536876;padding:20px}@media(max-width:900px){.hero{grid-template-columns:1fr 1fr}.hero aside{grid-column:1/-1;border-left:0;border-top:1px solid #bdd0cf}.cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:630px){header,main{padding:14px}.hero,.cards,.gallery{grid-template-columns:1fr}.hero aside{grid-column:auto}.mast{font-size:28px}}"""
    label="MORNING" if issue["edition"]=="morning" else "EVENING"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GIB {label} HTML QA · {ESC(issue["report_date"])}</title><style>{css}</style></head><body><header><div class="micro">GLOBAL INTELLIGENCE BRIEF · INDEPENDENT HTML QA</div><div class="mast">Global Intelligence Brief</div><nav><a href="#front">Overview</a><a href="#news">World</a><a href="#sources">Sources</a><a href="#qa">QA</a><button id="boox" type="button">BOOX Color</button></nav></header><main><div class="flag">QA HOLD · {label} · cutoff {ESC(gate["cutoff_tpe"])} · source captured {ESC(gate["capture_utc"])} · Not signed journalism; not a published edition.</div><section class="hero" id="front"><div><div class="kicker">GLOBAL LEAD · SOURCE CANDIDATE</div><h1>{lead_title}</h1><p class="deck">{lead_desc}</p><a href="#news">Read attributed briefing ↓</a></div><div>{hero_visual}</div><aside><div class="kicker">THE DAY IN FIVE</div><ol>{day5}</ol></aside></section><section id="news"><h2>World in Brief</h2><div class="cards">{"".join(cards)}</div></section><section><h2>Real photo archive</h2><div class="gallery">{"".join(photo_cards) or "<p>No successfully decoded and embedded licensed photo in this edition.</p>"}</div></section><section id="sources"><h2>Source packet</h2><p>Source URLs, publication timestamps and source verification labels are saved in source_packet.json. Newsroom-index results are not independently confirmed.</p><p>{coverage_text}</p></section><section id="archive"><h2>Research archive</h2><p>Historical research is kept outside the dated world-news list. Old EIA/BLS reports are not presented as today's new events.</p></section><section id="articles">{"".join(articles)}</section><section class="qa" id="qa"><h2>Editorial / Offline QA</h2><p>Release HOLD: human fact-check, cross-publisher coverage, photo rights, real BOOX reader review and 10-day trial remain open.</p><p>Images in this file: {len(photos)}/3; only embedded data:image content is displayed. EPUB OFF · LINE OFF · Pages OFF · Schedule OFF.</p></section></main><footer>GIB Style C · Internal source-index QA, not a licensed newspaper or formal issue.</footer><script>document.getElementById('boox').onclick=()=>document.body.classList.toggle('boox')</script></body></html>''',packet,dict(coverage)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--edition",required=True,choices=["morning","evening"])
    ap.add_argument("--output",default="qa_outputs/html_style_c")
    ap.add_argument("--morning-issue")
    ap.add_argument("--download-photos",action="store_true")
    ap.add_argument("--source-mode",choices=["legacy","inoreader"],default="legacy")
    a=ap.parse_args()
    now=dt.datetime.now(dt.timezone.utc);date=now.astimezone(TPE).date()
    start,cutoff=bounds(date,a.edition)
    config=json.loads(Path("config/sources.json").read_text(encoding="utf-8"))
    errors=[]
    inoreader_health=None
    if a.source_mode=="inoreader":
        raw,inoreader_health=collect_export_feeds(urls_from_environment())
    else:
        raw=freenews(config,now,errors)+official_rss(config,errors)+gdelt(config,errors)
    collected=dt.datetime.now(dt.timezone.utc)
    prior=load_issue(a.morning_issue) if a.morning_issue else None
    scoped_raw,pre_rank_exclusions=filter_raw_before_ranking(raw,start,cutoff)
    issue=canonical_issue(scoped_raw,a.edition,cutoff.astimezone(dt.timezone.utc),config.get("section_weights"),prior,
                          max_items=16,require_material_relevance=True)
    issue["source_health"]["collector_errors"]=errors
    issue["source_mode"]=a.source_mode
    if inoreader_health is not None:
        attach_provenance(issue,scoped_raw,inoreader_health)
    issue["editorial_status"]="REVIEW_REQUIRED"
    issue["cutoff_tpe"]=cutoff.isoformat()
    issue["capture_started_utc"]=now.isoformat()
    issue["capture_finished_utc"]=collected.isoformat()
    rows,exclusions=filter_window(issue,prior,start,cutoff)
    issue["articles"]=rows
    issue["cutoff_exclusions"]=exclusions
    issue["source_health"]["claim_lineage_errors"]=check_claim_lineage(issue)
    blockers=audit_issue(issue,require_full=True)["reasons"]
    if a.source_mode=="inoreader":
        if any(inoreader_health["lane_stats"][lane]["readable_items"]==0 for lane in ("global","industry")):
            blockers.append("INOREADER_EMPTY_GLOBAL_OR_INDUSTRY_LANE")
        if any(not x.get("inoreader_lanes") for x in rows):
            blockers.append("INOREADER_SELECTED_SOURCE_LINEAGE_MISSING")
    blockers+=["SOURCE_INDEX_NOT_CLAIM_VERIFIED","INDEPENDENT_COVERAGE_REVIEW_PENDING",
                "HUMAN_REVIEW_PENDING","BOOX_REAL_DEVICE_PENDING","10_TRADING_DAY_TRIAL_NOT_STARTED"]
    offset=(now-cutoff.astimezone(dt.timezone.utc)).total_seconds()/60
    finished_offset=(collected-cutoff.astimezone(dt.timezone.utc)).total_seconds()/60
    if offset<0:blockers.append("EARLY_CAPTURE_PRE_CUTOFF_PREVIEW")
    if offset>35 or finished_offset>35:blockers.append("LATE_COLLECTION_NOT_CUTOFF_PROOF")
    if a.edition=="evening" and (not prior or prior.get("edition")!="morning" or prior.get("report_date")!=date.isoformat()):
        blockers.append("SAME_DAY_ACTUAL_MORNING_SNAPSHOT_REQUIRED")
    if not rows:blockers.append("NO_CUTOFF_WINDOW_STORIES")
    photo_cache=Path("qa_outputs/photo_cache");photos={};photo_audit=[]
    for row in PHOTOS:
        data,check=get_photo(row,photo_cache,a.download_photos)
        if data:photos[row["id"]]=data
        photo_audit.append(check)
    if len(photos)<len(PHOTOS):blockers.append("OFFLINE_PHOTO_EMBEDDING_INCOMPLETE")
    if photos:blockers.append("IMAGE_LICENSE_EDITORIAL_SIGNOFF_REQUIRED")
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    save_issue(issue,out/"issue.json")
    gate={"edition":a.edition,"report_date_tpe":date.isoformat(),"cutoff_tpe":cutoff.isoformat(),"capture_utc":now.isoformat(),
          "capture_finished_utc":collected.isoformat(),"release_approved":False,
          "source_mode":a.source_mode,"inoreader":inoreader_health,
          "source_index_candidates":len(raw),"window_eligible_before_rank":len(scoped_raw),"pre_rank_exclusions":pre_rank_exclusions,"selected":len(rows),
          "capture_lag_minutes":round(offset,1),"image_count":len(photos),
          "photo_audit":photo_audit,"excluded":exclusions,"collector_errors":errors,
          "blockers":sorted(set(blockers)),"morning_snapshot_reference":a.morning_issue}
    page,packet,coverage=render(issue,rows,photos,photo_audit,gate)
    (out/(a.edition+".html")).write_text(page,encoding="utf-8")
    (out/"source_packet.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding="utf-8")
    gate["coverage_by_desk"]=coverage
    gate["issue_sha256"]=digest((out/"issue.json").read_bytes())
    gate["html_sha256"]=digest(page.encode("utf-8"))
    (out/"qa_report.json").write_text(json.dumps(gate,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"qa":"HOLD","edition":a.edition,"stories":len(rows),
                      "photos":len(photos),"output":str(out),
                      "capture_utc":now.isoformat(),"blockers":gate["blockers"]},ensure_ascii=False))
if __name__=="__main__":main()
