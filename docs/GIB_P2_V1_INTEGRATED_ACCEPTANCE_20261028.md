# GIB P2 v1｜整合晨晚報與編輯品質單一驗收報告（2026-10-28）

> **結論：工程整合及真實來源試刊已完成；P2 新聞編輯品質尚未通過。維持 `QA HOLD`，不得啟用對外發布、正式排程、LINE、Pages 或宣稱 BOOX 驗收完成。** 本文件只記錄本輪整合及已取得的證據，不修改任何已凍結的編輯標準。

## 核准範圍與變更控制

- 依使用者 2026-10-28 核准的「GIB 整合方案 v1」執行；沒有變更 `config/frozen_contract.json`，檔案 SHA `f473ea35bb17ea0d2a356e16333f785e1802f291`，仍為 `2026-10-23-approved-v1`。
- 已將「先自行測試、整批交付、單一報告、超範圍先取得核准、嚴禁自動發布」正式寫入 `AGENTS.md` 與 `EDITORIAL_V16_IMPLEMENTATION.md`。六章節與 Essential（10–15 分鐘）／Deep Research（30–45 分鐘）的原定目標保留。
- PR #12：https://github.com/ala927832-create/global-intelligence-brief/pull/12 ，合併 commit `0816e65fd1eba1b25033c319bce1073a43efc608`。
- PR #13：https://github.com/ala927832-create/global-intelligence-brief/pull/13 ，合併 commit `a86b1606e9cd3ad5562d4272a5a8822803365c19`。因 Gemini 2.5 Flash-Lite 在真實 QA 回傳 HTTP 404，**僅內部 P2 QA** 改用 Google 公布具免費層的 `gemini-3.5-flash-lite`；原有使用者 `GEMINI_MODEL` 變數、凍結契約與生產狀態都沒有更改，並沿用既有 `GEMINI_FREE_TIER_CONFIRMED=1` 授權門檻，不啟用付費備援。
- Google 官方模型及免費層定價：https://ai.google.dev/gemini-api/docs/models 及 https://ai.google.dev/gemini-api/docs/pricing

## 整合後的實際架構

同一次 **24 路 Inoreader Free 原始發布者 RSS** 收集 → 單一可追溯 `article_index.json` 和來源健康紀錄 → 現有 `gib.newsroom_v16.canonical_issue`（同一套全球新聞重要性規則）→ 真實同日晨報及晚報 QA 底稿 → `gib.publish_v16.export` 的 Essential / Deep Research QA EPUB 與原 Style C HTML 共用同一份各期 `issue.json`。

- `qa/p2_integrated_batch.py`：一次來源快照，產生配對試刊；`run_newsroom_v16.py` 負責既有新聞編輯、Gemini 草稿、人工證據工作表與雙版輸出；`tools/gib_style_c_rc/live_html_qa.py` 只作 Style C 内容顯示，不重製排版。
- Style C 已展示原定六章節名稱及候選內容，未核實的模型分析標註 `AI EDITORIAL DRAFT · UNVERIFIED`；Deep Research 未取得支持時明確顯示 HOLD。
- 晚報讀取當日**已產生的晨報底稿**作事件比較，狀態標記 `CANDIDATES_ONLY_MATERIAL_CHANGE_UNVERIFIED`，不能把不同網址或標題直接稱為已核實重大變化。
- 2026-10-28 中午的來源快照回溯製作 **2026-10-27** 的晨晚報；這是 **backfill／QA 回放**，不是 2026-10-27 07:30、17:30 當時的真實擷取，也不是長期定時發行驗收。
- Zinc Intelligence 原始 repository 不動；工業補助／環境／鋅鋼／HDG 沒有獲得額外新聞優先級。

## GitHub 確實執行的測試

| 實際驗證項目 | 結果與證據 |
|---|---|
| 凍結契約、來源／程式回歸與跨模組整合 | **PASS**。P2 PR 最終 QA：https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40628411659 |
| 合併後原始 24 路真實新聞來源 | **PASS**，近七日 352 個去重文章網址；https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40628510755 |
| 合併後完整專案 smoke QA | **PASS**；https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40628510847 |
| 晨晚底稿、共享來源索引、Style C 同底稿對應及四份 EPUB QA 預覽 | **技術 PASS**；Run https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40628985757 ；artifact https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40628985757/artifacts/12790876110 |
| EPUB QA 離線資源、內部連結與格式基本檢查 | **技術 PASS**（既有 `scripts/check_offline_package.py`）。**不等於 W3C EPUBCheck 或 BOOX NeoReader 真機通過** |
| Gemini 免費層 API 接通與兩輪實際呼叫 | **可連線，但編輯品質 FAIL**：晨報及晚報皆為 `SECOND_PASS_NO_MATERIAL_EDIT`；第二輪未達既有實質修訂門檻，不能記作兩輪合格 |
| 當日真實晨晚編輯與深度研究完整度 | **FAIL/HOLD**：2026-10-27 回放的晨報 3 則、晚報 3 則，未達 8–12 則世界精選與 3–5 項研究分析要求。現有來源證據不足，不得補假新聞 |
| 三大頭條逐項查核、主張證據定位、獨立交叉來源、2–3 個正式深讀研究 | **FAIL/HOLD**：新聞索引及 AI 解釋仍為未核實草稿；沒有取得足夠一手事實、人工簽核與合格研究正文 |
| 10 個真實交易日 20 期及 BOOX 真機 | **尚未開始 P3**，不得宣稱任何驗收結果 |
| 正式對外發布 | **OFF**，`release_approved=false` |

## 需要修復但不得偷換標準的問題

**A. 來源時間窗與供稿完整性**：每日 RSS 會持續更新，從隔天中午抓取的單一有限 RSS 快照無法保證完整重建前一天早晚所有新聞。近七日抓取的 352 則，不等於前一天各半日的 8–12 則合格重點。實際出版時需有準時快照與新聞證據保存，但在業主未批准啟動正式排程之前不得開啟背景正式發行。

**B. Gemini 編輯**：舊 2.5 模型回傳 404 已以免費 3.5 模型處理。現在模型可以回覆兩輪，但輸出被既有「第二輪必須有實質修訂」稽核拒收。不得修改審核閾值以製造通過，也不得把缺少核實資料的短摘要延長成研究文章。

**C. 第一手證據及深讀**：需要為前三大國際新聞建立可信的一手證據位置、確切日期與數字口徑，補足來源之間的獨立性、反面證據與推翻條件，才可能有 2–3 篇真正符合標準的深度研究。不能依據 RSS 標題作自動事實確認。

**D. 圖像與閱讀**：Style C 維持原布局。舊 Wikimedia 歷史照片下載曾有一次 2/3 的非決定性失敗，後續回歸可成功，但不能當作每期新聞現場照片或已授權新聞圖像的證明。EPUBCheck、BOOX 實機長讀及使用者簽核均留待 P3。

## 本次核准的結果與下一個門檻

- **工程整合 P2 v1：已實作並通過真實執行測試。**
- **新聞編輯 P2：未通過，維持 HOLD。**
- **使用者現在無須更新 Secrets、手動按 GitHub Actions 或操作 BOOX。**
- 下一輪仍應在**原已核准的 P2 範圍內**集中修正「當日兩個真實採集窗的供稿證據、三大頭條來源核查、Gemini 第二輪實質修訂與深度研究實料」，整批自行驗收。若發現必須變更編輯契約、新增付費服務、改動發行排程或擴大功能，須**先提出具體差異並取得業主同意**。不得將 P2 技術成功當作 P3 或正式出版授權。

— QA 記錄截至 2026-10-28；無任何 AI 撰寫的未核實主張自動獲准發布。

## 2026-10-28 補充：核准範圍內第二輪 P2 內容品質檢查

**本段為同一份報告的最新驗收結果**。前面 P2 v1 初次試刊的 3 則／期、Gemini 404 和兩輪不合格，是當時歷史紀錄；以下為後續修正後的真實結果，以新 Run 為準，不刪除前次缺陷。

- 實作與 PR：https://github.com/ala927832-create/global-intelligence-brief/pull/14 （merged commit `490537b15d80ca1e06c16dd4dfcaff3677395614`）；`config/frozen_contract.json` SHA 仍為 `f473ea35bb17ea0d2a356e16333f785e1802f291`，完全不變。沒有新增來源、付費功能、正式排程或發行設定。
- 真實 P2 Run：https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40630904419 ，兩項工作均成功：完整回歸與真實 24-feed 晨晚配對 QA；GitHub artifact：https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40630904419/artifacts/12791327433 。另有主分支 repository smoke 及歷史離線 EPUBCheck Run 成功（`40630904379`、`40630904398`）。**Success 只指技術測試，並非 P2 編輯簽核。**
- **真實截稿時間已校正**：晨報 `2026-10-26 17:30→2026-10-27 07:30`、晚報 `2026-10-27 07:30→17:30`，均為 Asia/Taipei。舊程式的 07:00／17:00 屬錯誤，不是原合約。新增正式回歸斷言。
- **來源候選量與篩選結果**：24 路實際 RSS 截取 423 則去重候選；近七日 354 則。2026-10-27 的晨報出版窗 19 則新聞、選入 6 則、3 個原始發布者網域；晚報窗 43 則、選入 4 則、3 個原始發布者網域。選題由原本英文經濟詞彙偏重，補充選舉、外交、人道、災害、公衛及繁體中文重大國際新聞，但**仍未達 8–12 則全球精選或 4 個來源網域的核准標準**。
- **快照時間的不可替代限制**：來源實際取得於 2026-10-28 約 12:12（台灣），比 10/27 晨報截止晚 **1722.6 分鐘**，比晚報截止晚 **1122.6 分鐘**，分別被程式標記 `RETROSPECTIVE_SNAPSHOT_NOT_COMPLETE`。單次事後 RSS 回放不能完整證明截稿當時的新聞來源覆蓋，也不應被當成實際 07:30／17:30 發行成功。**目前不啟用任何 QA 定時背景擷取；若要新增排程，須先取得業主明確同意。**
- **頭條與事實查核**：晨晚各期的前三個事件都沒有人工簽核的可信事實主張；`independently_verified_claim_count=0`，一手原文定位與不同媒體對同一主張的實質交叉核對仍缺。只是多個網域或不同網址，不能替代獨立查核。
- **Gemini 第二輪**：使用既有已授權免費 QA 模型及沒有付費備援的兩輪流程。晨報 `REVISED_DRAFT_PENDING_REVIEW`，至少有兩個重要段落被實質編修，僅代表技術與文本修訂符合門檻；晚報仍是 `SECOND_PASS_NO_MATERIAL_EDIT`，所以不被接納。數值沒有出現在來源的事件遭檢測與警告，不能進入已核實敘述。晨報編輯通過也不代表研究主張經人工確認。
- **深度研究**：晨晚合格深度研究均為 **0 篇**，未完成兩至三篇有一手實料、歷史比較、反方證據、推翻條件、人工核實的篇章。未經審查的模型段落只可作 QA 草稿。
- **原始版面與出版界線**：Style C 仍沿用相同布局，Essential／Deep 的 QA EPUB 共用同一期 `canonical_issue`，但沒有 BOOX 真機及十交易日／20 期認證，正式發布依然是 `OFF`。所有新的可驗證欄位集中於 `P2_INTEGRATED_QA_REPORT.json` 的 `cutoff_snapshot`、`window_diagnostics`、`p2_editorial_acceptance`，可追溯缺失而不製造成功。

**總結：P2 v1 整合工程及本輪改進已完成、真正的 P2 編輯驗收未通過；不進 P3、也不要求使用者重複操作 GitHub。** 繼續改善必須遵守 `AGENTS.md` 所載原核准範圍；任何排程／版面／費用／產品方向改變，先求同意。
