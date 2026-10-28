# GIB V2｜Essential / Deep Research 網頁閱讀 QA 交付（2026-10-28）

**目的：** 提供先行網頁測試版讓業主審閱，僅在業主確認後才開始任何額外階段；不等於正式發行或 P2 / P3 內容驗收。

## 網頁入口（外部靜態 HTML 預覽，非 GitHub Pages 正式發刊）
- Essential: https://raw.githack.com/ala927832-create/global-intelligence-brief/main/docs/qa-web-v2/essential.html
- Deep Research: https://raw.githack.com/ala927832-create/global-intelligence-brief/main/docs/qa-web-v2/deep.html
- GitHub 原始檔：`docs/qa-web-v2/essential.html` 與 `docs/qa-web-v2/deep.html`。
- 這兩份 HTML 使用既有 Style C CSS 的內嵌內容與官方 repo 公開測試圖檔。採用 `samples/official_research_2026-10-23.json` 歷史 QA 底稿，含四項歷史議題與兩篇研究專題；不是 2026-10-28 的完整即時新聞。素材內的數值、引文尚未本輪重新核實，不能計入合格的新版 30–40 / 40–50 分鐘時長，也不算 P2 正式新聞品質達標。
- raw.githack.com 是第三方開發預覽服務，非 GitHub 官方頁面；其外部可用性未由本次工具實際驗證，故另外提供 HTML 自行開啟版作備援。正式 GitHub Pages 仍未啟用。
- 兩版包含六章節、可切換 Essential / Deep、字體放大、站內導航與可複製但不自動儲存的閱讀回饋。

## 尚未變更的來源快照設定
使用者提出「10/29、10/30、11/02 的六次截稿快照設定改變」，但未指定新的日期、時間或是否取消。因此原定三工作日六次時窗 **保持原狀**，不猜測新排程：
2026/10/29、10/30、11/02，台北時間每日 07:30 / 17:30，僅限源索引 QA。Workflow `.github/workflows/gib_p2_three_day_source_capture.yml` 檔案未修改，SHA `a483066155b02b434a091e4ff69b3f77a753bafb`。

## P4
目前 approved GIB 契約只有 P1、P2、P3 和正式發行門檻，未定義 P4 的工作範圍。使用者明確要求**網頁確認之後**才執行 P4，因此本輪不啟動或自行推定 P4 的含義，也不打開持續發行、排程、LINE、Pages 或新付費服務。

## 可供業主審閱的事項
- **Essential：** 新聞排序、標題／摘要密度、分析篇幅、來源追溯、字級與閱讀節奏。
- **Deep：** 1–2 個深入專題的論證深度、圖文貼合、歷史比較、反方證據與可推翻條件。
- **兩版：** 手機與桌面版可讀性、章節導航、文字密度；這些只是歷史樣本閱讀 QA，閱讀分鐘數需以新版真實內容另行量測。

**安全狀態：** `P2_EDITORIAL_HOLD`、`P3_REAL_DEVICE_NOT_TESTED`、`PUBLICATION_OFF`。
