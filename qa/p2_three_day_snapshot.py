"""Owner-approved GIB P2: ONLY six scheduled public-source QA captures.

2026-10-29, 2026-10-30, 2026-11-02, Taipei 07:30 & 17:30.
A hard whitelist prevents any source capture outside these slots. Separate
self-disable runs on the last evening or any unexpectedly late invocation.
This module does not import the Gemini/editorial/EPUB/LINE/publishing stack.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests

from qa.opml_free_p1 import collect as collect_opml, validate_config
from qa.p2_source_fusion import collect_existing_free_sources, fuse_with_original_opml
from gib.editorial import canon_url
from qa.p2_content_gate import source_input_gate, eligible_source_rows, selected_story_gate
from gib.newsroom_v16 import canonical_issue

TZ = ZoneInfo("Asia/Taipei")
UTC = dt.timezone.utc
ALLOWED_DATES = frozenset({"2026-10-29", "2026-10-30", "2026-11-02"})
LAST_DAY = "2026-11-02"
SLOTS = {"morning":(7,30), "evening":(17,30)}
SCHEDULES = {"30 23 * * 0-4":"morning", "30 9 * * 1-5":"evening"}
MAX_START_LAG_MINUTES = 45
REPO = "ala927832-create/global-intelligence-brief"
WORKFLOW_FILE = "gib_p2_three_day_source_capture.yml"
OUT = Path("qa_out/p2_three_day")
SCHEMA = "GIB_P2_THREE_WORKDAY_QA_SNAPSHOT_v1"


def now_utc():
    return dt.datetime.now(UTC)


def deadline_local(day,slot):
    hour,minute = SLOTS[slot]
    return dt.datetime.combine(dt.date.fromisoformat(day),dt.time(hour,minute),TZ)


def slot_window(day,slot):
    cutoff=deadline_local(day,slot)
    if slot=="morning":
        return cutoff-dt.timedelta(hours=14),cutoff
    return cutoff-dt.timedelta(hours=10),cutoff


def plan(now,cron):
    """No work outside the approved six date/slot combinations."""
    local=now.astimezone(TZ)
    day=local.date().isoformat()
    slot=SCHEDULES.get(cron)
    active=bool(slot and day in ALLOWED_DATES)
    scheduled=deadline_local(day,slot) if slot else None
    lag=(now-scheduled.astimezone(UTC)).total_seconds()/60 if scheduled else None
    if lag is not None and lag < 0:
        active=False
    return {
        "active":active,
        "date":day,
        "slot":slot or "unknown",
        "target_local":scheduled.isoformat() if scheduled else None,
        "start_lag_minutes":round(lag,2) if lag is not None else None,
        "at_cutoff":bool(active and lag is not None and 0<=lag<=MAX_START_LAG_MINUTES),
        "terminal":bool(day>=LAST_DAY and (
            day>LAST_DAY or (slot=="evening" and local>=deadline_local(LAST_DAY,"evening")))),
        "release_approved":False,
    }


def validate_plan(now,cron):
    status=plan(now,cron)
    if not status["active"]:
        raise ValueError("UNAUTHORIZED_DATE_OR_SLOT_NO_SOURCE_CAPTURE")
    return status


def _digest(blob):
    return hashlib.sha256(blob).hexdigest()


def _artifact_api(method,path,token=None):
    token=token or os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("GITHUB_ACTIONS_TOKEN_REQUIRED_FOR_ARTIFACT_READ_OR_SHUTDOWN")
    url="https://api.github.com/repos/"+REPO+"/"+path.lstrip("/")
    response=requests.request(method,url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28"
    },timeout=(6,25),allow_redirects=True)
    response.raise_for_status()
    return response


def artifact_name(day,slot):
    if day not in ALLOWED_DATES or slot not in SLOTS:
        raise ValueError("INVALID_CAPTURE_ARTIFACT_DATE_OR_SLOT")
    return "gib-p2-source-qa-"+day+"-"+slot


def _read_artifact(day,slot):
    name=artifact_name(day,slot)
    result=_artifact_api("GET","actions/artifacts?name="+quote(name)+"&per_page=30").json()
    matches=[a for a in result.get("artifacts",[])
             if a.get("name")==name and not a.get("expired")
             and a.get("workflow_run",{}).get("head_branch")=="main"]
    matches.sort(key=lambda a:(a.get("created_at",""),a.get("id",0)),reverse=True)
    if not matches:
        return None,"MORNING_QA_ARTIFACT_NOT_FOUND"
    r=_artifact_api("GET","actions/artifacts/"+str(matches[0]["id"])+"/zip")
    z=zipfile.ZipFile(io.BytesIO(r.content))
    names=[n for n in z.namelist() if n.endswith("/snapshot_window.json") or n=="snapshot_window.json"]
    if len(names)!=1:
        return None,"MORNING_ARTIFACT_MISSING_SINGLE_WINDOW_INDEX"
    data=json.loads(z.read(names[0]))
    if data.get("schema")!=SCHEMA or data.get("date_tpe")!=day or data.get("slot")!=slot:
        return None,"MORNING_ARTIFACT_PROVENANCE_MISMATCH"
    return data,None


def _datetime(text):
    value=dt.datetime.fromisoformat(str(text).replace("Z","+00:00"))
    if value.tzinfo is None:
        raise ValueError("UNZONED_PUBLICATION")
    return value.astimezone(UTC)


def classify_window(rows,day,slot):
    start,end=slot_window(day,slot)
    window=[]
    rejected={"OUTSIDE_CUTOFF":0,"NO_VALID_PUBLICATION_DATE":0}
    for article in rows:
        try:
            published=_datetime(article.get("published_at"))
        except (ValueError,TypeError):
            rejected["NO_VALID_PUBLICATION_DATE"]+=1
            continue
        if start.astimezone(UTC) < published <= end.astimezone(UTC):
            window.append(article)
        else:
            rejected["OUTSIDE_CUTOFF"]+=1
    return window,rejected,start,end


def compare_seen_indices(morning,evening):
    """Source discovery delta, NOT independently verified event developments."""
    m={canon_url(x.get("url","")):x for x in morning if canon_url(x.get("url",""))}
    e={canon_url(x.get("url","")):x for x in evening if canon_url(x.get("url",""))}
    changed=[url for url in e.keys()&m.keys()
             if (e[url].get("title"),e[url].get("snippet"))!=
                (m[url].get("title"),m[url].get("snippet"))]
    return {
        "kind":"INDEX_DISCOVERY_DIFFERENCE_ONLY_NOT_MATERIAL_WORLD_EVENT_CHANGE",
        "newly_seen_original_urls":sorted(e.keys()-m.keys()),
        "shared_original_urls":len(e.keys()&m.keys()),
        "changed_index_text_original_urls":sorted(changed),
        "independent_claims_verified":0,
        "material_news_updates_verified":0,
    }


def execute_capture(now=None,cron=None,opml_fetcher=None,extra_fetchers=None,
                    morning_snapshot=None,out=None):
    """Capture only approved scheduled slot. Programmatic input is testable."""
    now=now or now_utc()
    status=validate_plan(now,cron or "")
    day,slot=status["date"],status["slot"]
    out=Path(out or OUT/day/slot)
    out.mkdir(parents=True,exist_ok=True)
    started=now_utc() if opml_fetcher is None else now
    opml_config=json.loads(Path("config/inoreader_free_feeds.json").read_text(encoding="utf-8"))
    if len(validate_config(opml_config))!=24:
        raise ValueError("ORIGINAL_24_OPML_INVENTORY_CHANGED")
    original,opml_health=collect_opml(opml_config,fetcher=opml_fetcher,now=started)
    provider_config=json.loads(Path("config/sources.json").read_text(encoding="utf-8"))
    # Daily budget guard for already-existing FreeNewsApi: max eight detail calls
    # per capture, not the legacy 32. No paid fallback is enabled.
    provider_config["freenews_details_daily_cap"]=8
    if opml_fetcher is None or extra_fetchers is not None:
        providers=collect_existing_free_sources(provider_config,started,fetchers=extra_fetchers)
    else:
        providers={}
    full,health=fuse_with_original_opml(original,opml_health,providers,started)
    filtered,rejected,window_start,window_end=classify_window(full,day,slot)
    completed=now_utc() if opml_fetcher is None else now
    observed_lag=(started-deadline_local(day,slot).astimezone(UTC)).total_seconds()/60
    # GitHub scheduled workflows can be late or even skipped. This is measured.
    capture_status=("AT_CUTOFF_CAPTURE_STARTED" if 0<=observed_lag<=MAX_START_LAG_MINUTES
                   else "DELAYED_QA_CAPTURE_NOT_PROOF_OF_CUTOFF_COMPLETENESS")
    prior_error=None
    prior=None
    if slot=="evening":
        if morning_snapshot is not None:
            prior=morning_snapshot
        elif opml_fetcher is None:
            try:
                prior,prior_error=_read_artifact(day,"morning")
            except (requests.RequestException,ValueError,zipfile.BadZipFile,KeyError) as exc:
                prior_error="MORNING_ARTIFACT_READ_"+type(exc).__name__
        else:
            prior_error="MORNING_FIXTURE_NOT_SUPPLIED"
    morning_delta=(compare_seen_indices(
        prior.get("rows",[]) if prior else [],filtered) if slot=="evening" and prior else None)
    if slot=="evening" and morning_delta is None:
        morning_delta={"kind":"NO_VERIFIED_SAME_DAY_MORNING_BASELINE",
                       "reason":prior_error or "MORNING_ARTIFACT_MISSING",
                       "material_news_updates_verified":0}
    # R1 evidence is computed from the SAME real, bounded index that this
    # approved six-slot workflow captured, not the later replay runner.
    # Pure source/selection QA only; NO Gemini, HTML, EPUB or extra fetches.
    r1={"scope":"MORNING_ONLY_G0_G1_READ_ONLY", "news_not_fact_verified":True,
        "release_approved":False}
    if slot=="morning":
        cutoff=deadline_local(day,slot)
        g0=source_input_gate(filtered,cutoff,"morning",observed_at=started)
        eligible,_,_,_=eligible_source_rows(filtered,cutoff,"morning")
        probe=canonical_issue(eligible,"morning",cutoff.astimezone(UTC),
                              provider_config.get("section_weights"),
                              require_material_relevance=False,tiered_v3=True)
        g1=selected_story_gate(probe)
        # On-time capture proof comes from this explicitly whitelisted job,
        # never from source_input_gate's retrospective-only field.
        r1.update({
            "g0":{k:v for k,v in g0.items() if k!="sample_event_titles"},
            "g1":g1,
            "time_gate":capture_status,
            "scheduled_date":day,
            "scheduled_slot":slot,
            "time_verified":capture_status=="AT_CUTOFF_CAPTURE_STARTED",
            "structural_pass":(capture_status=="AT_CUTOFF_CAPTURE_STARTED"
                               and not g0["blockers"] and not g1["blockers"]),
            "p2_editorial_pass":False,
        })
    snapshot={
        "schema":SCHEMA,"date_tpe":day,"slot":slot,
        "scheduled_local_cutoff":deadline_local(day,slot).isoformat(),
        "window_start_local":window_start.isoformat(),
        "window_end_local":window_end.isoformat(),
        "observed_start_utc":started.isoformat(),
        "observed_finish_utc":completed.isoformat(),
        "actual_start_delay_minutes":round(observed_lag,2),
        "time_gate":capture_status,
        "source_health":health,
        "all_unique_url_count":len(full),
        "source_window_article_count":len(filtered),
        "window_exclusions":rejected,
        "round1_source_selection_quality":r1,
        "morning_delta_provenance":prior.get("date_tpe")+"|"+prior.get("slot") if prior else None,
        "index_delta":morning_delta,
        "rows":filtered,
        "publication_status":"OFF_INTERNAL_QA_ONLY",
        "content_fact_checked":False,
        "gemini_used":False,
        "style_c_generated":False,
        "line_sent":False,
        "release_approved":False,
        "p2_editorial_approved":False,
        "p3_approved":False,
    }
    b=json.dumps(snapshot,ensure_ascii=False,indent=2).encode("utf-8")+b"\n"
    (out/"snapshot_window.json").write_bytes(b)
    (out/"source_index_all.json").write_text(
        json.dumps(full,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"source_health.json").write_text(
        json.dumps(health,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={k:v for k,v in snapshot.items() if k not in ("rows","source_health")}
    summary["snapshot_window_sha256"]=_digest(b)
    summary["original_opml_source_gate"]=health.get("original_opml_p1_gate")
    summary["external_provider_diagnostics"]=health.get("p2_external_source_fusion",{})
    summary["round1_source_selection_quality"]=r1
    summary["source_window_unique_domains"]=len({
        __import__("urllib.parse",fromlist=["urlsplit"]).urlsplit(row["url"]).hostname
        for row in filtered
    })
    (out/"capture_summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P2_CAPTURE",day,slot,capture_status,
          "OPML",len(original),"ALL",len(full),"WINDOW",len(filtered),
          "RELEASE_OFF",flush=True)
    return snapshot,summary


def three_day_rollup(today_snapshot=None):
    """Generated only after the last authorized evening, with honest missing slots."""
    summary=[]
    for day in sorted(ALLOWED_DATES):
        for slot in SLOTS:
            if (today_snapshot and today_snapshot.get("date_tpe")==day
                    and today_snapshot.get("slot")==slot):
                item=today_snapshot
                error=None
            else:
                try:
                    item,error=_read_artifact(day,slot)
                except (requests.RequestException,ValueError,zipfile.BadZipFile,KeyError) as exc:
                    item,error=None,"ARTIFACT_LOOKUP_"+type(exc).__name__
            summary.append({
                "date_tpe":day,"slot":slot,
                "state":item.get("time_gate") if item else "MISSING_OR_UNVERIFIED_CAPTURE",
                "capture_start_utc":item.get("observed_start_utc") if item else None,
                "window_articles":item.get("source_window_article_count") if item else None,
                "morning_delta":item.get("index_delta") if item and slot=="evening" else None,
                "error":error,
            })
    report={
        "kind":"GIB_P2_LIMITED_3_WORKDAY_QA_ROLLUP",
        "approved_days":sorted(ALLOWED_DATES),
        "approved_snapshots":6,
        "observed_snapshots":sum(x["state"] not in ("MISSING_OR_UNVERIFIED_CAPTURE",None)
                                 for x in summary),
        "slots":summary,
        "real_global_news_completeness_verified":False,
        "independent_headline_facts_approved":0,
        "editorial_p2_approved":False,
        "publication_status":"OFF",
        "qa_schedule_expiry":LAST_DAY+"T17:30:00+08:00",
    }
    return report


def disable_if_expired(now=None,cron=None,token=None,stopper=None):
    now=now or now_utc()
    status=plan(now,cron or "")
    if not status["terminal"]:
        return {"disabled":False,"reason":"WITHIN_APPROVED_QA_WINDOW"}
    if stopper is not None:
        stopper()
    else:
        _artifact_api("PUT","actions/workflows/"+WORKFLOW_FILE+"/disable",token=token)
    return {"disabled":True,"reason":"OWNER_APPROVED_3_DAY_QA_FINISHED","at_utc":now.isoformat()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("plan","capture","disable"))
    parser.add_argument("--cron",default=os.environ.get("GIB_SCHEDULE_CRON",""))
    args=parser.parse_args()
    current=now_utc()
    if args.command=="plan":
        status=plan(current,args.cron)
        for key,value in status.items():
            if key in ("active","terminal","at_cutoff","date","slot"):
                print(key+"="+str(value).lower() if isinstance(value,bool) else key+"="+str(value))
        print("P2_QA_PLAN",json.dumps(status,ensure_ascii=False))
    elif args.command=="capture":
        snapshot,summary=execute_capture(now=current,cron=args.cron)
        if snapshot["date_tpe"]==LAST_DAY and snapshot["slot"]=="evening":
            report=three_day_rollup(snapshot)
            file=OUT/"P2_THREE_DAY_QA_ROLLUP.json"
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("P2_ROLLUP",report["observed_snapshots"],"of 6",flush=True)
    else:
        print("P2_AUTO_STOP",json.dumps(
            disable_if_expired(now=current,cron=args.cron),ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
