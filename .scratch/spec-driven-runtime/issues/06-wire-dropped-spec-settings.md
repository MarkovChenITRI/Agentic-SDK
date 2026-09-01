# 06: 接上七項被丟掉的設定

**What to build:** 讓七項在 spec 裡通過驗證、但從來沒有生效的設定真正到達 workflow。這是本 effort 裡第一張會改變既有 agent 行為的票。

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] `gates` 的三個上限值從 spec 傳入
- [ ] `entry_module` 從 spec 傳入
- [ ] `memory.kind` 從 spec 傳入
- [ ] `plan` 的 system prompt 從 spec 傳入
- [ ] `retrieve` 的 top_k 從 spec 傳入
- [ ] `perceive` 的 importance 從 spec 傳入
- [ ] `output_format` 從 spec 傳入
- [ ] 每一項各有一個測試，透過 `build_workflow(spec, deployment)` 斷言該值確實到達 Workflow
- [ ] `gates` 會改變既有 agent 的中止時機，這件事寫進變更紀錄

## Comments

這七項現在的狀況是：spec 驗證它們、甚至夾限它們的範圍，然後執行時用的是各自的預設值。`gates` 目前一律是最多 50 次跳轉、同一模組最多 5 次、逾時 300 秒。

刻意與 03 分開，因為 03 的驗收標準是「行為完全不變」。兩件事混在一起的話，測試變紅時分不出是資料流接錯，還是某項設定生效後的正常結果。
