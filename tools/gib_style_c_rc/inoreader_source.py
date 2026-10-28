"""GIB Phase 1: Inoreader *exported RSS/JSON feed* adapter.

Only the output feed URLs (stored as GitHub Actions secrets) are read.
This is a source discovery adapter, NOT an editorial verification service.
No Inoreader API credentials or article body text are persisted.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

import requests
from gib.editorial import canon_url

LANES = {
    "global": "INOREADER_GLOBAL_FEED_URL",
    "macro": "INOREADER_MACRO_FEED_URL",
    "energy_commodities": "INOREADER_ENERGY_COMMODITIES_FEED_URL",
    "taiwan": "INOREADER_TAIWAN_FEED_URL",
}
# Official Inoreader region/beta hosts are explicitly allowed, not arbitrary domains.
ALLOWED_HOSTS = frozenset({
    "inoreader.com", "www.inoreader.com", "us.inoreader.com", "beta.inoreader.com",
    "innoreader.com", "www.innoreader.com",
})
MAX_FEED_BYTES = 2_000_000
MAX_ENTRIES_PER_LANE = 200
MAX_SNIPPET_CHARS = 450


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("style", "script", "noscript"):
            self.skipping += 1

    def handle_endtag(self, tag):
        if tag.lower() in ("style", "script", "noscript") and self.skipping:
            self.skipping -= 1

    def handle_data(self, value):
        if not self.skipping:
            self.words.append(value)


def plain_text(raw):
    parser = _Text()
    parser.feed(str(raw or "")[:10_000])
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.words))).strip()[:MAX_SNIPPET_CHARS]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _one_text(item, names):
    for el in item.iter():
        if el is item:
            continue
        if _local(el.tag) in names and el.text and el.text.strip():
            return el.text.strip()
    return ""


def _original_link(item):
    # Atom alternate links and RSS <link>, not the Inoreader output feed URL.
    for el in item:
        if _local(el.tag) == "link" and el.get("href") and el.get("rel", "alternate") in ("alternate", ""):
            return el.get("href")
    return _one_text(item, {"link", "origLink"})


def _validate_feed_url(url):
    """Return a safe HTTPS Inoreader output URL, never log the secret value.

    Normalize only documented/recognizable Inoreader hostnames and a full
    output-stream path. No arbitrary URL/redirect or non-HTTPS requests.
    """
    if not isinstance(url,str) or not url.strip():
        raise ValueError("INOREADER_EXPORT_URL_MISSING")
    value=url.strip()
    if len(value)>4096 or "\\n" in value or "\\r" in value:
        raise ValueError("INOREADER_EXPORT_VALUE_NOT_SINGLE_URL")
    if len(value)>=2 and value[0]==value[-1] and value[0] in ("'",'"'):
        value=value[1:-1].strip()
    if value in LANES.values():
        raise ValueError("INOREADER_EXPORT_SECRET_CONTAINS_NAME_NOT_URL")
    if value.lower() in ("rss","json","export","on","url","inoreader","inoreader.com"):
        raise ValueError("INOREADER_EXPORT_PLACEHOLDER_NOT_URL")
    # Some UIs copy an http or scheme-less address. Upgrade to HTTPS
    # locally only; verify the hostname and /stream/user/ path afterward.
    if value.lower().startswith("http://"):
        value="https://"+value[7:]
    elif not value.lower().startswith("https://"):
        short=value.lstrip("/")
        host=short.split("/",1)[0].lower()
        if host in ALLOWED_HOSTS:
            value="https://"+short
        else:
            raise ValueError("INOREADER_EXPORT_NOT_A_URL")
    try:
        parsed=urlsplit(value)
        hostname=parsed.hostname
        port=parsed.port
    except ValueError:
        raise ValueError("INOREADER_EXPORT_URL_MALFORMED") from None
    if parsed.scheme.lower()!="https":
        raise ValueError("INOREADER_EXPORT_HTTPS_REQUIRED")
    if parsed.username or parsed.password or parsed.fragment or port is not None:
        raise ValueError("INOREADER_EXPORT_URL_UNSAFE")
    if hostname not in ALLOWED_HOSTS:
        if hostname and (hostname.endswith(".inoreader.com") or hostname.endswith(".innoreader.com")):
            raise ValueError("INOREADER_EXPORT_UNRECOGNIZED_INOREADER_HOST")
        raise ValueError("INOREADER_EXPORT_NOT_INOREADER_DOMAIN")
    if not parsed.path.startswith("/stream/user/"):
        raise ValueError("INOREADER_EXPORT_EXPECTED_RSS_OR_JSON_STREAM_LINK")
    if parsed.path.rstrip("/").endswith("/view/html"):
        raise ValueError("INOREADER_EXPORT_HTML_VIEW_NOT_SUPPORTED")
    return value


def safe_feed_diagnostics(urls):
    """Classify configured lane URLs without outputting addresses or tokens."""
    result = {}
    for lane, secret_name in LANES.items():
        value = urls.get(lane, "")
        try:
            _validate_feed_url(value)
            result[lane] = "VALID_URL_SHAPE"
        except ValueError as exc:
            result[lane] = str(exc)
    return result


def check_environment_secrets():
    """CLI-friendly preflight. NEVER prints any secret URL or host/path/query."""
    results = safe_feed_diagnostics(urls_from_environment())
    for lane, status in results.items():
        print(f"INOREADER_FEED_URL_CHECK {lane}: {status}")
    return all(status == "VALID_URL_SHAPE" for status in results.values())


def _parse(raw: bytes, content_type: str):
    prefix = raw.lstrip()[:1]
    if prefix == b"{" or "json" in content_type.lower():
        doc = json.loads(raw)
        items = doc.get("items") if isinstance(doc, dict) else None
        if not isinstance(items, list):
            raise ValueError("INOREADER_JSON_ITEMS_MISSING")
        for item in items[:MAX_ENTRIES_PER_LANE]:
            if not isinstance(item, dict):
                continue
            # Output may use either JSON Feed fields or Inoreader's native
            # stream-entry shape (alternate/canonical links; Unix published).
            links = item.get("canonical") or item.get("alternate") or []
            if not isinstance(links, list):
                links = []
            original = next((link.get("href", "") for link in links
                             if isinstance(link, dict) and link.get("href")), "")
            summary = item.get("summary") or item.get("content_text") or item.get("content_html") or ""
            if isinstance(summary, dict):
                summary = summary.get("content") or ""
            yield {
                "title": item.get("title") or "",
                "url": item.get("url") or item.get("external_url") or original,
                "published": item.get("date_published") or item.get("published") or item.get("date_modified") or "",
                "summary": summary,
                "publisher": (item.get("author") or {}).get("name", "") if isinstance(item.get("author"), dict) else "",
            }
        return
    if prefix != b"<":
        raise ValueError("INOREADER_UNSUPPORTED_FEED_FORMAT")
    root = ET.fromstring(raw)
    entries = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
    for item in entries[:MAX_ENTRIES_PER_LANE]:
        yield {
            "title": _one_text(item, {"title"}),
            "url": _original_link(item),
            "published": _one_text(item, {"pubDate", "published", "updated", "date"}),
            "summary": _one_text(item, {"description", "summary", "content", "encoded"}),
            "publisher": _one_text(item, {"creator", "author"}),
        }


def strict_timestamp(value):
    """Published-time attribution must include a real timezone, never assume UTC."""
    if not value:
        return None
    if isinstance(value, (int,float)):
        return dt.datetime.fromtimestamp(value,dt.timezone.utc).isoformat()
    raw=str(value).strip()
    try:
        parsed=dt.datetime.fromisoformat(raw.replace('Z','+00:00'))
    except ValueError:
        try:
            parsed=parsedate_to_datetime(raw)
        except (ValueError,TypeError):
            return None
    if not parsed.tzinfo:
        return None
    return parsed.astimezone(dt.timezone.utc).isoformat()


def normalize_items(raw: bytes, content_type: str, lane: str):
    if lane not in LANES:
        raise ValueError("INVALID_LANE")
    rows = []
    rejected = {"missing_title_or_url": 0, "invalid_article_link": 0,
                "missing_publication_time": 0, "future_publication_time": 0}
    future_bound = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)
    for item in _parse(raw, content_type):
        title = plain_text(item["title"])[:280]
        url = str(item["url"] or "").strip()
        parsed = urlsplit(url)
        if not title or not url:
            rejected["missing_title_or_url"] += 1
            continue
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            rejected["invalid_article_link"] += 1
            continue
        if parsed.hostname in ALLOWED_HOSTS:
            # No canonical source yet; do not index Inoreader's reader URL as an original.
            rejected["invalid_article_link"] += 1
            continue
        stamp = strict_timestamp(item["published"])
        if not stamp:
            rejected["missing_publication_time"] += 1
            continue
        parsed_stamp = dt.datetime.fromisoformat(stamp)
        if parsed_stamp > future_bound:
            rejected["future_publication_time"] += 1
            continue
        rows.append({
            "title": title,
            "url": url,
            "published_at": stamp,
            "publisher": parsed.hostname.lower(),
            "snippet": plain_text(item["summary"]),
            "provider": "inoreader_export",
            "official": False,
            "inoreader_lanes": [lane],
        })
    return rows, rejected


def collect_export_feeds(urls, fetcher=None):
    """Fail closed if any configured lane is missing; no legacy-source fallback."""
    missing = [lane for lane in LANES if not urls.get(lane)]
    if missing:
        raise RuntimeError("INOREADER_NOT_CONNECTED:" + ",".join(missing))
    normalized_urls={}
    for lane in LANES:
        try:
            normalized_urls[lane]=_validate_feed_url(urls[lane])
        except ValueError as exc:
            # Print only safe lane name and stable validation code.
            raise ValueError(f"INOREADER_INVALID_EXPORT_{lane}:{exc}") from None

    def request(url):
        response = requests.get(url, timeout=24, allow_redirects=False,
                                headers={"User-Agent": "GIB-Inoreader-ReadOnly/1.0",
                                         "Accept": "application/feed+json,application/json,application/rss+xml,application/atom+xml,application/xml,text/xml"})
        # A redirect can inadvertently forward secret query strings to another host.
        if 300 <= response.status_code < 400:
            raise ValueError("INOREADER_REDIRECT_NOT_ALLOWED")
        response.raise_for_status()
        if len(response.content) > MAX_FEED_BYTES:
            raise ValueError("INOREADER_EXPORT_TOO_LARGE")
        return response.content, response.headers.get("Content-Type", "")

    fetch = fetcher or request
    lane_stats = {}
    by_url = {}
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
    for lane in LANES:
        url = normalized_urls[lane]
        try:
            content, content_type = fetch(url)
            if len(content) > MAX_FEED_BYTES:
                raise ValueError("INOREADER_EXPORT_TOO_LARGE")
            rows, rejected = normalize_items(content, content_type, lane)
        except Exception as exc:
            # Never include Inoreader feed address or raw exception text in logs/artifacts.
            raise RuntimeError("INOREADER_FEED_UNAVAILABLE:" + lane + ":" + type(exc).__name__) from None
        lane_stats[lane] = {
            "readable_items": len(rows),
            "rejected": rejected,
            "feed_sha256": hashlib.sha256(content).hexdigest(),
            "retrieved_at_utc": fetched_at,
            "export_refresh_expected_minutes": 30,
        }
        for row in rows:
            key = canon_url(row["url"]) or row["url"]
            if key in by_url:
                by_url[key]["inoreader_lanes"] = sorted(set(
                    by_url[key]["inoreader_lanes"] + row["inoreader_lanes"]))
            else:
                by_url[key] = row
    return list(by_url.values()), {
        "provider": "inoreader_export",
        "connected_lanes": list(LANES),
        "lane_stats": lane_stats,
        "distinct_original_article_urls": len(by_url),
        "retrieved_at_utc": fetched_at,
        "data_origin": "USER_CONFIGURED_INOREADER_EXPORT",
        "verified_claim_count": 0,
        "caveat": "RSS/JSON index is not independently fact-checked; export may be delayed ~30 minutes.",
    }


def urls_from_environment():
    return {lane: os.getenv(key, "").strip() for lane, key in LANES.items()}


def attach_provenance(issue, raw, health):
    """Preserve discovery and original-article attribution without exposing private feed URLs."""
    lanes_by_url = {}
    for row in raw:
        key = canon_url(row["url"]) or row["url"]
        lanes_by_url.setdefault(key, set()).update(row.get("inoreader_lanes", []))
    for article in issue.get("articles", []):
        found = set()
        for source in article.get("sources", []):
            key = canon_url(source.get("url", "")) or source.get("url", "")
            these = lanes_by_url.get(key, set())
            if these:
                source["discovery_provider"] = "inoreader_export"
                source["inoreader_lanes"] = sorted(these)
                found.update(these)
        article["inoreader_lanes"] = sorted(found)
    issue.setdefault("source_health", {})["inoreader"] = health
    return issue


if __name__ == "__main__":
    raise SystemExit(0 if check_environment_secrets() else 1)
