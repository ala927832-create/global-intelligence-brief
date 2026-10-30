"""R1 E1/E2 evidence-first editorial QA on existing issue replay. No network or new source capture."""
from urllib.parse import urlsplit
from gib.editorial import canon_url, editorial_event_family

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
            "resolved":c["editorial_disposition"] not in
                ("HOLD_FOR_INDEPENDENT_CASE_REVIEW",None) and
                c["different_material_new_fact"]!="UNVERIFIED",
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
    e2_pass=not e2_cases
    return {"R1_E1":{"pass":e1_pass,"cases":e1_cases},
            "R1_E2":{"pass":e2_pass,"cases":e2_cases},
            "expert_90_gate":"NOT_ELIGIBLE" if not(e1_pass and e2_pass) else "READY_FOR_INDEPENDENT_REVIEW",
            "editorial_signoff":False,"release":"OFF"}
