"""Six independent on-demand OPML source snapshots for R1 CONTENT QA only.

No Gemini, public publishing, LINE, Pages, or historical cutoff backdating.
Each call actually fetches all 24 approved publisher feeds. Six calls are separate.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from qa.opml_free_p1 import collect, validate_config
from qa.p2_content_gate import source_input_gate, eligible_source_rows, selected_story_gate
from gib.newsroom_v16 import canonical_issue

UTC = dt.timezone.utc
CONFIG = Path("config/inoreader_free_feeds.json")
OUT = Path("qa_out/r1_on_demand")
COUNT = 6


def run(out=OUT, count=COUNT, pause=5, collector=collect, clock=None):
    if count != COUNT:
        raise ValueError("EXACTLY_SIX_INDEPENDENT_CAPTURES_REQUIRED")
    if pause < 0:
        raise ValueError("NEGATIVE_PAUSE")
    clock = clock or (lambda: dt.datetime.now(UTC))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if len(validate_config(config)) != 24:
        raise ValueError("EXPECTED_24_APPROVED_OPML_FEEDS")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "GIB_R1_ON_DEMAND_SIX_REAL_PULLS_v1",
                "scope": "CONTENT_ONLY_NOT_DEADLINE_RELIABILITY",
                "publication": "OFF", "snapshots": [], "r1_final_pass": False}
    for i in range(1, count + 1):
        start = clock()
        if start.tzinfo is None:
            raise ValueError("START_MUST_BE_TIMEZONED")
        articles, health = collector(config, now=start)
        finish = clock()
        cutoff = start
        try:
            gate = source_input_gate(articles, cutoff, "morning", observed_at=start)
            eligible, _, _, _ = eligible_source_rows(articles, cutoff, "morning")
            issue = canonical_issue(eligible, "morning", cutoff,
                                    require_material_relevance=False, tiered_v3=True)
            selection = selected_story_gate(issue)
            structural = not gate.get("blockers") and not selection.get("blockers")
        except Exception as exc:
            gate = {"blockers": ["GATE_EXCEPTION_" + type(exc).__name__]}
            selection = {"blockers": ["NOT_EVALUATED"]}
            structural = False
        domains = {urlsplit(a.get("url", "")).hostname for a in articles}
        snapshot = {
            "schema": manifest["schema"], "index": i,
            "started_at_utc": start.astimezone(UTC).isoformat(),
            "finished_at_utc": finish.astimezone(UTC).isoformat(),
            "window": "14h_before_actual_start",
            "article_count": len(articles),
            "original_domains": len(domains - {None}),
            "health": health,
            "source_gate": gate,
            "selection_gate": selection,
            "structural_pass": bool(structural),
            "expert_score": None, "expert_pass": False,
            "editorial_signoff": False, "publication": "OFF",
            "rows": articles
        }
        blob = (json.dumps(snapshot, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8")
        dest = out / ("snapshot_%02d.json" % i)
        dest.write_bytes(blob)
        manifest["snapshots"].append({
            "index": i, "filename": dest.name,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "started_at_utc": snapshot["started_at_utc"],
            "finished_at_utc": snapshot["finished_at_utc"],
            "article_count": len(articles),
            "structural_pass": bool(structural),
            "expert_score": None
        })
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("R1_PULL", i, "articles", len(articles), "structural", structural, flush=True)
        if i != count:
            time.sleep(pause)
    return manifest


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--out", default=str(OUT))
    args.add_argument("--pause", type=int, default=5)
    cfg = args.parse_args()
    result = run(out=cfg.out, pause=cfg.pause)
    print("R1_CONTENT_ACCEPTED", result["r1_final_pass"], flush=True)
