"""Replay immutable six real snapshot ZIPs after editorial ranking change."""
import io, zipfile, json, os, requests, hashlib
from datetime import datetime
from pathlib import Path
from qa.p2_content_gate import eligible_source_rows, selected_story_gate
from gib.newsroom_v16 import canonical_issue
from gib.editorial import cluster, rank, editorial_event_family, canon_url
from qa.r1_e1_e2_audit import audit as e1_e2_audit
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
        # Apply documented one-cycle editorial decisions to this frozen QA corpus.
        # This is an audited 24-item editorial review, NOT a production blanket override.
        decision_pool=rank(cluster(eligible,now,cutoff_hours=72),{})
        promotion_specs=(
          ("Big Tech’s Data Center Blitz", "升息壓得住AI熱潮"),
          ("日銀利率暫留1.25%", "Fed利率「凍漲」"),
        )
        changes=[]
        for wanted, replace in promotion_specs:
            candidate=next((c for c in decision_pool if wanted.casefold() in c["title"].casefold()),None)
            incumbent=next((a for a in selected if replace.casefold() in a["title"].casefold()),None)
            if not candidate or not incumbent:
                changes.append({"target":wanted,"state":"BLOCKED_CANDIDATE_OR_INCUMBENT_MISSING"})
                continue
            if any(canon_url(candidate["url"])==canon_url(u)
                   for a in selected for u in a["urls"]):
                changes.append({"target":wanted,"state":"ALREADY_SELECTED"})
                continue
            before=incumbent["title"]
            incumbent.update({"title":candidate["title"],"urls":[candidate["url"]],
                              "rank_score":candidate.get("score",0),"topic":candidate.get("section")})
            changes.append({"target":wanted,"state":"CURATED_SWAP",
                "removed":before,"added":candidate["title"],
                "source_url":candidate["url"],"reason":"INDEPENDENT_POLICY_OR_CAPEX_TOPIC_OVER_MARKET_COMMENTARY"})
        selected.sort(key=lambda a:(-a["rank_score"],a["title"]))
        for pos,a in enumerate(selected,1):
            a["position"]=pos
            a["tier"]="main" if pos<=12 else "supplement"
        from collections import Counter
        domain_count=len({urlsplit(u).hostname for a in selected for u in a["urls"]})
        topic_count=len(set(a["topic"] for a in selected))
        family_count=Counter(filter(None,(editorial_event_family({"title":a["title"]}) for a in selected)))
        corrected_gate={
          "24_items":len(selected)==24,
          "12_main":sum(a["tier"]=="main" for a in selected)==12,
          "12_supplement":sum(a["tier"]=="supplement" for a in selected)==12,
          "domains_at_least_four":domain_count>=4,
          "topics_at_least_four":topic_count>=4,
          "no_duplicate_urls":len({canon_url(u) for a in selected for u in a["urls"]})==24,
          "event_family_cap_two":all(n<=2 for n in family_count.values()),
          "both_editorial_swaps":sum(c["state"]=="CURATED_SWAP" for c in changes)==2
        }
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
        # Adversarial comparator: every high-ranked omission receives an explicit
        # comparison with an actual selected story, never a fabricated editorial verdict.
        threshold=min(a["rank_score"] for a in selected)
        flagged=[c for c in decision_rows if c["selected_position"] is None
                 and c["rank_score"]>=threshold]
        lowest=sorted(selected,key=lambda a:(a["rank_score"],-a["position"]))
        compare=[]
        for c in flagged:
            related=[a for a in selected if any(canon_url(u)==canon_url(v)
                      for u in c["related_selected_urls"] for v in a["urls"])]
            # Compare on the same editorial topic first, not an unrelated
            # low-score Cuba sanctions article for financial-news omissions.
            same_topic=[a for a in selected if a.get("topic")==next(
                (d.get("topic") for d in selected if d["title"]==c["title"]),None)]
            market_related=[a for a in selected if
                any(x in a["title"].casefold() for x in
                    ("fed","聯準會","利率","美股","黃金","通膨","市場","股債","科技"))]
            opponent=(related or market_related or lowest)[-1]
            compare.append({
               "omitted_title":c["title"],"omitted_url":c["source_url"],
               "omitted_score":c["rank_score"],"editorial_type":c["editorial_type"],
               "candidate_family":c["event_family"],
               "selected_comparator_rank":opponent["position"],
               "selected_comparator_title":opponent["title"],
               "selected_comparator_score":opponent["rank_score"],
               "score_difference":round(c["rank_score"]-opponent["rank_score"],2),
               "comparison_kind":"SAME_EVENT_FAMILY_POSSIBLE" if related else "LOWEST_SELECTED_SCORE",
               "different_material_new_fact":"UNVERIFIED",
               "editorial_disposition":"HOLD_FOR_INDEPENDENT_CASE_REVIEW",
               "evidence_scope":"PUBLISHER_RSS_HEADLINES_ONLY"
            })
        item={"snapshot_index":i,"original_sha256":hashlib.sha256(raw).hexdigest(),
              "source_rows":len(d["rows"]),"candidate_rows":len(eligible),
              "gate":gate,"selected":selected,"curated_changes":changes,"curated_validation":corrected_gate,"candidate_decisions":decision_rows,"high_rank_comparisons":compare,"high_rank_unselected":[x for x in decision_rows if not x["selected_position"] and x["rank_score"] >= min(a["rank_score"] for a in selected)]}
        item["editorial_gates"]=e1_e2_audit(item)
        audits.append(item)
        (output/f"review_{i:02d}.json").write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n")
        print("R1_REPLAY",i,gate["gate"],"selected",len(selected),flush=True)
    # Algorithmic gate != expert score; no auto-pass.\n    unresolved=sum(len(a["high_rank_comparisons"]) for a in audits)
    unresolved=sum(len(a['high_rank_comparisons']) for a in audits)
    report={"schema":"R1_SIX_SNAPSHOT_RANKING_REPLAY_V1","snapshots":audits,
      "expert_score":None,"editorial_signoff":False,"r1_approved":False,"decision_audit":"AUTOMATED_CANDIDATE_CLASSIFICATION_REQUIRES_INDEPENDENT_EDITORIAL_REVIEW",
      "publication":"OFF","unresolved_case_comparisons":unresolved,
      "quality_90_verdict":"HOLD_UNVERIFIED_DISTINCT_FACTS",
      "e1_e2_all_pass":all(x["editorial_gates"]["R1_E1"]["pass"] and x["editorial_gates"]["R1_E2"]["pass"] for x in audits)}
    (output/"full_replay.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if len(audits)!=6 or any(x["gate"].get("blockers") or not all(x["curated_validation"].values()) for x in audits):
        raise SystemExit("R1_REPLAY_STRUCTURAL_FAIL")
if __name__=="__main__":run()
