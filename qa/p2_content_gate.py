"""GIB V3 source-first fail-closed gate.

Do not confuse a raw URL count with 20 DISTINCT attributable news events.
Live production of reader-facing QA is stopped here before Gemini, HTML, EPUB.
Pure code with no network or side effects.
"""
from __future__ import annotations
import datetime as dt
from collections import Counter
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from gib.contract import locked_contract
from gib.editorial import cluster, classify, material_news_candidate, SPORTS_LEISURE

TZ=ZoneInfo("Asia/Taipei")
UTC=dt.timezone.utc
INVALID_HOSTS={"news.google.com","www.inoreader.com","inoreader.com"}

def _date(raw):
    try:
        value=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        if value.tzinfo is None: return None
        return value.astimezone(UTC)
    except (ValueError,TypeError,OverflowError): return None

def _cutoff_window(cutoff,edition):
    local=cutoff.astimezone(TZ)
    if edition=="morning":
        return (local-dt.timedelta(hours=14)).astimezone(UTC),cutoff
    return (local-dt.timedelta(hours=10)).astimezone(UTC),cutoff

def _usable_source_summary(row):
    # Only actually returned publisher text, not the headline or AI prose.
    snippet=str(row.get("snippet") or row.get("description") or "").strip()
    if len(snippet)>=50: return True
    known={row.get("source_id"),*list(row.get("source_ids") or [])}
    for item in (row.get("reported_key_points") or []) + (
            row.get("source_digest",{}).get("points",[])
            if isinstance(row.get("source_digest"),dict) else []):
        if isinstance(item,dict) and item.get("source_id") and item.get("source_id") in known and (
                len(str(item.get("text") or "").strip())>=50):
            return True
    return False

def eligible_source_rows(rows,cutoff,edition="morning"):
    """Return only dated publisher excerpts that may enter G0 and G1.

    Crucially, do not rank or invent a 20-story issue from RSS URL counts.
    """
    if cutoff.tzinfo is None: raise ValueError("CUTOFF_REQUIRES_TIMEZONE")
    start,end=_cutoff_window(cutoff,edition)
    rejected=Counter()
    eligible=[]
    for row in rows:
        if not isinstance(row,dict):
            rejected["INVALID_ROW"]+=1;continue
        title=str(row.get("title") or "").strip()
        url=str(row.get("url") or "").strip()
        host=urlsplit(url).hostname
        if not title or not host or urlsplit(url).scheme!="https" or host.lower() in INVALID_HOSTS:
            rejected["INVALID_OR_UNORIGINAL_PUBLISHER_URL"]+=1;continue
        pub=_date(row.get("published_at"))
        if pub is None or not start<pub<=end:
            rejected["OUTSIDE_WINDOW_OR_MISSING_DATETIME"]+=1;continue
        if not _usable_source_summary(row):
            rejected["TITLE_ONLY_OR_INSUFFICIENT_SOURCE_TEXT"]+=1;continue
        if SPORTS_LEISURE.search(title):
            rejected["SPORTS_NOT_NEWS_DESK"]+=1;continue
        if not material_news_candidate(row):
            # A leading story on an approved WORLD newsroom feed need not
            # mention inflation/war/AI to be newsworthy. This relaxes only
            # discovery, not sourcing, human editing or editorial acceptance.
            allowed_global=(row.get("provider")=="direct_opml_rss"
                            and "global" in (row.get("source_groups") or
                                             [row.get("source_group")]))
            if not allowed_global:
                rejected["NONNEWS_OR_LOW_SIGNAL"]+=1;continue
        eligible.append(row)
    return eligible,rejected,start,end

def source_input_gate(rows,cutoff,edition="morning",contract=None,observed_at=None):
    """Morning candidate gate with explicit retrospective-capture diagnostics.

    A 2026-10-29 RSS read must not be called an on-time 2026-10-28 edition.
    """
    contract=contract or locked_contract()
    q=contract["editorial_acceptance"]["source_intake_hard_gate"]
    eligible,rejected,start,end=eligible_source_rows(rows,cutoff,edition)
    distinct=cluster(eligible,end,cutoff_hours=25)
    domains={urlsplit(a["url"]).hostname for a in distinct}
    topics={classify(a["title"]) for a in distinct}
    rules={
        "distinct_evidence_bearing_events":len(distinct),
        "original_publisher_domains":len(domains),
        "editorial_topic_groups":len(topics),
    }
    minimums={
        "distinct_evidence_bearing_events":q["min_distinct_current_events"],
        "original_publisher_domains":q["min_distinct_original_publisher_domains"],
        "editorial_topic_groups":q["min_editorial_topic_groups"],
    }
    blockers=[f"{key.upper()}_{val}_BELOW_{minimums[key]}"
              for key,val in rules.items() if val<minimums[key]]
    lag=None
    if observed_at is not None:
        if observed_at.tzinfo is None: raise ValueError("OBSERVED_AT_REQUIRES_TIMEZONE")
        lag=round((observed_at.astimezone(UTC)-end.astimezone(UTC)).total_seconds()/60,1)
        if lag < 0: blockers.append("SOURCE_SNAPSHOT_BEFORE_CUTOFF_INCOMPLETE")
        elif lag > 45: blockers.append("RETROSPECTIVE_CAPTURE_NOT_ON_TIME")
    if edition=="evening":
        # 20 articles and 30–40/40–50 min are MORNING ONLY.
        # The evening is gated separately by genuine morning delta + P2 evidence.
        blockers=[]
    result={
        "gate":"HOLD_SOURCE_INPUT_INCOMPLETE" if blockers else "PASS_SOURCE_CANDIDATES_ONLY_NOT_FACT_VERIFIED",
        "edition":edition,
        "source_cutoff_utc":end.isoformat(),"source_window_start_utc":start.isoformat(),
        "source_capture_lag_minutes":lag,
        # A near-cutoff timestamp on a retrospective batch does not prove
        # the six owner-approved scheduled captures actually ran.
        "is_timely_cutoff_snapshot_proven":False,
        "source_timestamp_within_45m_only":bool(lag is not None and 0<=lag<=45),
        "input_original_rows":len(rows),"eligible_original_rows":len(eligible),
        "distinct_eligible_provider_domains":len({urlsplit(x["url"]).hostname for x in eligible}),
        "sample_eligible_source_groups":dict(sorted(Counter(
            x.get("source_group") or "other" for x in eligible).items())),
        "repeated_or_syndicated_items":len(eligible)-len(distinct),
        **rules,"minimums":minimums,
        "rejected":dict(sorted(rejected.items())),
        "blockers":blockers,
        "sample_event_titles":[a["title"] for a in distinct[:6]],
        "news_not_scarce_inference_prohibited":True,
        "source_index_does_not_prove_original_article_full_text":True,
        "gemini_allowed":False if blockers else None,
        "reader_preview_allowed":False if blockers else None,
        "publication_approved":False,
    }
    return result

def selected_story_gate(issue,contract=None):
    """Second hard stop BEFORE Gemini when the selection is structurally short.

    This does not grant fact-check approval, and will intentionally HOLD until
    the V3 editorial tiering is implemented in correction round 2.
    """
    contract=contract or locked_contract()
    cfg=contract["editorial_acceptance"]["morning_content"]
    if issue.get("edition")!="morning":
        return {"gate":"DEFER_TO_EXISTING_EVENING_DELTA_GATE","blockers":[],
                "publication_approved":False}
    articles=issue.get("articles") or []
    ids=[a.get("event_id") for a in articles if a.get("event_id")]
    mains=[a for a in articles if a.get("editorial_tier")=="main"]
    shorts=[a for a in articles if a.get("editorial_tier")=="supplement"]
    blockers=[]
    if not (cfg["unique_news_total_min"]<=len(set(ids))<=cfg["unique_news_total_max"]):
        blockers.append("UNIQUE_NEWS_COUNT_OUTSIDE_20_24")
    if len(ids)!=len(set(ids)):blockers.append("DUPLICATE_OR_MISSING_EVENT_IDS")
    if not (cfg["main_news_min"]<=len(mains)<=cfg["main_news_max"]):
        blockers.append("MAIN_NEWS_COUNT_OUTSIDE_10_12")
    if not (cfg["supplementary_news_min"]<=len(shorts)<=cfg["supplementary_news_max"]):
        blockers.append("SUPPLEMENT_NEWS_COUNT_OUTSIDE_10_12")
    if len(mains)+len(shorts)!=len(articles):
        blockers.append("UNTIERED_NEWS_EVENTS")
    # G1 must assess THE SELECTED stories, not merely a diverse raw source pool.
    # Only primary original URLs count for publisher-domain diversity; a
    # syndicated "related URL" in a single story cannot create a new event.
    selected_domains=set()
    selected_topics=set()
    selected_primary_urls=[]
    for a in articles:
        if a.get("topic"): selected_topics.add(a["topic"])
        sources=a.get("sources") or []
        primary=sources[0].get("url","") if sources else ""
        domain=urlsplit(primary).hostname
        if domain and urlsplit(primary).scheme=="https":
            selected_domains.add(domain)
            selected_primary_urls.append(primary)
        else: blockers.append("SELECTED_EVENT_MISSING_PRIMARY_HTTPS_SOURCE")
        if len(str(a.get("headline_summary") or "").strip())<50:
            blockers.append("SELECTED_EVENT_INSUFFICIENT_SOURCE_EXCERPT")
    if len(selected_domains)<contract["editorial_acceptance"]["source_intake_hard_gate"]["min_distinct_original_publisher_domains"]:
        blockers.append("SELECTED_PUBLISHER_DIVERSITY_BELOW_4")
    if len(selected_topics)<contract["editorial_acceptance"]["source_intake_hard_gate"]["min_editorial_topic_groups"]:
        blockers.append("SELECTED_TOPIC_DIVERSITY_BELOW_4")
    if len(selected_primary_urls)!=len(set(selected_primary_urls)):
        blockers.append("DUPLICATE_SELECTED_PRIMARY_SOURCE_URL")
    blockers=list(dict.fromkeys(blockers))
    return {
        "gate":"HOLD_SELECTED_STORY_VOLUME" if blockers else "PASS_EDITORIAL_VOLUME_ONLY_NOT_EVIDENCE_VERIFIED",
        "blockers":blockers,"unique_events":len(set(ids)),
        "main_news":len(mains),"supplementary_news":len(shorts),
        "selected_primary_publisher_domains":len(selected_domains),
        "selected_editorial_topics":len(selected_topics),
        "gemini_allowed":False if blockers else None,
        "reader_preview_allowed":False if blockers else None,
        "publication_approved":False
    }
