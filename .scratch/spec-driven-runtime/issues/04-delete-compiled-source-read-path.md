# 04: 刪掉編譯文字的讀取路徑

**What to build:** 移除從 Python 文字反推設定的整條路徑，以及所有依 spec 版本分流的判斷。這一步是 contract：確定沒有呼叫者之後才刪。

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] 依 spec 版本分流的判斷全部移除
- [ ] 用語法解析取得設定的模組與其全部輔助函式移除
- [ ] Builder 從程式碼文字推導 spec 的相容路徑移除
- [ ] 以程式碼文字為輸入的 Builder 狀態轉換函式移除
- [ ] 編譯 spec 成 Python 文字的函式保留
- [ ] 決定未設定時的檢索預設值，並讓 `default_spec()` 與該決定一致
- [ ] 測試全綠，行為不變

## Comments

編譯函式一定要留。AI Hub 的兩支公開查詢都要求 `playground_generated_source` 非空，欄位空掉的話 agent 會從公開列表消失，公開載入回 404。

被 02 擋住的原因是：那些版本分流的判斷是唯一擋在舊 agent 前面的東西。查證沒完成就刪，等於賭生產資料裡沒有舊資料。

## 票 01 發現的新約束

刪掉 `_current_spec()` 的相容推導會**翻轉生產環境的檢索預設值**，這件事在 grilling 時沒有看到。

現況：session 被 `build_default_python_source()` 種下（八個地方），相容推導再把它轉成 spec，結果是 `KeywordRetrieve`。刪掉推導之後，沒有 spec 的 session 拿到 `default_spec()`，結果是 `PassThroughRetrieve`。

兩者行為不同。`KeywordRetrieve()` 沒有任何條目，永遠命中不了，只會把「No matching entries.」送進上下文。`PassThroughRetrieve` 把使用者輸入當作檢索內容傳下去。

證據偏向 `PassThroughRetrieve`：Builder 介面在兩條路徑上都顯示 `retrieve_policy = none`，而 `PassThroughRetrieve` 才是「不檢索」的忠實表示。但這仍然是行為改變，與本 effort「行為不變」的承諾衝突，所以要明確決定而不是讓它默默發生。
