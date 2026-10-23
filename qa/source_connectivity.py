#!/usr/bin/env python3
"""GIB credential/source reachability diagnostic. No newsletter, no publication.

Reports *API connectivity*, not evidence verification, source quality, or two-stage
Gemini editorial success. Credentials are read from environment, never emitted.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = Path("qa_out/connection.json")
NOW = dt.datetime.now(dt.timezone.utc)
UA = "GlobalIntelligenceBrief-ReadOnly-ConnectionQA/1.0"


def request_json(url, headers=None, body=None, timeout=25):
    request = urllib.request.Request(
        url, data=body, headers={"User-Agent": UA, **(headers or {})},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = resp.read(800_000)
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return "NETWORK_" + type(exc).__name__, None


def record(provider, status, **fields):
    print(f"{provider}: {status}")
    return {"provider": provider, "status": status, **fields}


def freenews():
    key = os.getenv("FREENEWS_API_KEY", "").strip()
    if not key:
        return record("FreeNewsApi.io", "MISSING_SECRET")
    params = urllib.parse.urlencode({"language": "en", "country": "us"})
    status, payload = request_json(
        "https://api.freenewsapi.io/v1/news?" + params,
        headers={"x-api-key": key},
    )
    if status != 200:
        return record("FreeNewsApi.io", "HTTP_OR_NETWORK_ERROR", code=status)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return record("FreeNewsApi.io", "UNEXPECTED_RESPONSE_FORMAT", code=status)
    return record("FreeNewsApi.io", "CONNECTED", count=len(payload["data"]))


def gdelt():
    params = urllib.parse.urlencode({
        "query": '"global economy"',
        "mode": "artlist", "format": "json", "timespan": "24h", "maxrecords": 20,
    })
    status, payload = request_json(
        "https://api.gdeltproject.org/api/v2/doc/doc?" + params, timeout=35
    )
    if status == 429:
        return record("GDELT", "RATE_LIMITED_429_WAIT_AND_RETRY_LATER", code=status)
    if status != 200:
        return record("GDELT", "HTTP_OR_NETWORK_ERROR", code=status)
    if not isinstance(payload, dict):
        return record("GDELT", "UNEXPECTED_RESPONSE_FORMAT")
    items = payload.get("articles", [])
    return record("GDELT", "CONNECTED", count=len(items) if isinstance(items, list) else 0)


def rss(name, url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            root = ET.fromstring(resp.read(800_000))
        articles = sum(
            elem.tag.rsplit("}", 1)[-1] in ("item", "entry") for elem in root.iter()
        )
        return record(name, "CONNECTED", count=articles)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return record(name, "SOURCE_DENIED_ACCESS_403", code=403)
        return record(name, "HTTP_OR_NETWORK_ERROR", code=exc.code)
    except (urllib.error.URLError, ET.ParseError, ValueError, TimeoutError) as exc:
        return record(name, "NETWORK_OR_XML_ERROR", category=type(exc).__name__)


def gemini():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return record("Gemini", "MISSING_SECRET")
    # Listing available models validates API authentication without generating
    # tokens or incurring model-inference usage.
    auth_code, model_list = request_json(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=10",
        headers={"x-goog-api-key": key}, timeout=25
    )
    if auth_code != 200 or not isinstance(model_list, dict):
        return record("Gemini", "AUTHENTICATION_OR_NETWORK_ERROR", code=auth_code)
    if os.getenv("GEMINI_FREE_TIER_CONFIRMED") != "1":
        return record("Gemini", "KEY_AUTHENTICATED_GENERATION_SKIPPED_FREE_TIER_UNCONFIRMED",
                      available_model_count=len(model_list.get("models", [])))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    if not model.replace("-", "").replace(".", "").isalnum():
        return record("Gemini", "INVALID_MODEL")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    outputs = []
    for pass_number in (1, 2):
        body = json.dumps({
            "contents": [{"parts": [{"text":
                "Return the single word OK, with no other text. This is a connectivity check."
            }]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 24},
        }).encode("utf-8")
        code, payload = request_json(url, headers={
            "x-goog-api-key": key, "Content-Type": "application/json"
        }, body=body, timeout=40)
        if code != 200:
            return record("Gemini", "HTTP_OR_NETWORK_ERROR", code=code,
                          successful_calls=len(outputs), model=model)
        if not isinstance(payload, dict) or not payload.get("candidates"):
            return record("Gemini", "NO_MODEL_CANDIDATE", successful_calls=len(outputs), model=model)
        outputs.append(True)
    return record("Gemini", "TWO_CONNECTIVITY_CALLS_OK_NOT_EDITORIAL_RESEARCH",
                  successful_calls=2, model=model)


def main():
    statuses = [
        freenews(),
        gdelt(),
        rss("Federal Reserve RSS", "https://www.federalreserve.gov/feeds/press_monetary.xml"),
        rss("BLS RSS", "https://www.bls.gov/feed/bls_latest.rss"),
        rss("BOJ RSS", "https://www.boj.or.jp/en/rss/whatsnew.xml"),
        gemini(),
    ]
    output = {
        "run_at_utc": NOW.isoformat(), "status": "DIAGNOSTIC_ONLY_NO_PUBLICATION",
        "credential_values_never_logged": True,
        "source_statuses": statuses, "newsroom_end_to_end_verified": False,
        "ten_trading_days_passed": 0,
        "epubcheck_verified": False, "boox_device_verified": False,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    # Missing keys or unavailable sources are diagnostic failures, not release approvals.
    if statuses[0]["status"] != "CONNECTED":
        raise SystemExit(2)
    if statuses[-1]["status"] in ("MISSING_SECRET", "HTTP_OR_NETWORK_ERROR",
                                "NO_MODEL_CANDIDATE", "INVALID_MODEL"):
        raise SystemExit(3)


if __name__ == "__main__":
    main()
