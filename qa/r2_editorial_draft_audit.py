"""Audit sourced, original internal R2 editorial drafts without promoting them to release.

Only editorial STRUCTURE, source-lineage, timebase and quotation-limits are
machine checkable here. All source-level truth signoff stays for an editor.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from gib.editorial_depth import hanzi, redundancy

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"qa/r2_crosssource_claim_ledger_20261029.json"
ANALYSES=ROOT/"qa/r2_four_analyses_internal_20261029.json"
STUDIES=ROOT/"qa/r2_two_deep_studies_internal_20261029.json"
SECTIONS=("background","why_it_matters","transmission","history",
          "alternative","watch","limitations")
REF=re.compile(r"\[([FCDT][0-9]{2})\]")


def inspect(ledger, analyses, studies):
    dossiers={p["event_id"]:p for p in ledger["dossiers"]}
    issues=[]
    reports=[]
    cited=[]
    for typ,entries in (
        ("FOCUS_ANALYSIS",analyses["articles"]),
        ("CURRENT_DEEP_STUDY",studies["studies"])):
        for draft in entries:
            eid=draft["event_id"]
            dossier=dossiers.get(eid)
            findings=[]
            if dossier is None:
                findings.append("UNKNOWN_SOURCE_EVENT")
                sources=set()
            else:
                sources={c["id"] for c in dossier["claims"]}
                if dossier["human_reviewed"] or dossier["ready_for_gemini"]:
                    findings.append("UNAUTHORIZED_AUTO_CERTIFICATION")
            sections=draft.get("sections") or {}
            if any(not isinstance(sections.get(p),str)
                   or hanzi(sections[p])<55 for p in SECTIONS):
                findings.append("MISSING_SUBSTANTIVE_SEVEN_PART_ANALYSIS")
            combined="\n".join(sections.get(k,"") for k in SECTIONS)
            referenced=set(REF.findall(combined))
            if not referenced:
                findings.append("NO_CLAIM_LEVEL_LINEAGE_IN_DRAFT")
            extra=referenced-sources
            if extra:
                findings.append("CITED_CLAIM_MISSING_FROM_EVIDENCE_LEDGER")
            if any(not REF.findall(sections.get(p,"")) for p in SECTIONS):
                findings.append("ONE_OR_MORE_ANALYTIC_SECTIONS_WITHOUT_CLAIM_IDS")
            cjk=hanzi(combined)
            if cjk<800:
                findings.append("INSUFFICIENT_EVIDENCE_BOUNDED_CHINESE_DEPTH")
            repeated=redundancy(combined)
            if repeated>0.18:
                findings.append("REPEATED_TEXT_INSTEAD_OF_DISTINCT_ANALYSIS")
            if dossier:
                domains={urlsplit(src["url"]).hostname for src in dossier["sources"]
                         if urlsplit(src["url"]).scheme=="https"}
                independent_origin={src["issuer"] for src in dossier["sources"]}
                issue_date=dt.date.fromisoformat(ledger["issue_date"])
                source_ids=[src["id"] for src in dossier["sources"]]
                if len(source_ids)!=len(set(source_ids)):
                    findings.append("DUPLICATE_ORIGINAL_SOURCE_ID")
                for src in dossier["sources"]:
                    url=src["url"]
                    parsed=urlsplit(url)
                    if parsed.scheme!="https" or parsed.username or parsed.password:
                        findings.append("UNSAFE_OR_NON_HTTPS_ORIGINAL_SOURCE")
                    if "bls.gov/news.release/cpi.nr0.htm" in url.lower():
                        findings.append("MUTABLE_LATEST_RELEASE_LINK_NOT_PINNED")
                    when=src.get("publication_date")
                    if when:
                        try:
                            if dt.date.fromisoformat(when)>issue_date:
                                findings.append("SOURCE_PUBLISHED_AFTER_ISSUE_CUTOFF_DAY")
                        except ValueError:
                            findings.append("INVALID_SOURCE_PUBLICATION_DATE")
                if len(domains)<2 or len(independent_origin)<2:
                    findings.append("LESS_THAN_TWO_DISTINCT_SOURCE_ORIGINS")
                for cl in dossier["claims"]:
                    if cl["editor_signed"] or cl["source_match_status"]=="VERIFIED":
                        findings.append("UNATTESTED_CLAIM_PREMATURELY_MARKED_VERIFIED")
                    if not cl.get("source_ids"):
                        findings.append("UNSUPPORTED_CLAIM_NO_SOURCE_ID")
                    elif not set(cl["source_ids"]).issubset(
                          {s["id"] for s in dossier["sources"]}):
                        findings.append("CLAIM_HAS_UNKNOWN_SOURCE")
                    if cl.get("observation_date") and len(cl["observation_date"])<4:
                        findings.append("CLAIM_DATE_NOT_EXPLICIT")
                if not dossier.get("counterevidence") or not dossier.get("mechanism"):
                    findings.append("MISSING_COUNTEREVIDENCE_OR_CAUSAL_CHAIN")
                if not dossier.get("falsification") or not dossier.get("remaining_gaps"):
                    findings.append("NO_FALSIFICATION_OR_UNRESOLVED_LIMITATIONS")
            findings=sorted(set(findings))
            if findings:issues.extend(f"{eid}:{f}" for f in findings)
            reports.append({
                "kind":typ,"event_id":eid,"chinese_hanzi":cjk,
                "unique_claim_ids":len(referenced),"repetition_ratio":repeated,
                "source_lineage_structure_pass":not findings,
                "structural_blockers":findings,
                "editorially_reviewed":False,"gemini_passes":0
            })
            cited.extend(referenced)
    # Do not count multiple deep studies as distinct news focus events.
    focus_ids=[x["event_id"] for x in analyses["articles"]]
    study_ids=[x["event_id"] for x in studies["studies"]]
    if len(set(focus_ids))!=4 or len(focus_ids)!=4:
        issues.append("NOT_FOUR_DISTINCT_FOCUS_ARTICLES")
    if len(set(study_ids))!=2 or not set(study_ids).issubset(focus_ids):
        issues.append("NOT_TWO_CURRENT_FOCUS_LINKED_STUDIES")
    if len({d["topic"] for d in ledger["dossiers"]})!=4:
        issues.append("NOT_FOUR_DISTINCT_GLOBAL_FOCUS_TOPICS")
    if analyses.get("gemini_passes")!=0 or studies.get("gemini_passes")!=0:
        issues.append("GEMINI_PASS_RECORDED_BEFORE_SIGNOFF")
    if analyses.get("editorial_signoff")!="NOT_REQUESTED_NOT_OBTAINED":
        issues.append("UNAUTHORIZED_EDITORIAL_APPROVAL")
    total_focus=sum(x["chinese_hanzi"] for x in reports if x["kind"]=="FOCUS_ANALYSIS")
    total_deep=sum(x["chinese_hanzi"] for x in reports if x["kind"]=="CURRENT_DEEP_STUDY")
    return {
        "kind":"GIB_R2_INTERNAL_SOURCE_GROUNDED_DRAFT_AUDIT",
        "issue_date":"2026-10-29",
        "source_lineage_and_draft_structure_pass":not issues,
        "focus_analysis_chinese_hanzi":total_focus,
        "deep_studies_chinese_hanzi":total_deep,
        "distinct_news_focus_articles":len(set(focus_ids)),
        "headline_linked_deep_studies":len(set(study_ids)),
        "unique_cited_claims":len(set(cited)),
        "drafts":reports,
        "structural_blockers":sorted(set(issues)),
        "independent_human_fact_verification_completed":False,
        "editorial_depth_signoff_completed":False,
        "gemini_pass_one_called":False,
        "gemini_pass_two_called":False,
        "total_essential_issue_hanzi_verified":False,
        "total_deep_issue_hanzi_verified":False,
        "reading_minutes_verified":False,
        "g2_status":"HOLD_EVIDENCE_AND_HUMAN_EDITORIAL_SIGNOFF",
        "release_approved":False
    }


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True)
    args=a.parse_args()
    sources=json.loads(LEDGER.read_text(encoding="utf-8"))
    analyses=json.loads(ANALYSES.read_text(encoding="utf-8"))
    studies=json.loads(STUDIES.read_text(encoding="utf-8"))
    report=inspect(sources,analyses,studies)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "source_lineage_and_draft_structure_pass",
        "focus_analysis_chinese_hanzi","deep_studies_chinese_hanzi",
        "unique_cited_claims","structural_blockers","g2_status",
        "gemini_pass_one_called","release_approved")},ensure_ascii=False))
    return 0 if report["source_lineage_and_draft_structure_pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
