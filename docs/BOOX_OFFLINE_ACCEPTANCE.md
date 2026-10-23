# BOOX Note Air4 C｜單本離線閱讀與驗收規格

**固定設計：Layout 01、繁體中文、EPUB 3（可重排），六章順序不變。**

## 一次下載的含義

- 同一期的 `morning-deep.epub` 是完整離線閱讀合輯：含 Executive Brief、The World in Brief、Essential Analysis、Deep Research（如有足夠證據）、What Changed & What to Watch，以及 Sources & Evidence。
- 在 EPUB 中從「本書閱讀路線」點選新聞，再到「事件解析」「深入研究草稿」「來源與證據」均使用 EPUB 的**內部跳轉**。正文、CSS、封面及被納入的研究圖表必須內嵌。
- 即使手機或 BOOX 完全離線，也應能閱讀所有已收錄內容。外部出版社連結仍可保留作日後核實；它們**不表示**原始網站文章已內嵌，也不保證離線可開啟。
- `morning-essential.epub` 是獨立速讀書；對希望只下載一次的人，優先使用同一期 Deep 合輯，不需再下載 Essential。
- GitHub Actions 的 Artifact 是 ZIP 容器；下載並解壓後，匯入其中的 `morning-deep.epub`。正式發布仍被鎖定，尚未有公開自動直鏈。

## 已修復的問題

Pandoc 將 HTML5 `<nav>`、`<article>` 轉換成 EPUB 3 時可能丟失自訂 `id`，造成 `href="#..."` 的書內跳轉失效。出版器改用帶 class 的 `<div id="...">` 容器以保留錨點。

本地重建的歷史試讀樣本已檢查 31 個內部連結，無斷鏈；3 張圖片內嵌，無外部媒體資源依賴。**這不是正式 BOOX NeoReader 實機測試。**

## 發布必須通過的檢查

1. `python -m unittest discover -s tests -q`：契約、新聞、數字逐事件驗證和 EPUB 導覽回歸測試。
2. `python scripts/check_offline_package.py <EPUB>`：檢查所有內部目標與外部媒體依賴。
3. `bash scripts/run_epubcheck_qa.sh <輸出目錄>`：官方 EPUBCheck 格式規範。
4. BOOX NeoReader 實機離線測試：飛航模式、字級放大、內部目錄、快訊→解析→研究→返回、圖表閱讀及註解。
5. 真實新聞與一手證據審核、Gemini 雙輪審稿，以及連續 10 個真實交易日晨晚報品質驗收；**絕不把技術測試通過當成新聞品質已達標**。

任何一步未通過，GitHub Actions 可以保留 QA Artifact，但**不得向網站或 LINE 正式發布**。原 Zinc Intelligence Repository 和排程不得修改。
