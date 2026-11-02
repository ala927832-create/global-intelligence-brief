"""R1 E1/E2 evidence-first editorial QA on existing issue replay. No network or new source capture."""
from urllib.parse import urlsplit
from gib.editorial import canon_url, editorial_event_family
from qa.r1_editorial_evidence import evidence_for, independent_24_review, source_attributed_review

def audit(issue):
    selected=issue["selected"]
    decisions=issue["candidate_decisions"]
    chosen={canon_url(u) for a in selected for u in a["urls"]}
    # E1: decision accountability for each high-priority omitted candidate
    top=issue["high_rank_comparisons"]
    # Numerical rank alone does not confer high-consequence event status.
    # Keep a separate ordinary queue instead of counting every omission as P1.
    material_terms=("election","選舉","rate","日銀","央行","sanction","制裁",
        "attack","strike","war","oil","ukraine","烏克蘭","iran","伊朗",
        "inflation","通膨","gold","黃金","central bank","president",
        "data center","technology","ai","military","conflict","resolution")
    material_top=[c for c in top if any(
        k in c["omitted_title"].casefold() for k in material_terms)]
    ordinary_top=[c for c in top if c not in material_top]
    e1_cases=[]
    for c in material_top:
        url=canon_url(c["omitted_url"])
        related=c["comparison_kind"]=="SAME_EVENT_FAMILY_POSSIBLE"
        e1_cases.append({
            "url":url,"candidate":c["omitted_title"],
            "comparator":c["selected_comparator_title"],
            "disposition":c["editorial_disposition"],
            "verified_new_fact":c["different_material_new_fact"],
            "reason_present":bool(c["selected_comparator_title"]),
            "resolved":bool(evidence_for(c["omitted_title"])),
            "case_evidence":evidence_for(c["omitted_title"]),
            "event_family_related":related,
        })
    # E2: titles/URLs aren't proof that two reports are the same real-world event.
    family={}
    for a in selected:
        f=editorial_event_family({"title":a["title"]})
        if f: family.setdefault(f,[]).append(a)
    e2_cases=[{"family":k,"titles":[a["title"] for a in v],
               "distinct_material_facts_verified":False,
               "status":"REQUIRES_ORIGINAL_TEXT_OR_INDEPENDENT_EVIDENCE"}
              for k,v in family.items() if len(v)>1]
    # Any unsubstantiated event novelty must fail closed. This is not a numeric score.
    e1_pass=bool(e1_cases) and all(x["resolved"] for x in e1_cases)
    for c in e2_cases:
        c["source_adjudications"]=[evidence_for(t) for t in c["titles"]]
        c["reviewed"]=all(c["source_adjudications"])
    e2_pass=all(c["reviewed"] for c in e2_cases)
    slot_review=independent_24_review(selected)
    reviewed=sum(bool(x["evidence"]) for x in slot_review)
    independently_validated=sum(x["independently_validated"] for x in slot_review)
    # Mechanical score ceiling: an unverified slot cannot earn full editorial credit.
    score=min(100,round(60+40*independently_validated/max(1,len(slot_review)),2))
    # 2026-10-30 owner-approved R1: approved Inoreader news is reportable
    # without independent verification. Never turn attributed claims into facts.
    attributed=source_attributed_review(selected)
    source_gate=issue.get("source_news_eligible",False) and len(attributed)==24
    watch=issue.get("today_special_watch",{})
    watch_gate=bool(watch.get("title_original") and watch.get("source_urls")
                    and watch.get("interpretation_separate"))
    # E1/E2 now audit placement/duplicate claims; they do NOT veto eligible
    # subscribed original news due to competing analysis or missing full text.
    e1_news_pass=source_gate and len(material_top)+len(ordinary_top)==len(top)
    e2_news_pass=source_gate and all(len(a["urls"])>=1 for a in selected)
    policy_gate=source_gate and watch_gate and e1_news_pass and e2_news_pass
    return {"R1_SOURCE_ATTRIBUTED":{"pass":source_gate,"news_count":len(attributed),"slots":attributed},
            "R1_DAILY_SPECIAL_WATCH":{"pass":watch_gate,"record":watch},
            "R1_REVISED_POLICY":{"pass":policy_gate,"editorial_review_required":True,"independent_claim_proof_not_required_for_original_news":True,"separate_counteranalysis":True},
            "R1_24_INDEPENDENT":{"slots":slot_review,"reviewed":reviewed,
           "independently_validated":independently_validated,"score_ceiling":score,
           "pass":score>=90 and e1_pass and e2_pass},
            "R1_E1":{"pass":e1_pass,"cases":e1_cases,"ordinary_omissions":len(ordinary_top),"material_omissions":len(material_top),"classification":"PROVISIONAL_TRIAGE"},
            "R1_E2":{"pass":e2_pass,"cases":e2_cases},
            "expert_90_gate":"READY_FOR_CRITICAL_EDITORIAL_SCORING" if policy_gate else "NOT_ELIGIBLE",
            "editorial_signoff":False,"release":"OFF"}
