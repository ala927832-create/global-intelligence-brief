"""GIB P1: collect public publisher RSS feeds from a user's exported OPML index.

This program does not use Inoreader's gated Output Feeds, OAuth credentials,
article bodies, Gemini, or publication. News claims remain UNVERIFIED.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit
from email.utils import parsedate_to_datetime
import requests

from gib.editorial import canon_url
from tools.gib_style_c_rc.inoreader_source import plain_text, strict_timestamp

CONF = Path("config/inoreader_free_feeds.json")
LANES = ("global", "macro", "energy_commodities", "taiwan")
MAX_RESPONSE = 1_500_000
MAX_ITEMS_PER_FEED = 35
MAX_ARTICLES = 600
UA = "GlobalIntelligenceBrief/1.0 (public RSS source discovery QA)"
SUSPENDED = "feed suspended! please contact the owner."


def validate_config(config):
    feeds = config.get("feeds")
    if not isinstance(feeds, list) or not feeds:
        raise ValueError("OPML_SOURCE_LIST_EMPTY")
    seen_ids, seen_urls = set(), set()
    for source in feeds:
        lane, source_id, url = source.get("lane"), source.get("id"), source.get("url")
        if lane not in LANES or not source_id or not isinstance(url, str):
            raise ValueError("OPML_SOURCE_BAD_METADATA")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port is not None:
            raise ValueError("OPML_SOURCE_URL_NOT_PUBLIC_HTTPS")
        if parsed.hostname in ("localhost", "127.0.0.1", "inoreader.com", "www.inoreader.com"):
            raise ValueError("OPML_SOURCE_URL_NOT_PUBLISHER_RSS")
        if source_id in seen_ids or url in seen_urls:
            raise ValueError("OPML_SOURCE_DUPLICATE_ID_OR_URL")
        seen_ids.add(source_id)
        seen_urls.add(url)
    if set(source["lane"] for source in feeds) != set(LANES):
        raise ValueError("OPML_SOURCE_MISSING_GROUP")
    return feeds


def _local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _direct_text(item, keys):
    for el in item:
        if _local(el.tag) in keys and el.text and el.text.strip():
            return el.text.strip()
    return ""


def _article_link(item):
    # Prefer direct alternate link in Atom, then direct text <link> in RSS.
    for el in item:
        if _local(el.tag) == "link":
            href = el.get("href")
            if href and el.get("rel", "alternate") in ("", "alternate"):
                return href.strip()
            if el.text and el.text.strip():
                return el.text.strip()
    return _direct_text(item, {"origlink"})


def parse_feed(raw, source, now=None):
    """Parse RSS 2.0 or Atom and preserve only original-link metadata."""
    now = now or dt.datetime.now(dt.timezone.utc)
    root = ET.fromstring(raw)
    items = [x for x in root.iter() if _local(x.tag) in ("item", "entry")]
    parsed = []
    reasons = {"missing_title_or_url": 0, "invalid_link": 0,
               "missing_timezone_or_date": 0, "future": 0, "suspended": 0}
    for item in items[:MAX_ITEMS_PER_FEED]:
        title = plain_text(_direct_text(item, {"title"}))[:300]
        description = _direct_text(item, {"description", "summary", "content"})
        url = _article_link(item)
        if title.casefold().startswith(SUSPENDED) and (
            "inoreader pro plan is required" in description.casefold()
            or "inoreader.com/upgrade" in url.lower()
        ):
            reasons["suspended"] += 1
            continue
        if not title or not url:
            reasons["missing_title_or_url"] += 1
            continue
        u = urlsplit(url)
        if u.scheme not in ("https", "http") or not u.hostname or u.username or u.password:
            reasons["invalid_link"] += 1
            continue
        stamp = strict_timestamp(_direct_text(item, {"pubdate", "published", "updated", "date", "issued"}))
        if not stamp:
            reasons["missing_timezone_or_date"] += 1
            continue
        when = dt.datetime.fromisoformat(stamp)
        if when > now + dt.timedelta(minutes=10):
            reasons["future"] += 1
            continue
        parsed.append({
            "title": title, "url": url, "published_at": stamp,
            "publisher": source["name"], "snippet": plain_text(description)[:350],
            "provider": "direct_opml_rss", "official": source["url"].startswith(
                ("https://www.federalreserve.gov/", "https://www.bls.gov/", "https://www.eia.gov/")),
            "source_group": source["lane"], "source_id": source["id"],
            "source_name": source["name"], "verification_status": "INDEX_ONLY_NOT_FACT_CHECKED",
        })
    return parsed, {"total_items": len(items), "rejected": reasons}


def _download(url):
    response = requests.get(
        url, timeout=(6, 10), allow_redirects=True,
        headers={"User-Agent": UA, "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*;q=0.1"},
        stream=True,
    )
    try:
        response.raise_for_status()
        final_url = urlsplit(response.url)
        if final_url.scheme != "https" or not final_url.hostname:
            raise ValueError("NON_HTTPS_REDIRECT")
        buf = bytearray()
        for chunk in response.iter_content(32_768):
            buf.extend(chunk)
            if len(buf) > MAX_RESPONSE:
                raise ValueError("FEED_TOO_LARGE")
        return bytes(buf)
    finally:
        response.close()


def check_one(source, fetcher=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    meta = {"id": source["id"], "lane": source["lane"], "name": source["name"],
            "status": "UNTESTED", "valid_items": 0, "recent_7d": 0}
    try:
        raw = (fetcher or _download)(source["url"])
        rows, stat = parse_feed(raw, source, now)
        meta.update(stat)
        meta["valid_items"] = len(rows)
        meta["recent_7d"] = sum(
            dt.datetime.fromisoformat(x["published_at"]) >= now - dt.timedelta(days=7)
            for x in rows)
        meta["status"] = "OK" if rows else (
            "SUSPENDED_OUTPUT" if stat["rejected"]["suspended"] else "NO_USABLE_ARTICLES"
        )
        return meta, rows
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        meta["status"] = "HTTP_" + str(code)
    except requests.RequestException as exc:
        meta["status"] = "NETWORK_" + type(exc).__name__
    except (ET.ParseError, ValueError, TypeError) as exc:
        # No raw provider page content in logs.
        meta["status"] = "UNREADABLE_FEED_" + type(exc).__name__
    return meta, []


def collect(config, fetcher=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    feeds = validate_config(config)
    results = {}
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        future_to_source = {
            pool.submit(check_one, source, fetcher, now): source["id"]
            for source in feeds
        }
        for future in cf.as_completed(future_to_source):
            results[future_to_source[future]] = future.result()
    stats = []
    by_url = {}
    for source in feeds:
        meta, rows = results[source["id"]]
        stats.append(meta)
        for row in rows:
            key = canon_url(row["url"]) or row["url"]
            if key not in by_url:
                by_url[key] = row
                by_url[key]["source_groups"] = [row["source_group"]]
                by_url[key]["source_ids"] = [row["source_id"]]
            else:
                prev = by_url[key]
                prev["source_groups"] = sorted(set(prev["source_groups"] + [row["source_group"]]))
                prev["source_ids"] = sorted(set(prev["source_ids"] + [row["source_id"]]))
    articles = sorted(by_url.values(), key=lambda x: x["published_at"], reverse=True)[:MAX_ARTICLES]
    coverage = {}
    for lane in LANES:
        subset = [x for x in stats if x["lane"] == lane]
        coverage[lane] = {
            "configured_feeds": len(subset),
            "feeds_with_valid_articles": sum(x["status"] == "OK" for x in subset),
            "feeds_with_recent_7d": sum(x["recent_7d"] > 0 for x in subset),
            "recent_7d_candidates_before_dedup": sum(x["recent_7d"] for x in subset),
            "feed_errors": sum(x["status"] != "OK" for x in subset),
        }
    recent = sum(dt.datetime.fromisoformat(x["published_at"]) >= now - dt.timedelta(days=7)
                 for x in articles)
    report = {
        "kind": "GIB_FREE_OPML_PUBLIC_RSS_SOURCE_GATE",
        "phase": "P1_ONLY", "release_approved": False,
        "editorial_claims_verified": 0,
        "data_origin": "USER_OPML_DIRECT_PUBLISHER_RSS",
        "checked_at_utc": now.isoformat(),
        "configured_sources": len(feeds),
        "unique_original_article_urls": len(articles),
        "recent_7d_unique_article_urls": recent,
        "coverage": coverage, "source_statuses": stats,
    }
    gate_pass = (
        all(coverage[lane]["feeds_with_recent_7d"] >= 1 for lane in LANES)
        and sum(x["status"] == "OK" for x in stats) >= 8
        and recent >= 12
    )
    report["gate"] = "PASS_DIRECT_RSS_DISCOVERY" if gate_pass else "PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED"
    return articles, report



def attach_opml_provenance(issue, raw, report):
    """Keep four group assignments and OPML source IDs on selected citations."""
    refs = {}
    for row in raw:
        key = canon_url(row.get("url", "")) or row.get("url", "")
        refs.setdefault(key, {"source_groups": set(), "source_ids": set()})
        refs[key]["source_groups"].update(row.get("source_groups", [row.get("source_group")]))
        refs[key]["source_ids"].update(row.get("source_ids", [row.get("source_id")]))
    for article in issue.get("articles", []):
        groups = set()
        for item in article.get("sources", []):
            key = canon_url(item.get("url", "")) or item.get("url", "")
            provenance = refs.get(key)
            if not provenance:
                continue
            item["discovery_provider"] = "direct_opml_rss"
            item["opml_source_groups"] = sorted(x for x in provenance["source_groups"] if x)
            item["opml_source_ids"] = sorted(x for x in provenance["source_ids"] if x)
            groups.update(item["opml_source_groups"])
        article["opml_source_groups"] = sorted(groups)
    issue.setdefault("source_health", {})["free_opml"] = report
    return issue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CONF))
    ap.add_argument("--output", default="qa_out/inoreader_free_opml")
    args = ap.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    articles, report = collect(config)
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "source_health.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "article_index.json").write_text(
        json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lane, c in report["coverage"].items():
        print("P1_SOURCE", lane, "configured", c["configured_feeds"],
              "recent_feeds", c["feeds_with_recent_7d"],
              "recent_candidates", c["recent_7d_candidates_before_dedup"])
    for row in report["source_statuses"]:
        print("P1_FEED", row["id"], row["status"],
              "valid", row["valid_items"], "recent", row["recent_7d"])
    print("P1_GATE", report["gate"], "recent_unique", report["recent_7d_unique_article_urls"])
    return 0 if report["gate"] == "PASS_DIRECT_RSS_DISCOVERY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
