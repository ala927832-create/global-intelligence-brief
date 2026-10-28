"""P2 source enrichment from the existing free providers in frozen_contract.json.

This is not a new RSS catalog or editorial desk. Every candidate is still
unverified index metadata. An external feed's availability and quality are
reported separately from the 24-feed P1 OPML gate. Missing API keys fail open
for other *source providers* but never count as verified coverage.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import urlsplit

from gib.collect import freenews, gdelt, official_rss
from gib.editorial import canon_url

KNOWN_PROVIDERS = ("official_rss", "gdelt", "freenews")
MAX_RECENT_DAYS = 7
MAX_ADDITIONAL_PER_PROVIDER = 100


def collect_existing_free_sources(config, now, fetchers=None):
    """Existing free, read-only adapters; no new external services or paid tiers."""
    fetchers=fetchers or {
        "official_rss": lambda errs: official_rss(config,errs),
        "gdelt": lambda errs: gdelt(config,errs),
        "freenews": lambda errs: freenews(config,now,errs),
    }
    results={}
    for provider in KNOWN_PROVIDERS:
        errs=[]
        fn=fetchers.get(provider)
        if fn is None:
            results[provider]={"raw":[],"errors":["PROVIDER_NOT_CONFIGURED"]}
            continue
        try:
            items=fn(errs)
            if not isinstance(items,list):
                errs.append("INVALID_PROVIDER_RESPONSE")
                items=[]
            results[provider]={"raw":items[:MAX_ADDITIONAL_PER_PROVIDER],
                               "errors":errs,
                               "returned_by_provider":len(items)}
        except Exception as exc:
            results[provider]={"raw":[],"errors":["ADAPTER_"+type(exc).__name__],
                               "returned_by_provider":0}
    return results


def _recent_free_row(row, provider, now):
    if not isinstance(row,dict):
        return None,"INVALID_SHAPE"
    if row.get("provider") not in (provider,None):
        return None,"PROVIDER_MISMATCH"
    title=str(row.get("title") or "").strip()
    url=str(row.get("url") or "").strip()
    parts=urlsplit(url)
    if not title or not url or parts.scheme!="https" or not parts.hostname or parts.username or parts.password:
        return None,"MISSING_TITLE_OR_ORIGINAL_HTTPS_URL"
    if parts.hostname in ("news.google.com","www.inoreader.com","inoreader.com"):
        return None,"ORIGINAL_PUBLISHER_URL_UNCONFIRMED"
    stamp=row.get("published_at")
    try:
        pub=dt.datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
        if pub.tzinfo is None:
            return None,"MISSING_TIMEZONE"
        pub=pub.astimezone(dt.timezone.utc)
    except (TypeError,ValueError,OverflowError):
        return None,"MISSING_VALID_PUBLICATION_DATE"
    if pub > now+dt.timedelta(minutes=10):
        return None,"FUTURE_PUBLICATION_DATE"
    if pub < now-dt.timedelta(days=MAX_RECENT_DAYS):
        return None,"STALE_OR_OUTSIDE_SNAPSHOT"
    # Preserve index-only provenance. Never claim an API return is fact checked.
    safe={**row,"title":title[:300],"url":url,
          "published_at":pub.isoformat(),
          "snippet":str(row.get("snippet") or "")[:350],
          "provider":provider,
          "official":bool(provider=="official_rss"),
          "verification_status":"INDEX_ONLY_NOT_FACT_CHECKED",
          "source_group":None,
          "source_ids":[],
          "source_groups":[],
          "discovery_providers":[provider]}
    return safe,None


def fuse_with_original_opml(opml_rows, opml_health, other_results, now):
    """Prefer original OPML row per URL; record independent *discovery*, not truth.

    Other providers may return the same syndicated publisher URL; deduplication
    does not create an extra confirming publisher or a VERIFIED claim.
    """
    by_url={}
    for row in opml_rows:
        key=canon_url(row.get("url",""))
        if not key:
            continue
        one=dict(row)
        one["discovery_providers"]=["direct_opml_rss"]
        by_url[key]=one
    diagnostics={}
    for provider in KNOWN_PROVIDERS:
        bucket=other_results.get(provider,{})
        items=bucket.get("raw") or []
        errors=list(bucket.get("errors") or [])
        reasons={}
        accepted=0
        duplicates=0
        for item in items[:MAX_ADDITIONAL_PER_PROVIDER]:
            safe,reason=_recent_free_row(item,provider,now)
            if reason:
                reasons[reason]=reasons.get(reason,0)+1
                continue
            accepted+=1
            key=canon_url(safe["url"])
            if key in by_url:
                duplicates+=1
                existing=by_url[key]
                existing["discovery_providers"]=sorted(set(
                    existing["discovery_providers"]+[provider]))
            else:
                by_url[key]=safe
        diagnostics[provider]={
            "raw_items":len(items),
            "eligible_recent_index_items":accepted,
            "duplicate_original_urls":duplicates,
            "net_new_original_urls":accepted-duplicates,
            "rejected":reasons,
            "errors":errors,
            "claimed_verified_facts":0
        }
    rows=sorted(by_url.values(),key=lambda r:r.get("published_at") or "",reverse=True)
    health=dict(opml_health)
    health["data_origin"]="USER_OPML_PLUS_EXISTING_FREE_PUBLIC_INDEXES"
    health["original_opml_p1_gate"]=opml_health.get("gate")
    health["p2_external_source_fusion"]=diagnostics
    health["p2_total_source_index_items"]=len(rows)
    health["p2_original_opml_index_items"]=len(opml_rows)
    health["p2_external_net_new_index_items"]=len(rows)-len(opml_rows)
    health["p2_all_claims_unverified"]=True
    return rows,health
