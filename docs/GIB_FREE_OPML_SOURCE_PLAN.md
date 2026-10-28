> **定位**：本文件是 OPML 原始訂閱清單的接入技術文件，不是 GIB 全球新聞編輯企劃。選題以已核准的 `config/frozen_contract.json` 六章節為準。

# GIB P1 — 免費 Inoreader OPML → 原始發布者 RSS

本整合基於 2026-10-28 使用者實際匯出的 OPML 訂閱清單。免費 Inoreader 的資料夾 Output Feed 回應 Pro plan required，因此**不再要求、使用或假稱**該 Export 功能可用。

## 已匯入的來源

- 01_GLOBAL_NEWS：9 路（WSJ World、CBC Top Stories、BBC World、Guardian World、BBC China、Al Jazeera、NPR、NYT、BBC News）。
- 02_MACRO_MARKETS_TECH：6 路（BBC Business、BBC Technology、Federal Reserve、BLS Employment、BLS CPI、BLS PPI）。
- 03_ENERGY_COMMODITIES：3 路（EIA Today in Energy、EIA Press、EIA Gasoline/Diesel）。
- 04_TAIWAN_POLICY：6 路（紐時中文、Engadget、聯合即時 via RSSHub、UDN 科技、鉅亨、公共電視）。

總共 24 個不重複的來源網址。來源原始資料保留於 `config/inoreader_free_feeds.json`，不需要 Inoreader 帳戶登入或 GitHub Secrets。未把 OPML 的個人帳戶名稱存進配置。

## 執行與驗收

P1 Source Gate：`.github/workflows/opml_free_source_gate.yml`。在 PR 執行 **離線**解析測試，合併到 main 時 GitHub 自動執行一次**真實**公開 RSS 下載，輸出：
- `source_health.json`：每路 HTTP／XML 狀況、有效文章數、近 7 日文章、四分組覆蓋。
- `article_index.json`：實際取得的標題、原始文章網址、已確認的帶時區發布時間、OPML 群組來源 ID、來源名稱。文章內容與新聞事實未經核實。
- 嚴格的 `PASS_DIRECT_RSS_DISCOVERY`：四分組各至少有一個近 7 日有效 Feed、合計至少 8 個來源有有效文章，去重後至少 12 則近 7 日文章。不滿足則 `PARTIAL_SOURCE_COVERAGE_REVIEW_REQUIRED`，不可稱為通過。

已設定 Style C 手動 QA `source_mode=opml` 為預設，但 P1 仍只驗證來源；不得因通過 P1 逕行發行或啟用正式推送。保留舊 Inoreader Pro-only 模式作相容性參考，不要求使用者再設四個 Secret。

## 已知內容與技術缺口

- **資料夾不是新聞版面或優先級**：使用者 OPML 的「台灣工業法規補助」是訂閱來源資料夾名稱，其中的紐時中文、Engadget 等仍屬全球／科技內容。GIB 不因資料夾名稱要求擴充台灣補助報導；主管機關公告僅在事件具有足夠新聞價值時用作證據來源。
- **能源資料的邊界**：原始 OPML 的能源群組僅有 EIA 三路，不能宣稱其已覆蓋所有世界能源與原物料市場；LME 鋅、SHFE、TC、熱浸鍍鋅／鋼鐵供需屬於獨立研究查核來源，不是 GIB 每日補齊配額或主要新聞優先級。
- 一些發布者 RSS 可能返回 403、429、重導、舊文或無時區日期；保留來源級失敗報告，不悄悄用模型產生替代新聞。
- 免費 RSS 可存索引、日期、公開原始網址與短摘要供內部編輯；不得假設擁有原文、照片的重新散布權。
- OPML 只含「訂閱來源」而非 Inoreader 已讀、收藏、標籤規則或使用者過濾後的文章流。日後新增或刪除 Inoreader 訂閱，需要重新同步清單；現階段不會自動同步帳戶。

## 固定優化規則

先實際驗證來源，再處理 P2 AI 編輯與原有 Style C HTML，最後 P3 真實 BOOX 驗收與十個交易日試刊。不要反覆要求使用者點同一個 GitHub Actions。沒有實際 Run ID、健康報告與可追溯原文連結，不能回報已完成。
