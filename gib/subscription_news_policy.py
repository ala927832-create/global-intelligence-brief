"""Original Inoreader OPML subscription is a news-attribution source, not a truth oracle.

Only source IDs genuinely imported into the owner-approved 24-feed direct RSS
configuration can trigger the owner's NEWS reporting exception. This does
not permit ungrounded AI summaries, analysis, forecast claims or publication.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPML_CONFIG = ROOT / "config" / "inoreader_free_feeds.json"


@lru_cache(maxsize=1)
def subscribed_sources():
    config=json.loads(OPML_CONFIG.read_text(encoding="utf-8"))
    items=config.get("feeds") or []
    by_id={x["id"]:x for x in items}
    # Fail closed if the approved 24-source roster was accidentally replaced.
    if len(items)!=24 or len(by_id)!=24:
        raise RuntimeError("SUBSCRIBED_OPML_ROSTER_NOT_THE_24_APPROVED_SOURCES")
    return by_id


def is_subscribed_news(row):
    """Publisher RSS discovery metadata must map to a configured OPML feed."""
    if not isinstance(row,dict) or row.get("provider")!="direct_opml_rss":
        return False
    source_id=row.get("source_id")
    if not isinstance(source_id,str):
        return False
    config=subscribed_sources().get(source_id)
    if not config or row.get("source_group")!=config["lane"]:
        return False
    # A fused original item retains these fields. Don't allow a discovery
    # record from GDELT/FreeNewsApi to borrow an OPML ID for an exemption.
    if row.get("source_name")!=config["name"]:
        return False
    ids=row.get("source_ids")
    if ids is not None and source_id not in ids:
        return False
    groups=row.get("source_groups")
    if groups is not None and config["lane"] not in groups:
        return False
    return True


def news_evidence_policy(row):
    """Reportable source claims are not the same as verified research facts."""
    if not is_subscribed_news(row):
        return {"subscription_news_eligible":False,
                "news_source_status":"NON_SUBSCRIBED_STANDARD_GATE",
                "independent_claim_verification":False}
    summary=str(row.get("snippet") or row.get("description") or "").strip()
    has_excerpt=len(summary)>=50
    return {
        "subscription_news_eligible":True,
        "news_source_status":"SUBSCRIBED_ATTRIBUTED_NEWS_NOT_FACT_CERTIFIED",
        "source_name":row.get("source_name"),
        "source_id":row.get("source_id"),
        "source_group":row.get("source_group"),
        "summary_policy":("ATTRIBUTED_PUBLISHER_EXCERPT" if has_excerpt
                          else "HEADLINE_ONLY_LINK_NO_AI_SUMMARY"),
        "independent_claim_verification":False,
        "research_requiring_independent_evidence":True,
        "news_may_be_reported_as_source_claim":True,
        "gemini_or_publication_permission":False
    }
