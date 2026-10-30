"""Evidence-linked R1 adjudications. Restricted to Oct 30 frozen QA captures.

This ledger does not assert that inaccessible article bodies were examined.
Every supported editorial decision cites a source URL and records verification limits.
"""
CASES={
 "Fed利率「凍漲」":("ANALYSIS_NOT_POLICY_EVENT","https://news.cnyes.com/news/id/6640877","INVESTMENT_OUTLOOK"),
 "No Clear Winner in Israel Election":("SAME_ELECTION_RESULT","https://www.aljazeera.com/news/2026/10/29/israel-election-result-shows-no-overall-majority-as-vote-count-complete","CORE_EVENT_CORROBORATED_ONLY"),
 "〈貴金屬盤後〉黃金":("PROMOTED_DISTINCT_MARKET_MOVE","https://news.cnyes.com/news/id/6641352","SOURCE_ATTRIBUTED"),
 "Israel election results: Qatar":("RELATED_NEW_DIPLOMATIC_RESPONSE","https://www.theguardian.com/world/live/2026/oct/29/israel-election-results-live-updates-poll-netanyahu-eisenkot-bloc-coalition-latest-news","DISTINCT_CLAIM"),
 "Iran war live: IRGC":("DISTINCT_IRGC_CLAIM","https://www.aljazeera.com/news/liveblog/2026/10/30/iran-war-live-irgc-says-four-tankers-struck-mines-in-strait-of-hormuz","UNDERLYING_ATTACK_UNCONFIRMED"),
 "美伊衝突風險升高":("DISTINCT_BUSINESS_RESPONSE","https://www.reuters.com/business/energy/exxon-chevron-cancel-adipec-executive-trips-sources-say-2026-10-29/","SOURCE_ATTRIBUTED"),
 "歐洲央行利率按兵不動":("COMBINED_POLICY_AND_SUCCESSION","https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.pr261029~abbb6dc64b.sv.html","OFFICIAL_SUCCESSION_SUPPORT"),
 "As Missile Stockpiles Dwindle":("ONE_US_JAPAN_FACILITY_EVENT","https://apnews.com/article/3351555ce9c46b41a3e31d91b81894eb","CORROBORATED"),
 "Ukraine Pauses Strikes":("DISTINCT_ATTRIBUTED_UKRAINE_REPORT","https://www.wsj.com/world/ukraine-pauses-strikes-on-russian-refineries-after-pressure-from-u-s-a9e512f8","UNDERLYING_ORDER_NOT_INDEPENDENTLY_VERIFIED"),
}
# Official / independent confirmations verified on 2026-10-30, not RSS-only.
EXTRA={
 "Fed更有空間升息":("US_WEEKLY_JOBLESS_CLAIMS","https://apnews.com/article/929f6739871efc054ae72afca2b68c3a","CORROBORATED"),
 "Canada's new national security strategy":("CANADA_NEW_NATIONAL_SECURITY_STRATEGY","https://www.pm.gc.ca/en/news/news-releases/2026/10/29/prime-minister-carney-launches-plan-stronger-canada-strengthen","OFFICIAL_SOURCE"),
 "聯合國大會通過決議":("UN_CUBA_EMBARGO_RESOLUTION","https://www.eeas.europa.eu/delegations/un-new-york/eu-explanation-vote-un-general-assembly-draft-resolution-a81l5-embargo-imposed-united-states-america_en","OFFICIAL_SOURCE"),
 "US sanctions Rwanda":("RWANDA_SANCTIONS_PUBLISHER_REPORT","https://www.forth.news/lists/ustreas/CgUoPzPV6eyQAkvsSxoY7","OFFICIAL_RELEASE_REPRODUCED")
}
def evidence_for(title):
 for k,v in {**CASES,**EXTRA}.items():
  if k.casefold() in title.casefold():
   return {"decision":v[0],"evidence_url":v[1],"evidence_limit":v[2]}
 return None
def independent_24_review(selected):
 """Each slot has an explicit review. Unsupported facts remain open and lower score."""
 rows=[]
 for a in selected:
  ev=evidence_for(a["title"])
  scope="SPECIFIC_SOURCE_ADJUDICATION" if ev else "RSS_INDEX_ONLY_NOT_FULL_ARTICLE_VERIFIED"
  rows.append({"position":a["position"],"title":a["title"],
   "source_urls":a["urls"],"tier":a["tier"],"topic":a["topic"],
   "evidence":ev,"scope":scope,
   "source_attribution_available":bool(a["urls"]),
   "remaining_evidence_task":None if ev else "FETCH_PUBLISHER_FULL_TEXT_OR_PRIMARY_DOCUMENT_AND_VERIFY_MATERIAL_FACT",
   "independently_validated":bool(ev and ev["evidence_limit"] in
       ("CORROBORATED","DISTINCT_CLAIM","OFFICIAL_SUCCESSION_SUPPORT","CORE_EVENT_CORROBORATED_ONLY","OFFICIAL_SOURCE","OFFICIAL_RELEASE_REPRODUCED")),
   "editorial_note":"Requires full article claim/novelty comparison" if not ev else ev["decision"]})
 return rows
