"""P2 numeric gate: read dated, official EIA Brent/WTI XLS, no substitute quotes.
QA-only, no published price chart until source checks pass.
"""
import io,json,requests,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path("qa_out/visual_p2");ROOT.mkdir(parents=True,exist_ok=True)
result={"B_official_source_gate":"HOLD","series":{},"cutoff":"2026-10-30","publication":"OFF"}
try:
    merged={}
    for label,ticker in (("Brent","RBRTE"),("WTI","RWTC")):
        url="https://www.eia.gov/dnav/pet/hist_xls/"+ticker+"d.xls"
        resp=requests.get(url,headers={"User-Agent":"GIB-offline-visual-qa/1.0"},timeout=(15,60))
        resp.raise_for_status()
        table=pd.read_excel(io.BytesIO(resp.content),sheet_name="Data 1",header=None)
        records=[]
        for row in table.itertuples(index=False,name=None):
            if len(row)<2:continue
            date=pd.to_datetime(row[0],errors="coerce")
            try:value=float(row[1])
            except(TypeError,ValueError):continue
            if pd.notna(date) and "2026-10-01"<=date.strftime("%Y-%m-%d")<="2026-10-30":
                records.append({"date":date.strftime("%Y-%m-%d"),"value":value})
        if len(records)<14:raise ValueError("NOT_ENOUGH_LIVE_EIA_OBSERVATIONS_"+ticker)
        merged[label]=records
        result["series"][ticker]={"url":url,"file_sha256":hashlib.sha256(resp.content).hexdigest(),
                  "n":len(records),"last_date":records[-1]["date"],"last_value":records[-1]["value"]}
    common=sorted(set(x["date"] for x in merged["Brent"]) & set(x["date"] for x in merged["WTI"]))
    if len(common)<14:raise ValueError("TOO_FEW_MATCHED_OBSERVATIONS")
    result["B_official_source_gate"]="PASS"
    result["common_dates"]=len(common)
    (ROOT/"B_brent_wti_eia_official.json").write_text(json.dumps({"series":merged,"audit":result},indent=2))
except Exception as e:
    result["error_type"]=type(e).__name__
    result["error_summary"]=str(e)[:180]
(ROOT/"B_source_audit.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
if result["B_official_source_gate"]!="PASS":
    raise SystemExit("B_OFFICIAL_EIA_DATA_HOLD_NO_CHART")
