"""Attempt an independent 1991-2026 EIA history rebuild from official PUBLIC HTML.

Unlike the 44-row manually transcribed QA CSV, this reads every weekly value
from EIA's public historical table. On network failure, reports a blocker and
never treats the EIA article's historical claim as independently confirmed.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import requests
from lxml import html as lhtml
from gib.official_data_rebuild import EIA_SOURCE

YEAR_MONTH=re.compile(r'^\s*(19\d\d|20\d\d)-([A-Za-z]{3})\s*$')
WEEK_DATE=re.compile(r'^\d{2}/\d{2}$')
MONTHS={dt.date(2000,m,1).strftime("%b").lower():m for m in range(1,13)}


def parse_history(source_html):
    root=lhtml.fromstring(source_html)
    values={}
    for tr in root.xpath("//tr"):
        texts=[' '.join("".join(td.itertext()).split()) for td in tr.xpath("./td")]
        if len(texts)<3:continue
        match=YEAR_MONTH.match(texts[0])
        if not match:continue
        year=int(match.group(1))
        month=MONTHS.get(match.group(2).lower())
        if month is None:continue
        # Official monthly rows typically have five adjacent (week-ending,value) pairs.
        for i in range(1,len(texts)-1,2):
            datestr=texts[i]
            if not WEEK_DATE.fullmatch(datestr):continue
            mm,dd=map(int,datestr.split("/"))
            if mm!=month:raise ValueError("EIA month/date mismatch")
            v=texts[i+1].replace(",","").strip()
            if not re.fullmatch(r"\d{1,3}(?:\.\d+)?",v):continue
            date=dt.date(year,mm,dd)
            val=Decimal(v)
            if date in values and values[date]!=val:raise ValueError("Conflicting EIA week")
            values[date]=val
    if len(values)<1500:raise ValueError("Unable to parse enough genuine historical weeks")
    return values


def summarize_history(values,as_of=dt.date(2026,10,24)):
    recent={day:val for day,val in values.items() if dt.date(1991,1,1)<=day<=as_of}
    summer=defaultdict(list)
    for date,value in recent.items():
        if 5<=date.month<=9:
            summer[date.year].append(value)
    if any(not summer.get(y) or len(summer[y])<18 for y in range(1991,2027)):
        raise ValueError("Missing at least one full EIA summer")
    means={year:sum(group)/len(group) for year,group in sorted(summer.items())}
    if not Decimal("95.0")<means[2026]<Decimal("96.5"):
        raise ValueError("2026 EIA output inconsistent with published statement")
    # Historical 'highest since 1998' asserts no year after 1998 beats 2026.
    highest_1999_to_2025=max((means[y],y) for y in range(1999,2026))
    confirmed=all(means[2026]>means[y] for y in range(1999,2026))
    return {
        "status":"INDEPENDENT_OFFICIAL_HTML_HISTORY_RECOMPUTED_NEEDS_EDITOR_REVIEW",
        "series":"WPULEUS3",
        "observations_total_as_of":len(recent),
        "years":len(means),
        "may_sep_avg_pct":{str(y):str(means[y].quantize(Decimal("0.01"))) for y in means},
        "methodology":"Arithmetic mean of all Friday end-date values May-Sep within each year, unweighted; not necessarily exact EIA publication algorithm",
        "matches_2026_highest_since_1998_under_this_method":confirmed,
        "highest_1999_to_2025":{"year":highest_1999_to_2025[1],"mean_pct":str(highest_1999_to_2025[0].quantize(Decimal("0.01")))},
        "human_signed":False,
        "release_approved":False
    }


def download_eia_history():
    res=requests.get(EIA_SOURCE,timeout=24,allow_redirects=False,
                     headers={"User-Agent":"GIB-Provenance-QA/1.0"})
    res.raise_for_status()
    if res.status_code!=200:raise ValueError("EIA source did not return status 200")
    if len(res.content)>1_800_000:raise ValueError("EIA official page too large")
    if "html" not in res.headers.get("Content-Type","").lower():
        raise ValueError("EIA source is not HTML")
    return res.content


def run(output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    result={"status":"OFFICIAL_HISTORY_NOT_RECONSTRUCTED","source":EIA_SOURCE,
            "human_signed":False,"release_approved":False}
    try:
        raw=download_eia_history()
        result["retrieved_source_sha256"]=hashlib.sha256(raw).hexdigest()
        weekly=parse_history(raw)
        result.update(summarize_history(weekly))
        # A separate historical graph makes the 'since 1998' test auditable.
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        means=result["may_sep_avg_pct"]
        years=sorted(map(int,means))
        fig,ax=plt.subplots(figsize=(9.2,4.5))
        ax.plot(years,[float(means[str(y)]) for y in years],marker="o",markersize=3)
        ax.scatter([1998,2026],[float(means["1998"]),float(means["2026"])])
        ax.axhline(float(means["2026"]),linestyle="--",alpha=.55)
        ax.set(xlabel="Calendar year",ylabel="May–Sep mean utilization (%)",
               title="EIA WPULEUS3 | 1991–2026 summer weekly means")
        ax.set_xlim(1991,2027)
        ax.grid(alpha=.25)
        fig.text(.08,.015,
            "QA direct official HTML time-series rebuild; arithmetic means of weekly end dates; methodology subject to review",
            fontsize=7)
        fig.tight_layout(rect=(0,.05,1,1))
        fig.savefig(out/"eia_refinery_summer_means_1991_2026.png",dpi=160)
        plt.close(fig)
        with (out/"eia_weekly_official_history.csv").open("w",encoding="utf-8") as f:
            f.write("week_ending,utilization_pct,source\n")
            for day,val in sorted(weekly.items()):
                f.write(f"{day.isoformat()},{val},{EIA_SOURCE}\n")
    except (ValueError,requests.RequestException,TypeError,KeyError) as ex:
        # Never embed web request error text (can include paths or headers).
        result["error_class"]=type(ex).__name__
        result["status"]="OFFICIAL_HISTORY_BLOCKED"
    (out/"eia_full_history_check.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report=out/"EVIDENCE_REBUILD_QA.md"
    if report.exists():
        if result.get("status")=="INDEPENDENT_OFFICIAL_HTML_HISTORY_RECOMPUTED_NEEDS_EDITOR_REVIEW":
            history_note=(
                "\n## EIA 1991–2026 direct official weekly historical rebuild\n\n"
                "The full historical comparison **has now been recomputed** from the official "
                "EIA HTML weekly table; this is distinct from the earlier 44-row transcription. "
                f"The downloaded source SHA-256 is `{result['retrieved_source_sha256']}`. "
                f"Historical summer averages: **1998 {result['may_sep_avg_pct']['1998']}%**, "
                f"**2000 {result['may_sep_avg_pct']['2000']}%**, "
                f"**2025 {result['may_sep_avg_pct']['2025']}%**, "
                f"**2026 {result['may_sep_avg_pct']['2026']}%**. "
                f"The 1999–2025 maximum was {result['highest_1999_to_2025']['year']} "
                f"({result['highest_1999_to_2025']['mean_pct']}%). "
                "The historical claim passes the unweighted weekly-year grouping test: "
                f"**{result['matches_2026_highest_since_1998_under_this_method']}**. "
                "This does **not** certify the EIA chart methodology, refinery output, "
                "diesel inventory causal claims, or signed editorial fact-checking.\n"
            )
        else:
            history_note=(
                "\n## EIA full history attempt\n\n"
                "The full official HTML history was not retrieved and parsed. "
                f"Status: {result.get('status')}; "
                "historical comparisons remain unverified by independent arithmetic.\n"
            )
        with report.open("a",encoding="utf-8") as handle:
            handle.write(history_note)
    print(json.dumps({k:v for k,v in result.items() if k not in ("may_sep_avg_pct",)},
        ensure_ascii=False))
    return result


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default="qa_outputs/official_data_figures")
    args=p.parse_args()
    run(args.output_dir)
