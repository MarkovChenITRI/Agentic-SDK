# 04: 刪掉編譯文字的讀取路徑

**What to build:** 移除從 Python 文字反推設定的整條路徑，以及所有依 spec 版本分流的判斷。這一步是 contract：確定沒有呼叫者之後才刪。

**Blocked by:** 02, 03

**Status:** done

- [x] 依 spec 版本分流的判斷全部移除
- [x] 用語法解析取得設定的模組與其全部輔助函式移除
- [x] Builder 從程式碼文字推導 spec 的相容路徑移除
- [x] 以程式碼文字為輸入的 Builder 狀態轉換函式移除
- [x] 編譯 spec 成 Python 文字的函式保留
- [x] 決定未設定時的檢索預設值，並讓 `default_spec()` 與該決定一致
- [x] 測試全綠，行為不變

## Comments

編譯函式一定要留。AI Hub 的兩支公開查詢都要求 `playground_generated_source` 非空，欄位空掉的話 agent 會從公開列表消失，公開載入回 404。

被 02 擋住的原因是：那些版本分流的判斷是唯一擋在舊 agent 前面的東西。查證沒完成就刪，等於賭生產資料裡沒有舊資料。

## 票 01 發現的新約束

刪掉 `_current_spec()` 的相容推導會**翻轉生產環境的檢索預設值**，這件事在 grilling 時沒有看到。

現況：session 被 `build_default_python_source()` 種下（八個地方），相容推導再把它轉成 spec，結果是 `KeywordRetrieve`。刪掉推導之後，沒有 spec 的 session 拿到 `default_spec()`，結果是 `PassThroughRetrieve`。

兩者行為不同。`KeywordRetrieve()` 沒有任何條目，永遠命中不了，只會把「No matching entries.」送進上下文。`PassThroughRetrieve` 把使用者輸入當作檢索內容傳下去。

證據偏向 `PassThroughRetrieve`：Builder 介面在兩條路徑上都顯示 `retrieve_policy = none`，而 `PassThroughRetrieve` 才是「不檢索」的忠實表示。但這仍然是行為改變，與本 effort「行為不變」的承諾衝突，所以要明確決定而不是讓它默默發生。

## 完成記錄

**刪除量：** `source_builder.py` 從 1677 行降到 860 行，移除 57 個定義（7 個公開、50 個私有）。`source_parser.py` 整檔刪除。

**檢索預設值的決定：** 維持 `PassThroughRetrieve`。依據是 Builder 介面在兩條路徑上都顯示 `retrieve_policy = none`，而舊路徑編譯出的 `KeywordRetrieve()` 沒有任何條目、永遠命中不了，只會把「No matching entries.」送進上下文。`PassThroughRetrieve` 才是「不檢索」的忠實表示。這個改變只影響全新 session 在使用者回答檢索問題之前的狀態；AI Hub 上 15 個 agent 全部帶自己的 spec，不受影響。

**保留的三處版本判斷不是 v1 分叉：** `routes/aihub.py` 與 `aihub_bridge.py` 的兩處是在驗證 AI Hub 回傳的酬載是不是 v2 spec，`session_spec.py` 的一處是存取器對 session 資料的守門。刪掉它們等於對外部輸入不設防。

**新增 `reset_spec()`：** 原本種新草稿的四個地方只寫 `python_source`，spec 沒有跟著建立，導致 `/start/anonymous` 之後 session 沒有 spec。改成統一走 `reset_spec()`。

**測試：** 252 passed。減少的 4 個是測試解析方向的測試（解析既有程式碼文字取得設定、events schema 的來源解析、legacy RUNNER_CONFIG 解析），該能力已隨本票移除。`test_playground_source_parser.py` 更名為 `test_playground_source_generation.py`，因為它現在只測編譯方向。

**測試假資料的更正：** 多個測試的假 AI Hub 回應只給 `python_source` 不給 `workflow_spec`。生產環境已查證全部 15 個 agent 都帶 spec，所以那些假資料不符實際，已補齊。
