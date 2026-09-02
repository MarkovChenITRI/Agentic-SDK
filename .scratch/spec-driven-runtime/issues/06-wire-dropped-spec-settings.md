# 06: 接上七項被丟掉的設定

**What to build:** 讓七項在 spec 裡通過驗證、但從來沒有生效的設定真正到達 workflow。這是本 effort 裡第一張會改變既有 agent 行為的票。

**Blocked by:** 05

**Status:** done

- [x] `gates` 的三個上限值從 spec 傳入
- [x] `entry_module` 從 spec 傳入
- [x] `memory.kind` 從 spec 傳入
- [x] `plan` 的 system prompt 從 spec 傳入（票 03 已完成）
- [x] `retrieve` 的 top_k 從 spec 傳入（票 03 已完成）
- [x] `perceive` 的 importance 從 spec 傳入（票 03 已完成）
- [x] `output_format` — 見下方，它不是執行期設定
- [x] 每一項各有一個測試，透過 `build_workflow(spec, deployment)` 斷言該值確實到達 Workflow
- [x] `gates` 會改變既有 agent 的中止時機，這件事寫進變更紀錄

## Comments

這七項現在的狀況是：spec 驗證它們、甚至夾限它們的範圍，然後執行時用的是各自的預設值。`gates` 目前一律是最多 50 次跳轉、同一模組最多 5 次、逾時 300 秒。

刻意與 03 分開，因為 03 的驗收標準是「行為完全不變」。兩件事混在一起的話，測試變紅時分不出是資料流接錯，還是某項設定生效後的正常結果。

## 票 03 縮小了本票的範圍

`spec_to_config` 直接讀整份 spec，所以 `perceive.importance`、`retrieve.fallback`、`retrieve.top_k` 三項在票 03 就已生效，不必在這裡處理。

本票剩下四項：`gates`、`entry_module`、`memory.kind`、`output_format`。這四項要動 `build_workflow` 本身——它目前硬寫 `InContextMemory()`，也沒有把 gates 或 entry_module 傳給 `Workflow(...)`。

票 03 新增的 `test_spec_path_and_compiled_source_path_agree_except_on_dropped_settings` 用一組允許清單釘住已生效的三項。本票每接通一項，就從那個清單移除一項。

## 完成記錄

**`output_format` 從來不是執行期設定。** 它是 Builder 的選擇，`apply_builder_step` 會把它解析成 `action.module`（`GenerativeAction` 或 `ToolCallAction`）與 `action.params`。`BuilderSourceConfig` 沒有 `output_format` 這個欄位，所以沒有東西可接——它早就透過 action 模組生效了。原本把它列進七項是分類錯誤。

**實際接上三項：**

`gates` 現在從 spec 讀三個上限值，未設定時退回 SDK 的預設（50 / 5 / 300）。這會改變既有 agent 的中止時機——spec 裡存了較小值的 agent 從現在起會照那個值中止。

`entry_module` 從 spec 傳給 `Workflow`。編譯出的程式碼文字從來不輸出它，所以舊路徑一律是 `perceive`。

`memory.kind` 取代寫死的 `InContextMemory()`。未知的 kind 現在會丟 `ValueError` 而不是被默默忽略。每次執行仍然拿到自己的記憶體，兩個請求不會共用。

**測試：** 六個新測試透過 `build_workflow(spec, {})` 直接斷言，包含「未知 kind 會被拒絕」與「每次執行拿到獨立的記憶體」。全套 259 passed，與本 effort 開始前的基準線相同。
