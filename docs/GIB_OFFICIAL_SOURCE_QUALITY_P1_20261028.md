> **編輯定位校正（2026-10-28）**：本文是上一輪**來源技術驗收紀錄**，不是 GIB 的編輯優先序或新增每日新聞版面。先前把台灣工業補助／環境法規／鋅鋼／HDG 研究列為 P0/P1，屬於助理自行延伸，**沒有使用者核准**。GIB 仍由 `config/frozen_contract.json` 已凍結的「全球新聞六章節／兩種閱讀深度」決定選題。原新增的三路產發署 RSS 已移往**輔助證據資料庫**，不再自動佔每日新聞名額；原報告內的 27 路與 355 則為當時特定 Run 的歷史事實，不是目前配置。詳見 `docs/GIB_EDITORIAL_RESTORE_20261028.md`。

# GIB P1 — 官方政策／鋅鋼／熱浸鍍鋅與 BLS 品質補強

## 本次實際改動
- 原本使用者 OPML 24 路公開 RSS 完整保留。
- 2026-10-28 經官方產業發展署 RSS 清單確認的 3 路來源新增到 `config/inoreader_free_feeds.json`：
  - 新聞發布 `https://www.ida.gov.tw/ctlr?PRO=rss.RSSView&t=1`
  - 產業發展法令規章 `https://www.ida.gov.tw/ctlr?PRO=rss.RSSView&t=2`
  - 施政措施 `https://www.ida.gov.tw/ctlr?PRO=rss.RSSView&t=8`
- 新增 `qa/bls_official_v1.py`，一次向 BLS 免註冊 Public Data API v1 查詢 CPI、非農就業人數、失業率、PPI；保留原始 `seriesID`、月份 `observation_period`、單位、註記及檢查時間。**API 的數據月份不是新聞發布時間**，也不能用來替代官方新聞稿日期。
- 更新 `.github/workflows/opml_free_source_gate.yml`，自動測試原始公開 RSS 與獨立 BLS 資料核查，後者即使 HTTP 403 也會作明確紀錄、不偽造數值或使 RSS 新聞來源 QA 成功假冒 BLS 已成功。
- 可信查核與研究來源集中於 `config/specialist_official_references.json`，不宣稱它們都是 RSS，無驗證的 HTML／PDF 來源不能當成今天新新聞。

## 可信度／取得方式分級

| 類別 | 官方核對來源 | 自動化狀態 | 使用限制 |
|---|---|---|---|
| 台灣產業／法規／施政 | 經濟部產業發展署官方 RSS | 已新增；待真實 GitHub Run 驗證 | RSS 若網站封鎖或無發布日期，原樣標記失敗 |
| 補助申請與截止日 | 經濟部補助計畫入口網／產發署電子公告 | 官方網頁人工查核清單 | 不能因公告存在推論特定工廠符合申請資格 |
| 環境／廢水／循環 | 環境部新聞與開放資料／水污染資訊 | 官方資料表與網頁查核清單 | 環保新聞資料集約 3 日更新；正式內容以環境部公告為準 |
| 鋅供需 | ILZSG Press Releases | 官方協會新聞稿查核 | 月報完整資料可能付費；新聞稿不得偽裝成完整資料庫 |
| LME 鋅價／庫存 | LME Zinc 正式報價頁 | 帶日期官方市場參考 | Official Prices／Closing Prices 必須分開記錄；不得聲稱可任意大量取用或即時 |
| 全球鋼鐵 | worldsteel Press Releases／Steel Data Viewer | 月度與展望查核清單 | 報告月份與公告日期分開 |
| HDG 技術 | American Galvanizers Association Publications | 技術研究和專家查核 | 非每日新聞；不是完整 ASTM 付費標準原文 |
| USGS 鋅供給 | USGS 2026 Mineral Commodity Summaries | 年度長期資料 | 不適合假裝成即時鋅價訊號 |
| BLS 美國 CPI／就業／PPI | BLS 公開 API v1 | 免費免註冊、已實作 API adapter，待真實 GitHub Run 驗證 | 月份數值與公告時間不可混淆；HTTP 403 不進行猜測填補 |

## 來源品質的正式驗收

1. 同一個 main 分支 Run 至少保證原有 24 路不被刪除，新增三條官方 RSS 來源狀態有逐路診斷；每條來源有 `valid_items` 和 `recent_7d`，而不是只檢查 HTTP 200。
2. BLS API 返回四個可信數值與 `seriesID` 時標記 `OFFICIAL_SERIES_OK`；其他情況標記缺少或連線限制，不可視作已通過數值管線。
3. LME／ILZSG／worldsteel／AGA 是已核對的查核入口；**尚未宣稱具備自動解析**，沒有現成無權限 RSS 的不得強行新增至新聞 Feed。
4. 台灣環保、法規及工業補助涉及適用資格、預算、截止日與修訂版本，正式影響評估需原文人工／專業核查。
5. P1 只驗收真實來源與研究資料。P2 Gemini/Style C 新聞編輯與 P3 BOOX／長期試刊仍 HOLD，不自動發送 LINE、EPUB 或正式發布。

## 依據（截至 2026-10-28）

- IDA 官方 RSS 清單：https://www.ida.gov.tw/ctlr?PRO=rss.RSSList&lang=0
- BLS v1 無需註冊：https://www.bls.gov/developers/home.htm
- BLS 免費 API 技術：https://www.bls.gov/developers/api_signature.htm
- 環境部開放資料：https://data.moenv.gov.tw/dataset/detail/MNEWS_P_01
- ILZSG：https://www.ilzsg.org/press-releases/
- LME Zinc：https://www.lme.com/en/metals/non-ferrous/lme-zinc
- worldsteel：https://worldsteel.org/media/press-releases/2026/
- AGA：https://galvanizeit.org/education-and-resources/publications

## GitHub 真實來源驗收結果（2026-10-28 台北時間）

**實際 Run：** https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40624847579

- `P1_GATE PASS_DIRECT_RSS_DISCOVERY`，共 **27** 路（原始 OPML 24＋產業發展署 3），近 7 日去重 **355** 個原始文章網址。
- 全球 9 路中近 7 日有新聞的 9 路；總經 6 路中 2 路；能源 3 路中 2 路；台灣 9 路中 7 路。
- 產發署新聞 `taiwan_ida_press`：OK，20 個有效項目，近 7 日 2 則。
- 產發署法令 `taiwan_ida_regulations`：OK，20 個有效項目，近 7 日 1 則。
- 產發署施政措施 `taiwan_ida_policy`：NO_USABLE_ARTICLES，0 個可用項目。保留來源，但未證明有有效新聞，不可誤報成功。
- BLS Public Data API v1：**OFFICIAL_SERIES_OK**，四序列皆回傳有效資料；最新觀測月份都是 **2026-09**（CPI CUSR0000SA0、失業率 LNS14000000、非農 CES0000000001、PPI WPUFD4）。這些觀測數據不是 2026-10-28 當日發布的新聞。
- 原有 BLS RSS 三路仍 HTTP 403；不是 BLS API 的失敗，不能混淆。這次可用的數值查核替代管線已完成。
- 總專案 smoke QA Run：https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40624847546 → Success。
- 真實證據 artifact：https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40624847579/artifacts/12788443725 。

**嚴格結論：** 台灣官方 RSS 與 BLS 數值管線已取得真實成功證據；ILZSG、LME、worldsteel、AGA 等專業入口屬於已核對但**尚未自動化**的查核來源。無權限的完整月報與技術標準不可宣稱可免費採集。P2／P3 發行驗收仍 HOLD。
