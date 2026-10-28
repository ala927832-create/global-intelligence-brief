"""Five genuine ad-hoc 2026-10-28 public RSS snapshots; not official cutoff captures."""
import datetime as dt
import hashlib
import json
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from gib.editorial import canon_url
from qa.opml_free_p1 import collect, validate_config

UTC=dt.timezone.utc
TPE=ZoneInfo("Asia/Taipei")
OUT=Path("qa_out/p2_five_now_20261028")

def now():
    result=dt.datetime.now(UTC)
    if result.astimezone(TPE).date().isoformat()!="2026-10-28":
        raise RuntimeError("EXPIRED_ONE_TIME_SOURCE_CAPTURE")
    return result

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,indent=2)+"\n"
    path.write_text(raw,encoding="utf-8")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def run():
    config=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))
    assert len(validate_config(config))==24
    previous=None
    all_summaries=[]
    for i in range(1,6):
        started=now()
        rows,health=collect(config,now=started)
        finished=dt.datetime.now(UTC)
        urls={canon_url(x.get("url","")) for x in rows if canon_url(x.get("url",""))}
        recent=0
        for x in rows:
            try:
                d=dt.datetime.fromisoformat(x["published_at"].replace("Z","+00:00"))
                if d.tzinfo and started-dt.timedelta(hours=24)<=d<=started:
                    recent+=1
            except (ValueError,TypeError,KeyError):
                continue
        item={
            "kind":"FIVE_REAL_NOW_SNAPSHOTS_NOT_OFFICIAL_CUTOFFS",
            "index":i,"expected":5,
            "started_utc":started.isoformat(),"finished_utc":finished.isoformat(),
            "original_rss_sources":24,"source_scope":"Original 24 public OPML RSS only; no paid or additional API calls",
            "collected_unique_original_urls":len(urls),"recent_24h":recent,
            "p1_gate":health.get("gate"),
            "source_health":health,
            "delta_vs_previous_real_snapshot":{
                "new_urls":len(urls-(previous or set())),
                "missing_urls":len((previous or set())-urls),
                "shared_urls":len(urls&(previous or set())),
                "first_sample_has_no_baseline":previous is None
            },
            "press_frontpage_headline_rank_proven":False,
            "claims_verified":0,"P2_EDITORIAL":"HOLD",
            "P3_REAL_DEVICE":"NOT_TESTED","release_approved":False
        }
        folder=OUT/("snapshot_%02d"%i)
        item["article_index_sha256"]=save(folder/"source_index.json",rows)
        save(folder/"capture_summary.json",item)
        all_summaries.append(item)
        save(OUT/"ROLLUP_PROGRESS.json",{
            "completed":len(all_summaries),"expected":5,"snapshots":all_summaries,
            "P2_EDITORIAL":"HOLD","P3_REAL_DEVICE":"NOT_TESTED","release_approved":False
        })
        print("REAL_RSS_CAPTURE",i,"of 5",started.isoformat(),"unique",len(urls),
              "recent24h",recent,"gate",health.get("gate"),flush=True)
        previous=urls
        if i<5: time.sleep(20)
    save(OUT/"FIVE_REAL_SNAPSHOT_ROLLUP.json",{
       "completed":5,"expected":5,
       "real_snapshot_start_times_utc":[x["started_utc"] for x in all_summaries],
       "unique_url_counts":[x["collected_unique_original_urls"] for x in all_summaries],
       "recent_24h_counts":[x["recent_24h"] for x in all_summaries],
       "source_gates":[x["p1_gate"] for x in all_summaries],
       "source_scope":"24 public OPML RSS only; excludes other free APIs intentionally to avoid rate limits",
       "not_a_substitute_for_six_approved_cutoff_captures":True,
       "no_assertion_of_front_page_headline_positions":True,
       "no_independent_fact_check":True,
       "P2_EDITORIAL":"HOLD","P3_REAL_DEVICE":"NOT_TESTED",
       "P3_TWENTY_REAL_ISSUES":"NOT_TESTED","release_approved":False
    })
    print("COMPLETED_FIVE_GENUINE_SNAPSHOTS; NO_P2_OR_P3_APPROVAL",flush=True)

if __name__=="__main__":
    run()
