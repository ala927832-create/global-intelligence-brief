"""Reproducible illustrated, still-UNAPPROVED BOOX research book from official samples.

This is an evidence-based offline reading QA artifact, not a live newspaper.
It never calls Gemini or imports/reproduces copyrighted news articles.
"""
from __future__ import annotations

import argparse
import json
import shutil
from decimal import Decimal
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gib.official_data_rebuild import build_evidence_package, EIA_ARTICLE, EIA_SOURCE, BLS_RELEASE
from gib.publish_v16 import export
from scripts.build_official_data_qa import build as build_charts

ROOT=Path(__file__).resolve().parents[1]
FIGURES=ROOT/"assets"/"editorial"/"qa_official_figures"


def load_counterdata():
    bls=json.loads((ROOT/"data"/"bls_september_2026_household_counterevidence.json").read_text("utf-8"))
    eia=json.loads((ROOT/"data"/"eia_20260828_capacity_denominator_example.json").read_text("utf-8"))
    if bls["source"]!=BLS_RELEASE or eia["source"]!="https://www.eia.gov/dnav/pet/pet_pnp_wiup_dcu_nus_w.htm":
        raise ValueError("Counterevidence source mismatch")
    before,after=bls["august_2026"],bls["september_2026"]
    changes={key:after[key]-before[key] for key in
             ("civilian_labor_force_thousands","employed_thousands","unemployed_thousands")}
    if changes!={"civilian_labor_force_thousands":485,"employed_thousands":406,
                 "unemployed_thousands":78}:
        raise ValueError("BLS original-vintage values inconsistent")
    if after["participation_pct"]-before["participation_pct"]!=0.2:
        # Avoid float equality problems and never round away a mismatch.
        if Decimal(str(after["participation_pct"]))-Decimal(str(before["participation_pct"]))!=Decimal("0.2"):
            raise ValueError("BLS participation arithmetic mismatch")
    if round(100*eia["gross_inputs_thousand_bpd"]/eia["operable_capacity_thousand_bpd"],1)!=eia["official_utilization_pct"]:
        raise ValueError("EIA gross/capacity consistency mismatch")
    return bls,eia,changes


def household_figure(out):
    bls,eia,changes=load_counterdata()
    names=["Labour force","Employed","Unemployed"]
    values=[changes[x] for x in ("civilian_labor_force_thousands","employed_thousands","unemployed_thousands")]
    fig,ax=plt.subplots(figsize=(8.3,4.7))
    ax.bar(names,values)
    for i,val in enumerate(values):
        ax.text(i,val+10,f"+{val:,}k",ha="center",fontsize=10)
    ax.set(title="U.S. household survey | Aug to Sep 2026",ylabel="Monthly difference (thousands of persons)",ylim=(0,540))
    ax.grid(axis="y",alpha=.2)
    fig.text(.06,.01,"BLS 2026-10-02 initial release, Summary table A | household survey only",fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1))
    filename=out/"bls_household_counter_evidence.png"
    fig.savefig(filename,dpi=170)
    plt.close(fig)
    return filename


def _figure(filename,title,caption):
    return {"file":"qa_official_figures/"+filename,"title":title,"caption":caption}


def two_study_sections(arith,history,bls_counter,eia_counter,changes):
    av=arith["eia"]["mean_pct"]
    gain=arith["eia"]["difference_percentage_points_2026_minus_2025"]
    historical_ok=history.get("status")=="INDEPENDENT_OFFICIAL_HTML_HISTORY_RECOMPUTED_NEEDS_EDITOR_REVIEW"
    historical_note=(
        "全史來源直接重新下載 EIA 官方歷史表，以 1991–2026 年所有週末日期落在 5 至 9 月的觀測"
        "計算算術平均；得到 1998 年 {a}%、2026 年 {b}%。在同一公式下，"
        "2026 年高於 1999–2025 的所有年度。此計算僅重建歷史排序，"
        "EIA 圖表的原始加權、資料修訂時點仍需人工比對。".format(
             a=history["may_sep_avg_pct"]["1998"],b=history["may_sep_avg_pct"]["2026"])
        if historical_ok else
        "當次無法完整擷取 EIA 1991–2026 官方歷史表，因此暫時只能展示"
        "2025 和 2026 的 44 筆轉錄觀測；1998 年以來最高這項主張尚未完成獨立歷史重算。"
    )
    eia_sections=[
        {"heading":"研究定位：比率上升不等於總產量上升",
         "body":"EIA 在 2026 年 10 月 22 日的官方分析稱，美國煉油廠 2026 年 5–9 月平均產能利用率超過 95%，是同一期間自 1998 年以來最高。必須先辨認指標本身：利用率分子是煉油投入量，分母是可運轉產能；這與單純計算原油進廠總量或柴油產量並不相同。2026 年開工率偏高值得研究，但不代表全部的用油需求、企業獲利或價格都出現相同比例的增長。發行前須逐一確認原始資料頻率、季節分組及修訂版本。"},
        {"heading":"官方週資料的同口徑重建",
         "body":f"將 EIA WPULEUS3 每週利用率依『週結束日在 5–9 月』分類，2025 年平均 {av['2025']}%，2026 年平均 {av['2026']}%，變化 {gain} 個百分點。此為直接以百分率取算術平均，並未按各週原油加工量或產能加權；因此必須標示分析方法，而不是將結果當成 EIA 已簽核的精確重算。圖上每個點是一週資料，90% 上下的週次、夏季的高點、與 95% 水準線，都可由原始 CSV 再計算。",
         "figure":_figure("eia_refinery_2025_vs_2026.png","EIA 2025 與 2026 煉油利用率週序列","每年 22 週，端點日期位於 5–9 月；橫軸為週次，非完全相同的日曆週。2025/2026 算術平均：{0}%／{1}%。".format(av["2025"],av["2026"]))},
        {"heading":"1998 年歷史主張如何核對",
         "body":historical_note,
         **({"figure":_figure("eia_refinery_summer_means_1991_2026.png","1991–2026 歷史夏季利用率比較","全史圖以官方週表機器擷取重算；『2026 為 1998 年以來最高』以相同算式評估。") } if historical_ok else {})},
        {"heading":"第一個反證：產能分母效應",
         "body":f"EIA 另一份官方『Weekly Inputs & Utilization』在 2026-08-28 的數值為每日本期總投入 {eia_counter['gross_inputs_thousand_bpd']:,} 千桶、可運轉產能 {eia_counter['operable_capacity_thousand_bpd']:,} 千桶，兩者比值約 {eia_counter['official_utilization_pct']}%。這只能重建該週比率，不能從一個星期證明 2019 年後的產能下滑幅度。官方 10 月文章另稱 2019 年後產能約減少 4%；要分辨高比率究竟來自分子增加或分母縮小，仍須再取兩期完整加工量與可運轉產能。若分母下降，類似投入量也可能產生更高利用率。"},
        {"heading":"第二個反證：季節性及庫存可能反向移動",
         "body":"EIA 官方文章寫明，煉油廠通常在 5–9 月維持較高利用率以供應夏季汽油需求；1991 年以來這五個月的歷史均值約 92%，其他七個月約 88%。2026 年較高的開工率不能直接和全年均值相比。EIA 2026 年 10 月 5 日的另一份季度分析指出，截至 9 月 25 日，蒸餾油庫存約低於 2021–2025 同週平均 13%，它支持當時庫存相對偏緊的方向，但仍不足以獨立證明所有開工率變化都是全球供給導致。該文所用油品煉製利差圖表來源包含 Bloomberg，若無使用授權與可重算數據，應保留為具來源標示的官方敘述，不重製該商業圖表。"},
        {"heading":"因果鏈與可能推翻的條件",
         "body":"目前可檢查的假說是：全球油品需求和供應變動，可能提高柴油等產品利差；若利差提高，煉油廠有誘因增加投入，隨後影響成品油供應和庫存。這串機制不是從一個利用率數字就可以全部推得。最有力的反方檢查是對照可運轉產能、原油實際投入量、蒸餾油庫存、產品出口量及季節調整後的需求。如果開工率偏高卻沒有對應投入與出口改善，或庫存快速回補，應下修『緊供給推動』的解釋力。沒有零售和成本資料，不應宣稱工業品價格必然上升。"},
        {"heading":"資料來源、人工審稿缺口與下一期追蹤",
         "body":"資料來源：EIA Today in Energy 2026-10-22、同機構 2026-10-05 季度文章、WPULEUS3 官方週歷史表與 Weekly Inputs & Utilization。EIA 同一機構的多份文件可交叉檢查口徑，但不是來自獨立機構的多套統計。研究者應簽核是否採用週末月份分組、是否重算歷史修訂與能否支持因果。下期逐一追蹤官方庫存與總投入量；在具名簽核前僅為 QA 研究，不能公開發行。"}
    ]
    b=arith["bls"]
    bls_sections=[
        {"heading":"研究定位：兩個調查不能混成一個訊號",
         "body":"2026 年 10 月 2 日 BLS 固定封存版的 9 月就業報告，企業調查顯示非農職位月增 29,000，家庭調查則記錄失業率 4.2%。前者抽樣雇主報告的職位、工時與薪酬，後者衡量人口的就業、失業及勞動參與情況。兩份調查的樣本、單位與誤差不同，所以不能把 +29,000 當成失業率變動的直接分子。本文僅研究發布當日的數據版本，後續修訂不得悄悄覆蓋原始資料。"},
        {"heading":"官方修訂的可重現算式",
         "body":"7 月原估就業增加 21,000，10 月 2 日版本改為減少 10,000，修訂為 -31,000；8 月原估增加 162,000，改為增加 133,000，修訂為 -29,000。兩月合計 -60,000，與 BLS 官方當日文字一致。圖表保留修訂前後數值及負值零線；讀者應區分『7 月修訂後為負』、『修訂總量為負』與『9 月非農仍新增 29,000』這三個不同的概念。",
         "figure":_figure("bls_original_vintage_revisions.png","BLS 7–8 月前值與後來修訂值","2026-10-02 固定發布版本；直條單位為千人，負值保留，不能當成當日最新修訂。")},
        {"heading":"反方數據：家庭就業上升與失業率同時上升",
         "body":f"BLS 家庭調查 A-1 表顯示，2026 年 8–9 月勞動力由 169,777 千人升至 170,262 千人，增加 {changes['civilian_labor_force_thousands']:,} 千人；就業人數由 162,746 升至 163,152 千人，增加 {changes['employed_thousands']:,} 千人；失業人數由 7,031 升至 7,109 千人，增加 {changes['unemployed_thousands']:,} 千人。同期勞動參與率由 61.6% 升至 61.8%，失業率則由 4.1% 升至 4.2%。因此『失業率上升』並不必然與『有人重新加入勞動市場且就業同時上升』矛盾。這是對簡化衰退敘事的重要限制，不能把兩個調查的總人數直接相減。",
         "figure":_figure("bls_household_counter_evidence.png","家庭調查：勞動力、就業及失業人數月變動","BLS A-1 表，同一家庭調查：+485、+406、+78 千人；分項因四捨五入可能不完全相加。")},
        {"heading":"工資與工時：避免過度推斷需求崩落",
         "body":"BLS 同一固定發布版本顯示，私人部門平均時薪 37.81 美元，月增約 0.1%，私人非農平均工時約 34.4 小時。這些觀察只能補充就業結構，不代表所有人實質薪資改善，因為實質購買力還取決於物價、工時及收入分布。若要判斷需求減弱，需要進一步核對經通膨調整的薪資、零售與服務消費、工時及職缺等資料。不能用一個月的報告，直接推定景氣衰退已發生或聯準會必將調整利率。"},
        {"heading":"調查方法、抽樣誤差與對立解釋",
         "body":"第一種解釋是企業招聘減速，與企業樣本的 9 月淨新增數較低以及 7–8 月下修一致。第二種解釋是勞動供給變化及調查波動，家庭調查在同一個月同時呈現勞動力與就業增加，故不能只用失業率上升判定整體勞動市場單向惡化。第三種方法風險是：BLS 就業數會因後續回報及季節因素重新估計。審稿人應分別為企業與家庭調查登錄每個表格和參照期間，避免同一統計被當成兩個獨立證據源。"},
        {"heading":"推翻條件與編輯必查",
         "body":"BLS 已將 2026 年 10 月就業報告排定於 11 月 6 日發布。下一版資料若上修 7–9 月企業就業數、工時改善且家庭調查就業持續增加，單月新增偏低的衰退推論將被削弱。相反地，如果後續招聘、工時及家庭調查的就業也持續惡化，才可能提高勞動市場走弱的證據強度。具名編輯仍須檢查定義、當期發布時間、修訂版本和來源計算，並明確標記哪些只是研究假說。"}
    ]
    return [
        {"event_id":"eia_refinery_20261022","title":"美國煉油廠高利用率：強勁需求、產能縮減，還是季節性？","sections":eia_sections},
        {"event_id":"bls_employment_20261002","title":"美國九月就業：企業調查放緩，家庭調查卻呈現勞動力增加","sections":bls_sections}
    ]


def build(output_dir:Path):
    output_dir.mkdir(parents=True,exist_ok=True)
    figures=output_dir/"figures"
    build_charts(figures)
    # Reuse the separately downloaded full official source data and its chart.
    # Never fake a historical graph when retrieval is blocked.
    primary_figures=ROOT/"qa_outputs"/"official_data_figures"
    for name in ("eia_full_history_check.json","eia_refinery_summer_means_1991_2026.png",
                 "eia_weekly_official_history.csv"):
        source=primary_figures/name
        if source.is_file():
            shutil.copy2(source,figures/name)
    historical_path=figures/"eia_full_history_check.json"
    if historical_path.is_file():
        history=json.loads(historical_path.read_text("utf-8"))
    else:
        history={"status":"OFFICIAL_HISTORY_NOT_RECONSTRUCTED"}
    bls,eia,changes=load_counterdata()
    household_figure(figures)
    if history.get("status")=="INDEPENDENT_OFFICIAL_HTML_HISTORY_RECOMPUTED_NEEDS_EDITOR_REVIEW":
        if not (figures/"eia_refinery_summer_means_1991_2026.png").is_file():
            raise RuntimeError("Official historical status requires chart")
    FIGURES.mkdir(parents=True,exist_ok=True)
    for path in figures.glob("*.png"):
        shutil.copy2(path,FIGURES/path.name)
    packet=json.loads((ROOT/"samples"/"official_two_case_20261024.json").read_text("utf-8"))
    stats=build_evidence_package(ROOT/"data"/"eia_wpuleus3_may_sep_2025_2026_transcribed.csv")
    packet["deep_research"]=two_study_sections(stats,history,bls,eia,changes)
    packet["editorial_status"]="REVIEW_REQUIRED"
    packet["publication_approved"]=False
    packet["human_signed"]=False
    packet["reader_time_verified"]=False
    packet["source_health"]["collector_errors"]=[]
    packet["source_health"]["research_qa_not_live_news"]=True
    packet["research_dossiers"]=[]
    packet["upcoming_events"]=[]
    # Distinguish supporting evidence from the featured articles' index links.
    packet["research_source_manifest"]=[
        {"source":EIA_SOURCE,"kind":"weekly historical table"},
        {"source":EIA_ARTICLE,"kind":"primary interpretive article"},
        {"source":"https://www.eia.gov/todayinenergy/detail.php?id=68245","kind":"EIA second analysis, same institution"},
        {"source":eia["source"],"kind":"gross inputs/capacity weekly snapshot"},
        {"source":BLS_RELEASE,"kind":"BLS immutable monthly release"},
    ]
    (output_dir/"ILLUSTRATED_ISSUE_QA.json").write_text(
        json.dumps(packet,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    book=export(packet,[],output_dir,qa_only=True)
    from scripts.check_offline_package import inspect
    audit=inspect(book["deep"]["epub"])
    if audit["issues"] or audit["embedded_images"]<4:
        raise RuntimeError("Reader book is missing embedded research figures")
    result={"status":"ILLUSTRATED_QA_ONLY_NOT_PUBLISHED","issue":book,
            "embedded_images_deep":audit["embedded_images"],
            "human_signed":False,"reading_time_verified":False,"release_approved":False,
            "historical_data_available":history.get("status")==
                   "INDEPENDENT_OFFICIAL_HTML_HISTORY_RECOMPUTED_NEEDS_EDITOR_REVIEW"}
    (output_dir/"ILLUSTRATED_READER_QA.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="qa_outputs/illustrated_studies")
    a=ap.parse_args()
    build(ROOT/a.output_dir)
