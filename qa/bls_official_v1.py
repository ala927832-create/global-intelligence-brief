"""Official BLS public API v1, read-only numeric observation QA.

No registration key required; this is not a substitute for BLS news releases.
Never label observation month as the actual publication timestamp.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import requests

API_URL="https://api.bls.gov/publicAPI/v1/timeseries/data/"
SERIES={
 "CUSR0000SA0":{"label":"US CPI all items (seasonally adjusted)","unit":"index"},
 "LNS14000000":{"label":"US civilian unemployment rate (seasonally adjusted)","unit":"percent"},
 "CES0000000001":{"label":"US total nonfarm payroll employment (seasonally adjusted)","unit":"thousands"},
 "WPUFD4":{"label":"US PPI final demand (not seasonally adjusted)","unit":"index"}
}

def parse_bls_payload(data,at=None):
    at=at or dt.datetime.now(dt.timezone.utc)
    report={"source":"US Bureau of Labor Statistics Public Data API v1",
            "endpoint":API_URL,
            "checked_at_utc":at.isoformat(),
            "data_type":"MONTHLY_OBSERVATION_NOT_RELEASE_NEWS",
            "official_release_timestamp_in_api":False,
            "release_approved":False,
            "status":"INVALID_RESPONSE",
            "series":{}}
    if not isinstance(data,dict) or data.get("status")!="REQUEST_SUCCEEDED":
        report["status"]="BLS_API_NOT_SUCCESSFUL"
        return report
    results=data.get("Results",{})
    series=results.get("series") if isinstance(results,dict) else None
    if not isinstance(series,list):
        return report
    for entry in series:
        if not isinstance(entry,dict) or entry.get("seriesID") not in SERIES:
            continue
        sid=entry["seriesID"]
        observations=[]
        for row in entry.get("data",[]):
            if not isinstance(row,dict):
                continue
            year,period,value=row.get("year"),row.get("period"),row.get("value")
            if not isinstance(year,str) or not year.isdigit() or not isinstance(period,str) or period not in {
                f"M{i:02d}" for i in range(1,13)}:
                continue
            try:
                val=float(value)
                when=dt.datetime(int(year),int(period[1:]),1,tzinfo=dt.timezone.utc)
            except (TypeError,ValueError,OverflowError):
                continue
            if when>at:
                continue
            observations.append({"observation_period":f"{year}-{period[1:]}",
                                 "value":val,
                                 "footnotes":[{"code":f.get("code"),"text":f.get("text")}
                                               for f in (row.get("footnotes") or [])
                                               if isinstance(f,dict) and (f.get("code") or f.get("text"))]})
        if observations:
            latest=max(observations,key=lambda x:x["observation_period"])
            report["series"][sid]={"label":SERIES[sid]["label"],
                                    "unit":SERIES[sid]["unit"],
                                    "latest":latest,
                                    "observations_returned":len(observations)}
    missing=sorted(set(SERIES)-set(report["series"]))
    report["missing_series"]=missing
    report["status"]="OFFICIAL_SERIES_OK" if not missing else "PARTIAL_OFFICIAL_SERIES"
    return report

def fetch_bls(session=None):
    http=session or requests
    payload={"seriesid":list(SERIES)}
    try:
        response=http.post(API_URL,json=payload,timeout=(6,24),
                            headers={"Accept":"application/json","User-Agent":"GlobalIntelligenceBrief-P1-DataQA/1.0"})
        response.raise_for_status()
        data=response.json()
        return parse_bls_payload(data)
    except requests.HTTPError as exc:
        code=exc.response.status_code if exc.response is not None else 0
        return {"source":"BLS API v1","status":f"HTTP_{code}",
                "official_release_timestamp_in_api":False,"release_approved":False}
    except (requests.RequestException, ValueError) as exc:
        return {"source":"BLS API v1","status":"NETWORK_OR_PAYLOAD_"+type(exc).__name__,
                "official_release_timestamp_in_api":False,"release_approved":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="qa_out/inoreader_free_opml/bls_official_series.json")
    args=ap.parse_args()
    report=fetch_bls()
    file=Path(args.output)
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("BLS_API_V1",report["status"])
    for sid,x in report.get("series",{}).items():
        print("BLS_SERIES",sid,"period",x["latest"]["observation_period"],
              "unit",x["unit"])
    # Economic API outage remains separately visible; not an RSS news ingestion gate.
    return 0 if report["status"]=="OFFICIAL_SERIES_OK" else 2

if __name__=="__main__":
    raise SystemExit(main())
