# 01: 把測試 fixture 遷移到 spec 路徑

**What to build:** 測試的 fixture 改用 spec 建構，斷言與行為完全不變。這一步是 expand：新的建構方式加在舊的旁邊，什麼都還沒被拿掉。它的目的是讓後續把執行層改成接收 spec 時，測試有一條可以變綠的基準線。

**Blocked by:** 無，可立即開始

**Status:** done

- [ ] 所有以程式碼文字建構的 fixture，改為先用 Builder 的逐步套用函式疊出 spec，再編譯成現有簽名需要的字串
- [ ] 測試的斷言一行未改
- [ ] 完整測試套件維持全綠
- [ ] 正式程式碼未變動，本票只動 `tests/`

## Comments

原本寫「這一步能證明兩條建構路徑產出相同的設定」。做完之後這句話不成立，實際結果如下。

**兩條路徑在未設定的檢索預設值上不一致。** 舊路徑編譯出 `KeywordRetrieve()`，spec 路徑編譯出 `PassThroughRetrieve`。使用者一旦明確選了檢索政策，兩者就一致——三種政策選項全部相同。差異只存在於使用者還沒回答之前。

**53 個 `build_source(...)` 呼叫中有 42 個沒有指定檢索政策**，所以它們的 fixture 現在使用 `PassThroughRetrieve` 而不是 `KeywordRetrieve`。測試仍然全綠，這代表沒有任何斷言依賴那個預設值，但也代表這條基準線不涵蓋檢索模組。票 03 若讓檢索模組走樣，這條基準線抓不到。

**證據顯示 spec 路徑才是對的。** Builder 介面在兩條路徑上都顯示 `retrieve_policy = none`。舊路徑卻編譯出一個沒有任何條目、永遠命中不了、只會把「No matching entries.」送進上下文的檢索模組。`PassThroughRetrieve` 才是「不檢索」的忠實表示。

**待決事項見票 04。** 生產環境目前的實際預設是 `KeywordRetrieve`，因為 session 被 `build_default_python_source()` 種下，再由相容路徑推導成 spec。票 04 刪掉那條推導之後，預設會翻成 `PassThroughRetrieve`。

## 三個遷移例外

- `test_custom_action_builder_emits_module_standard_action` 留在舊路徑，程式碼中有註解說明。custom action 只能從手寫程式碼到達：沒有任何 Builder 步驟產生它，v2 spec 的允許動作模組不含它，`spec_to_config` 把六個 `custom_*` 欄位全部寫死。它與它涵蓋的機制在票 04 一起移除。
- `test_keyword_retrieve_builder_emits_only_keyword_items_without_retrieve_fallback` 多了一個 `("retrieve_policy", "keyword")` 步驟。`apply_builder_step` 要求先設政策再設細節，舊路徑則從 payload 推斷。副作用是這個 fixture 現在也掛上了 `NextStepPlan`，舊 fixture 沒有。斷言只切 `KeywordRetrieve(` 區塊，因此不受影響。
- 一行 assert 有變動：`assert model_endpoints.normalize_endpoint_selections(build_source(), {}) == {}`。變的是內嵌在 assert 裡的 fixture 建構呼叫，期望值 `== {}` 未動。

## 未處理的既有問題

`tests/test_playground_contracts.py` 有一個互動元件的 dict literal 重複九次。這是本票之前就存在的重複，本次只是重新縮排，沒有抽成共用常數——那超出本票範圍。
