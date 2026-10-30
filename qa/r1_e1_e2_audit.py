"""R1 E1/E2 evidence-first editorial QA on existing issue replay. No network or new source capture."""
from urllib.parse import urlsplit
from gib.editorial import canon_url, editorial_event_family
from qa.r1_editorial_evidence import evidence_for, independent_24_review

def audit(issue):
    selected=issue["selected"]
    decisions=issue["candidate_decisions"]
    chosen={canon_url(u) for a in selected for u in a["urls"]}
    # E1: decision accountability for each high-priority omitted candidate
    top=issue["high_rank_comparisons"]
    e1_cases=[]
    for c in top:
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
    return {"R1_24_INDEPENDENT":{"slots":slot_review,"reviewed":reviewed,
           "independently_validated":independently_validated,"score_ceiling":score,
           "pass":score>=90 and e1_pass and e2_pass},
            "R1_E1":{"pass":e1_pass,"cases":e1_cases},
            "R1_E2":{"pass":e2_pass,"cases":e2_cases},
            "expert_90_gate":"NOT_ELIGIBLE" if not(e1_pass and e2_pass and score>=90) else "READY_FOR_INDEPENDENT_REVIEW",
            "editorial_signoff":False,"release":"OFF"}
