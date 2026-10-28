# GIB × Inoreader — Integrated Editorial Pilot

## 固定執行順序（不得拆成新美編版本）

P1 **來源整合**（本 PR）：從四路已設定的 Inoreader 輸出 Feed 讀取來源、保存時間與來源索引；連線失敗即停止。

P2 **AI 編輯及 Style C 刊物**（稍後）：選題與去重、事實核對、晨晚差異、原創中文／英文內容、離線照片及 Style C HTML。

P3 **實際驗收**（最後）：獨立新聞覆蓋率、BOOX 彩色真機＋真人長讀、10 個真實交易日共 20 次晨晚試刊。

凍結：Style C 新聞首頁＋文章內頁、BOOX 彩色研究頁、HTML 優先；不做新的視覺風格、不啟用 EPUB／LINE／正式排程、不新增爬蟲或付費 Agent。

## P1 來源流

- 全球新聞：`INOREADER_GLOBAL_FEED_URL`
- 全球經濟：`INOREADER_MACRO_FEED_URL`
- 能源與商品：`INOREADER_ENERGY_COMMODITIES_FEED_URL`
- 台灣資訊：`INOREADER_TAIWAN_FEED_URL`

這四路是來源分群，不代表已完全涵蓋鋅、HDG、鋼鐵與台灣環保政策。P1 會量化來源與缺口，不將來源數量直接等同於新聞覆蓋率。

Inoreader 保留你的訂閱、監測、Rules 與標籤。轉接器只讀四路 RSS／JSON 輸出，保留原新聞網址、原標題、來源短摘要、帶時區的發布時間、取得時間與各來源輸出 SHA-256。跨來源重複網址去重，原始來源標記可追溯，所有摘要一律維持 ATTRIBUTED_UNVERIFIED，不能自動稱為已查核。

## 帳號端只需做一次的設定

1. 在 Inoreader 對全球、總經、能源商品、台灣四個來源資料夾（或標籤）分別啟用 Export，選擇 RSS 或 JSON 輸出網址。
2. 在 GitHub 專案 ala927832-create/global-intelligence-brief → Settings → Secrets and variables → Actions → New repository secret，分別建立：
   - INOREADER_GLOBAL_FEED_URL
   - INOREADER_MACRO_FEED_URL
   - INOREADER_ENERGY_COMMODITIES_FEED_URL
   - INOREADER_TAIWAN_FEED_URL

**不要將含私密識別碼的輸出網址貼到公開 Repo、Issue、CI logs 或對話**。持有網址者可讀輸出內容；若需要撤銷，關閉該標籤的 Export 並更換 Secret。

## 使用既有手動 QA（不等於發行）

到 GitHub Actions → GIB - Style C live HTML QA (manual) → Run workflow，選 source_mode=inoreader、edition=morning。晚報必須提供同一天真實晨報 Run ID。流程讀取四個 Inoreader 輸出，不回退舊 FreeNewsApi／GDELT；仍只產生帶 HOLD 標記的 issue.json、source_packet.json、qa_report.json、晨報／晚報 HTML。

**本階段完成標準：** GitHub 確實讀到全球、總經、能源商品與台灣四路 Feed，來源與日期保留下來，重複事件有標記，兩路來源數據與取得時間可核實。未設定帳號專屬輸出網址前，狀態是「轉接程式就緒／真實連線尚未驗證」，而不是已完成新聞採集。

## 限制

- Inoreader 輸出 Feed 約每 30 分鐘更新；不可假稱 07:00／17:00 截稿瞬間同步。若日後需要更即時的帳號資料，才評估 OAuth API。
- 無明確時區／發布日期、沒有真實原始網址、Feed 格式錯誤、缺少任一路 Feed，均記為失敗，不能補假新聞。
- P1 的來源候選與粗分類，不等於 P2 的新聞重要性與逐項專業核查。
- 目前保留原有人工 BOOX 驗收與正式發行 HOLD。

## Inoreader P1 URL 錯誤快速診斷（2026-10-28）

四個 Secrets **存在**只代表 GitHub 能收到非空值，不等於值是有效 RSS／JSON Export URL。

- `INOREADER_EXPORT_HTTPS_REQUIRED`：應從 Inoreader 複製以 https:// 開頭的完整輸出網址，而非 http、無協定網址或 Secret 名稱。
- `INOREADER_EXPORT_NOT_INOREADER_DOMAIN`：目前填入的不是 Inoreader 輸出網址；不可貼原本訂閱的 BBC、新聞網站 RSS 或其他工具連結。
- `INOREADER_EXPORT_EXPECTED_RSS_OR_JSON_STREAM_LINK`：目前是 Inoreader 首頁／帳號頁／資料夾 UI 頁，不是 Export 視窗內的 RSS／JSON Feed。
- `INOREADER_EXPORT_SECRET_CONTAINS_NAME_NOT_URL`：Secret Value 被填成變數名稱。
- `INOREADER_EXPORT_UNRECOGNIZED_INOREADER_HOST`：URL 使用了尚未確認的 Inoreader 子網域，不會直接放行；需回到 Export 視窗複製正確 RSS／JSON 網址。
- `VALID_URL_SHAPE`：只確認 URL 結構正確；**還沒有檢查網路連線、HTTP 回應、是否具有真實新聞內容**。

GitHub Actions 檢查時只顯示 global / macro / energy_commodities / taiwan 四個來源名稱與上述分類，不輸出任何私人網址、查詢參數、存取識別碼。若四路都顯示 VALID_URL_SHAPE 才執行真實下載。

官方做法：於 Inoreader 左側對資料夾／標籤右鍵開啟資訊，啟用 Export，從 RSS 或 JSON 的選項複製生成的完整網址，不要使用 OPML、HTML clip 或頁面網址。

## 2026-10-28 verified P1 status — blocker, no further manual reruns

**Run:** https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40618450918

Main commit: `1cacec304113a7a3e1e0c0d6c9a4ed7632bb3fd1`.
- Offline four-lane parser/normalization/fail-closed tests: **PASS**.
- Live P1 gate executed inside main-branch GitHub Actions with the **actual four existing repository Secrets**: **BLOCKED_INVALID_FEED_VALUES**.
- Global, macro, energy_commodities and taiwan: all **INOREADER_EXPORT_NOT_A_URL**, even after safe normalisation of recognised Inoreader HTTP or scheme-less links.
- Live news downloaded: **none**. Publication / editorial: **HOLD**.

Do **NOT** ask the owner to run the same QA again or describe it as a code defect. The only unsolved P1 dependency is that all four GitHub Secret **values** must be replaced with actual RSS or JSON **Export URLs** from the corresponding Inoreader folder/tag property panel (not folder labels, news-site RSS, home-page addresses, or Secret names). The owner's one consolidated correction must be completed before the next live test. Afterwards an agent may make a narrowly scoped main-branch change to trigger the automatic `GIB P1 - Live Inoreader source gate` once; it must inspect that live run and its safe report before asking the owner to do anything else. Never request or print private feed URLs in chat.

The source adapter and P1 test suite are validated; end-to-end Inoreader connection is **NOT** validated. Do not progress to P2 until all four real input feeds are fetched and original URLs/timestamps prove ingestion.
