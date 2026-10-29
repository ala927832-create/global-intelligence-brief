"""R2 authorized internal research evidence packet builder. No draft/render/release."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from gib.r2_evidence_packets import build_packets


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-index",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--max-documents",type=int,default=6)
    args=ap.parse_args()
    if args.max_documents<0 or args.max_documents>8:
        raise SystemExit("R2_OFFICIAL_DOCUMENT_BUDGET_MUST_BE_0_TO_8")
    p=Path(args.source_index)
    if not p.is_file():
        raise SystemExit("R2_SOURCE_INDEX_MISSING")
    rows=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rows,list):
        raise SystemExit("R2_SOURCE_INDEX_MUST_BE_ARRAY")
    root=Path(__file__).resolve().parents[1]
    conf=json.loads((root/"config/sources.json").read_text(encoding="utf-8"))
    result=build_packets(rows,dt.datetime.now(dt.timezone.utc),
                         weights=conf.get("section_weights",{}),
                         max_documents=args.max_documents)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
       "r2_packet_status":result["status"],
       "focus_analysis_packets":len(result["analysis_packets"]),
       "deep_study_candidates":len(result["current_deep_research_shortlist"]),
       "primary_context_located":result.get("focus_with_located_primary_context",0),
       "primary_fetch_results":len(result["primary_source_fetch_results"]),
       "curated_original_documents_matched":result.get("curated_primary_documents_located",0),
       "matched_original_document_claim_phrases":result.get("curated_primary_claim_phrases_matched",0),
       "signed_fact_complete_packets":result.get("focus_with_signed_claims",0),
       "gemini_called":False,
       "reader_generated":False,
       "report":str(out)
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
