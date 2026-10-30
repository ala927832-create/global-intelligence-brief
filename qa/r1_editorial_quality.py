"""R1 editorial quality gates under owner-approved publisher attribution rules.
Do not score a generated summary that does not exist.
"""
def review(issue):
 selected=issue["selected"]
 watch=issue.get("today_special_watch",{})
 scores=[a.get("rank_score",0) for a in selected]
 rank_sorted=all(scores[i]>=scores[i+1] for i in range(len(scores)-1))
 slots=[{"position":a["position"],"title":a["title"],"tier":a["tier"],
         "publisher_urls":a["urls"],"status":"SOURCE_ATTRIBUTED",
         "actual_ai_summary":None,"fidelity_evaluated":False} for a in selected]
 # Generated summaries and actual reading layout are different outputs from news-index metadata.
 summary_pass=False
 reading_pass=False
 watch_pass=bool(watch.get("title_original") and watch.get("source_urls") and
                 watch.get("interpretation_separate") and
                 watch.get("reason") and
                 watch.get("story_position") in range(1,13))
 return {"SUMMARY_FIDELITY":{"pass":summary_pass,"reason":"NO_RENDERED_AI_SUMMARY_TO_COMPARE_TO_PUBLISHER_EXCERPT","slots":slots},
         "IMPORTANCE_RANKING":{"pass":rank_sorted,"status":"HEURISTIC_ORDER_ONLY_NOT_INDEPENDENT_NEWSWORTHINESS_SIGNOFF"},
         "READING_QUALITY":{"pass":reading_pass,"reason":"NO_RENDERED_FULL_ISSUE_OR_READER_VIEW"},
         "TODAY_SPECIAL_WATCH":{"pass":watch_pass,"record":watch,
                                "reason":"TOP_STORY_PROVENANCE_ONLY_NOT_INDEPENDENT_WATCH_SELECTION"},
         "CRITICAL_90":{"eligible":False,"score":None,"pass":False,
                        "reason":"SUMMARY_AND_READING_NOT_EVALUATED; NO_INVENTED_EXPERT_SCORE"}}
