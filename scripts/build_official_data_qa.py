"""Create reproducible, clearly unapproved two-case figure/evidence QA outputs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from gib.official_data_rebuild import build_evidence_package,read_refinery_csv,BLS_RELEASE,EIA_SOURCE

ROOT=Path(__file__).resolve().parents[1]

def build(output_dir:Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    csvpath=ROOT/"data"/"eia_wpuleus3_may_sep_2025_2026_transcribed.csv"
    info=build_evidence_package(csvpath)
    (output_dir/"source_arithmetic.json").write_text(
        json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    weekly=read_refinery_csv(csvpath)
    fig,ax=plt.subplots(figsize=(9.3,4.6))
    for year in (2025,2026):
        vals=[float(x[1]) for x in weekly[year]]
        ax.plot(range(1,23),vals,marker="o",markersize=3.5,label=str(year))
    ax.axhline(95,linestyle="--",linewidth=1,label="95% marker")
    ax.set(xlabel="Week index in May-Sep (week-ending dates)",ylabel="Utilization (%)",
           title="U.S. weekly refinery utilization | EIA WPULEUS3")
    ax.set_xlim(1,22)
    ax.set_ylim(80,100.5)
    ax.set_xticks([1,5,9,13,17,22])
    ax.grid(alpha=.25)
    ax.legend(loc="lower right")
    fig.text(.09,.01,
       "QA transcribed official weekly EIA table | vertical axis starts at 80%, not zero | unweighted means",
       fontsize=7)
    fig.tight_layout(rect=(0,.055,1,1))
    fig.savefig(output_dir/"eia_refinery_2025_vs_2026.png",dpi=170)
    plt.close(fig)

    bls=info["bls"]
    fig,ax=plt.subplots(figsize=(8.4,4.5))
    groups=("Jul 2026","Aug 2026")
    before=[bls["july_revision"]["previous"]/1000,bls["august_revision"]["previous"]/1000]
    after=[bls["july_revision"]["current"]/1000,bls["august_revision"]["current"]/1000]
    centers=(0,1)
    barw=.32
    ax.bar([x-barw/2 for x in centers],before,barw,label="Before revision")
    ax.bar([x+barw/2 for x in centers],after,barw,label="Oct 2 vintage")
    ax.axhline(0,linewidth=1)
    ax.set_xticks(centers,groups)
    ax.set_ylabel("Monthly nonfarm change (thousands of jobs)")
    ax.set_title("BLS July-August revisions | September 2026 release")
    ax.set_ylim(-35,180)
    ax.legend()
    fig.text(.09,.01,
       "QA transcription from archived Oct 2 release | Jul -31k; Aug -29k | combined -60k",
       fontsize=7)
    fig.tight_layout(rect=(0,.055,1,1))
    fig.savefig(output_dir/"bls_original_vintage_revisions.png",dpi=170)
    plt.close(fig)

    eia=info["eia"]
    report=f"""# Two primary-source statistical reconstructions | QA ONLY

**Not approved for publication.** This does not certify a 30–45 minute research article, and neither the editor nor a human reviewer has signed off.

## EIA refinery utilization

Official table: {EIA_SOURCE}

The manually transcribed EIA weekly observations, grouped by **week-ending dates in May–September**, give {eia['number_of_weeks']['2025']} records for 2025 and {eia['number_of_weeks']['2026']} for 2026.

- 2025 unweighted weekly mean: **{eia['mean_pct']['2025']}%**
- 2026 unweighted weekly mean: **{eia['mean_pct']['2026']}%**
- Change: **{eia['difference_percentage_points_2026_minus_2025']} percentage points**
- 2026 highest week: **{eia['max_2026']['utilization_pct']}%** (week ending {eia['max_2026']['week_ending']})

This checks only two seasons. The EIA article's **"highest since 1998"** is still NOT independently reconstructed from 1991–2026 history. Compare original XLS file and grouping methodology before an editor endorses it. Utilization is not absolute refinery output.

## BLS original-vintage revision reconciliation

Official immutable release: {BLS_RELEASE}

- July originally **+{bls['july_revision']['previous']:,}**, revised to **{bls['july_revision']['current']:,}**: change **{bls['july_revision']['delta']:,}** jobs.
- August originally **+{bls['august_revision']['previous']:,}**, revised to **{bls['august_revision']['current']:,}**: change **{bls['august_revision']['delta']:,}** jobs.
- Combined: **{bls['july_august_combined_revision_persons']:,}** jobs, matching the original release's statement.
- September nonfarm: **+{bls['september_nonfarm_payroll_change_persons']:,}** (establishment survey). Unemployment **{bls['september_unemployment_rate_pct']}%** (household survey).

These are distinct survey populations and initial publication vintages, not current-series estimates.

## Counter-evidence and editorial to-dos

**EIA**: test the capacity denominator effect, seasonal utilization norms, refinery outages and distillate inventories. Obtain both capacity and gross refinery input series before inferring more output. A higher ratio alone cannot prove stronger demand.

**BLS**: compare the revised July-August data with participation, hours and later payroll revisions. A single month's survey does not alone establish recession or Fed policy. Avoid comparing current revised time series to initial historical publications without a vintage label.

**Verification status:** calculations reproducible from the tracked manual snapshots, but original source-file hash, independent time-series download, cross-publisher checks, BOOX device signoff and human line-by-line attestation remain OPEN.
"""
    (output_dir/"EVIDENCE_REBUILD_QA.md").write_text(report,encoding="utf-8")
    return info

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",default="qa_outputs/official_data_figures")
    args=parser.parse_args()
    result=build(ROOT/args.output_dir)
    print(json.dumps({"status":"REBUILT_FROM_TRANSCRIBED_SOURCES_NOT_PUBLISHABLE",
       "eia_means":result["eia"]["mean_pct"],
       "bls_revision":result["bls"]["july_august_combined_revision_persons"]},
       ensure_ascii=False))
