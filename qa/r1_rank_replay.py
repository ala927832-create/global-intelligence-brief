"""Replay immutable six real snapshot ZIPs after editorial ranking change."""
import io, zipfile, json, os, requests, hashlib
from datetime import datetime
from pathlib import Path
from qa.p2_content_gate import eligible_source_rows, selected_story_gate
from gib.newsroom_v16 import canonical_issue
from gib.editorial import cluster, rank, editorial_event_family, canon_url
from urllib.parse import urlsplit
import re

REPO="ala927832-create/global-intelligence-brief"
ARTIFACT=12944730644

def run():
    token=os.environ.get("GH_TOKEN")
    if not token: raise RuntimeError("GH_TOKEN_REQUIRED")
    response=requests.get(f"https://api.github.com/repos/{REPO}/actions/artifacts/{ARTIFACT}/zip",
        headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"},
        timeout=(10,60))
    response.raise_for_status()
    z=zipfile.ZipFile(io.BytesIO(response.content))
    output=Path("qa_out/r1_replay")
    output.mkdir(parents=True,exist_ok=True)
    audits=[]
    for i in range(1,7):
        filename=f"snapshot_{i:02d}.json"
        raw=z.read(filename)
        d=json.loads(raw)
        now=datetime.fromisoformat(d["started_at_utc"])
        eligible,*_=eligible_source_rows(d["rows"],now,"morning")
        issue=canonical_issue(eligible,"morning",now,require_material_relevance=False,tiered_v3=True)
        gate=selected_story_gate(issue)
        selected=[]
        for j,a in enumerate(issue["articles"]):
            selected.append({"position":j+1,"title":a["title_original"],"tier":a["editorial_tier"],
              "topic":a["topic"],"rank_score":a["rank_score"],
              "urls":[s.get("url") for s in a["sources"]]})
        selected_urls={u for a in selected for u in a["urls"]}
        ranked=rank(cluster(eligible,now,cutoff_hours=72),{})
        selected_families={}
        for a in ranked:
            fam=editorial_event_family(a)
            if fam and canon_url(a.get("url","")) in {canon_url(u) for u in selected_urls}:
                selected_families.setdefault(fam,[]).append(a.get("url",""))
        decision_rows=[]
        for cand in ranked:
            url=cand.get("url","")
            matched=next((k for k,a in enumerate(selected,1) if canon_url(url) in {canon_url(u) for u in a["urls"]}),None)
            fam=editorial_event_family(cand)
            title=cand.get("title","")
            analysis=bool(re.search(r'^(?:opinion|commentary|op-ed|analysis|explained)\\s*[:|]|what .* reveals|what it means|why .* matters|社論|評論|觀點|解讀',title,re.I))
            reason=("SELECTED_MAIN" if matched and matched<=12 else
                    "SELECTED_SUPPLEMENT" if matched else
                    "RELATED_EVENT_ALREADY_SELECTED_REVIEW_DISTINCT_FACT" if fam and fam in selected_families else
                    "LOWER_EDITORIAL_RANK_OR_DIVERSITY_CAP_REVIEW" )
            decision_rows.append({"source_url":url,"title":title,
               "published_at":cand.get("published_at"),
               "source_domain":urlsplit(url).hostname,
               "event_family":fam,"editorial_type":"COMMENTARY_OR_ANALYSIS" if analysis else "REPORTED_NEWS_INDEX",
               "rank_score":cand.get("score"),"selected_position":matched,
               "decision_reason":reason,"related_selected_urls":selected_families.get(fam,[]) if fam else [],
               "manual_distinct_fact_verified":False})
        item={"snapshot_index":i,"original_sha256":hashlib.sha256(raw).hexdigest(),
              "source_rows":len(d["rows"]),"candidate_rows":len(eligible),
              "gate":gate,"selected":selected,"candidate_decisions":decision_rows,"high_rank_unselected":[x for x in decision_rows if not x["selected_position"] and x["rank_score"] >= min(a["rank_score"] for a in selected)]}
        audits.append(item)
        (output/f"review_{i:02d}.json").write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n")
        print("R1_REPLAY",i,gate["gate"],"selected",len(selected),flush=True)
    # Algorithmic gate != expert score; no auto-pass.
    report={"schema":"R1_SIX_SNAPSHOT_RANKING_REPLAY_V1","snapshots":audits,
      "expert_score":None,"editorial_signoff":False,"r1_approved":False,"decision_audit":"AUTOMATED_CANDIDATE_CLASSIFICATION_REQUIRES_INDEPENDENT_EDITORIAL_REVIEW",
      "publication":"OFF"}
    (output/"full_replay.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if len(audits)!=6 or any(x["gate"].get("blockers") for x in audits):
        raise SystemExit("R1_REPLAY_STRUCTURAL_FAIL")
if __name__=="__main__":run()
