# GIB V2｜2026-10-28 五次真實快照＋P3 EPUB 技術預驗｜單一驗收報告

> **結果：五次即時公開 RSS 快照成功；P3 歷史 EPUB 技術預驗成功；P2 編輯品質仍 HOLD，正式 P3 真機與 10 交易日／20 期試刊未完成，正式發刊 OFF。**

## 證據來源
- GitHub 實際 Run：[#40656990999](https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40656990999)，兩個 jobs 均 Success。
- 五次真實快照：[Artifact #12801428818](https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40656990999/artifacts/12801428818)。
- P3 歷史 EPUB 預驗：[Artifact #12803000342](https://github.com/ala927832-create/global-intelligence-brief/actions/runs/40656990999/artifacts/12803000342)。
- 兩份 artifact 保留 14 天，不應當成永久封存。

## 1. 五次即時真實採集
**依使用者本次明確要求執行，但這不是 10/29、10/30、11/02 已核准的六次 07:30／17:30 定時截稿快照。** 五次使用原有 24 路 OPML 公開原發布者 RSS。為避免重複消耗免費 API 額度，這批未呼叫 FreeNewsApi.io／GDELT／額外官方 RSS。不存在付費備援、Gemini 或對外發布。

| 快照 | 實際開始（Asia/Taipei） | 去重原文網址 | 近 24 小時文章 | 來源採集 |
|---|---|---:|---:|---|
| 1 | 2026-10-28 16:28:15 | 423 | 264 | PASS_DIRECT_RSS_DISCOVERY |
| 2 | 2026-10-28 16:28:37 | 423 | 264 | PASS_DIRECT_RSS_DISCOVERY |
| 3 | 2026-10-28 16:28:57 | 423 | 264 | PASS_DIRECT_RSS_DISCOVERY |
| 4 | 2026-10-28 16:29:18 | 423 | 264 | PASS_DIRECT_RSS_DISCOVERY |
| 5 | 2026-10-28 16:29:39 | 423 | 264 | PASS_DIRECT_RSS_DISCOVERY |

- 24 路設定來源中，19 路每輪取得有效文章；五輪皆有 352 個近七日去重文章。
- 五次資料原文網址集合相同：第二至第五輪，相對上一輪新增 0、消失 0、共同 423。
- 每輪來源故障相同：BLS Employment Situation、BLS CPI、BLS PPI 各 HTTP 403；EIA Press Releases 沒有可用文章；聯合新聞網即時列表 HTTP 403。
- OPML 四組都有近期可用來源：全球 9/9、總體金融科技 2/6、能源原料 2/3、台灣 5/6。
- **限制：** 約 84 秒連續採集只能驗證短時間穩定性；沒有重建截稿時點全球新聞，也沒有驗證媒體網站首頁頭條排名、重要性選題、具體新聞主張或人工簽核。五次成功不等於 P2 內容合格。

## 2. P3 技術預驗（不是正式 P3 驗收）
- 同一個 GitHub Run 在五次採集完成後才開始 EPUB 預驗。
- 使用既有 2026-10-23 歷史資料樣本，而非 2026-10-28 當天發行內容。
- 現有 EPUB 3 建置、離線內部連結／導航檢查成功，檢查結果 `resource_dependencies_on_network=0`，`offline_in_book_navigation=true`。
- 官方 EPUBCheck 對 `morning-essential.epub` 與 `morning-deep.epub` 均回報 **No errors or warnings detected**，共 2 份。
- **未完成：** BOOX Note Air4 C／NeoReader 真機長讀與字級確認、圖片每期真實授權確認、新 V2 晨報 30–40 分鐘／深讀 40–50 分鐘的內容長度與人工閱讀驗收、10 個真實交易日／20 期，及使用者正式發行簽核。

## 3. 下階段決策
1. 保留不變的六次指定時段暫時排程；不可用本次五個即時擷取代替，也不能另延長既有測試。
2. 真實六次資料到齊後，依 V2 頭條優先原則改善全球選題；注意「RSS 文章標題」不等於「媒體首頁頭條順位」。
3. 補齊前三大頭條的一手證據和獨立比對，完成 1–2 篇更深的研究，修正 Gemini 第二輪內容，並同步調整 P2 內仍採舊 2 篇與舊閱讀分鐘數的程式與驗收。
4. **只有 P2 正式內容驗收通過後**，再正式進入 P3 真機與 20 期試刊；本次技術預驗可沿用作基礎，但不能冒稱完整驗收。

**釋出狀態：** `OFF_UNTIL_QUALITY_AND_OWNER_APPROVAL`；Zinc Intelligence repo、既有六次快照 workflow、LINE／Pages／正式發布設定均未變動。
