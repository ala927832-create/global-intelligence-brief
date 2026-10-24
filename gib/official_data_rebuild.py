"""Rebuild small official-data research checks without presenting them as reviewed facts.

The EIA CSV is a manually transcribed subset of an official weekly table.
It is *not* a machine-downloaded, hash-attested complete raw series.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

EIA_SERIES = "WPULEUS3"
EIA_SOURCE = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=w&n=pet&s=wpuleus3"
BLS_RELEASE = "https://www.bls.gov/news.release/archives/empsit_10022026.htm"
EIA_ARTICLE = "https://www.eia.gov/todayinenergy/detail.php?id=68344"


def read_refinery_csv(path):
    """Reject duplicates, missing weeks/units and rows outside May-September."""
    by_year=defaultdict(list)
    seen=set()
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            date=dt.date.fromisoformat(row["week_ending"])
            if not (5 <= date.month <= 9 and date.year in (2025,2026)):
                raise ValueError("Unexpected observation date")
            if row["series_id"]!=EIA_SERIES or row["source_url"]!=EIA_SOURCE:
                raise ValueError("Unexpected source or series")
            if "MANUAL_TRANSCRIPTION" not in row["transcription_status"]:
                raise ValueError("Missing transparency label")
            if date in seen:
                raise ValueError("Duplicate week")
            seen.add(date)
            try:
                val=Decimal(row["utilization_pct"])
            except InvalidOperation as exc:
                raise ValueError("Invalid utilization percentage") from exc
            if not val.is_finite() or not Decimal("0") <= val <= Decimal("110"):
                raise ValueError("Invalid percentage range")
            if date.weekday()!=4:
                raise ValueError("EIA weekly ending dates should be Fridays")
            by_year[date.year].append((date,val))
    if set(by_year)!={2025,2026} or any(len(obs)!=22 for obs in by_year.values()):
        raise ValueError("Expected precisely 22 May-September observations per year")
    for values in by_year.values():
        values.sort()
        if any((b[0]-a[0]).days!=7 for a,b in zip(values,values[1:])):
            raise ValueError("Series has a missing or nonweekly entry")
    return by_year


def rebuild_refinery(path):
    rows=read_refinery_csv(path)
    averages={year:sum((val for _,val in entries),Decimal("0"))/len(entries)
              for year,entries in rows.items()}
    delta=averages[2026]-averages[2025]
    def round2(num):
        return str(num.quantize(Decimal("0.01")))
    return {
        "status":"REPRODUCED_FROM_MANUAL_OFFICIAL_TABLE_TRANSCRIPTION_NOT_FULL_HISTORY",
        "series_id":EIA_SERIES,
        "statistic":"arithmetic mean of weekly end-date observations, May-Sep",
        "source":EIA_SOURCE,
        "comparison_article":EIA_ARTICLE,
        "number_of_weeks":{str(year):len(v) for year,v in rows.items()},
        "mean_pct":{str(year):round2(v) for year,v in averages.items()},
        "difference_percentage_points_2026_minus_2025":round2(delta),
        "max_2026":{"week_ending":max(rows[2026],key=lambda x:x[1])[0].isoformat(),
                    "utilization_pct":str(max(rows[2026],key=lambda x:x[1])[1])},
        "matches_eia_claim_2026_above_95_pct":averages[2026]>95,
        "proves_highest_since_1998":False,
        "human_signed":False,
        "limitations":[
            "EIA weekly table manually transcribed; compare against official XLS before attestation",
            "Comparison is 2026 against 2025 only, not every year since 1998",
            "Weekly end-date grouping, unweighted; may differ from source seasonal methodology",
            "Utilization percentage is not refinery absolute output, margins or diesel prices"
        ]
    }


def rebuild_bls_revision():
    """Arithmetic from October 2, 2026 BLS archived September employment report."""
    july_old=21000
    july_new=-10000
    aug_old=162000
    aug_new=133000
    july_diff=july_new-july_old
    aug_diff=aug_new-aug_old
    combined=july_diff+aug_diff
    return {
      "status":"ARITHMETIC_REBUILT_FROM_ARCHIVED_RELEASE_MANUAL_TRANSCRIPTION",
      "release_date":"2026-10-02",
      "reference_month":"2026-09",
      "source":BLS_RELEASE,
      "september_nonfarm_payroll_change_persons":29000,
      "september_unemployment_rate_pct":"4.2",
      "july_revision":{"previous":july_old,"current":july_new,"delta":july_diff},
      "august_revision":{"previous":aug_old,"current":aug_new,"delta":aug_diff},
      "july_august_combined_revision_persons":combined,
      "matches_bls_stated_combined_revision":combined==-60000,
      "september_private_hourly_earnings_usd":"37.81",
      "september_private_average_workweek_hours":"34.4",
      "survey_distinction":"Payroll changes are establishment survey; unemployment rate is household survey",
      "source_as_of":"Initial October 2, 2026 report, not latest revised monthly series",
      "human_signed":False,
      "limitations":[
          "BLS date-specific archive, not later revised time series",
          "JEC secondary reporting is not independent original survey measurement",
          "No inference about the next Federal Reserve decision from this report alone"
      ]
    }


def build_evidence_package(eia_path):
    return {
      "kind":"GIB_TWO_OFFICIAL_CASE_REBUILD_QA",
      "release_approved":False,
      "approval_status":"HUMAN_FACT_CHECK_AND_BO0X_REVIEW_REQUIRED",
      "eia":rebuild_refinery(eia_path),
      "bls":rebuild_bls_revision(),
      "editorial_gates":{
          "matched_full_1991_2026_eia_history":False,
          "official_xls_source_digest_recorded":False,
          "bls_later_revision_series_compared":False,
          "human_reviewer_signed":False,
          "unverified_causal_chain_can_publish":False
      }
    }


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="qa_outputs/official_two_case_rebuild.json")
    args=ap.parse_args()
    path=root/"data"/"eia_wpuleus3_may_sep_2025_2026_transcribed.csv"
    result=build_evidence_package(path)
    output=root/args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"qa_file":str(output),
                      "eia_mean_pct":result["eia"]["mean_pct"],
                      "bls_revision_persons":result["bls"]["july_august_combined_revision_persons"],
                      "human_signed":result["eia"]["human_signed"]},ensure_ascii=False))
