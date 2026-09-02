# 02: 記憶類型的第二個選項是空的

**What to build:** Builder 的記憶類型選項，選了之後要嘛真的改變行為，要嘛不要出現在畫面上。

**Blocked by:** 無，可立即開始

**Status:** needs-triage

- [ ] 待評估

## Comments

Builder 的 `memory_type` 提供兩個選項：`in_context` 與 `workflow_recall_preview`。但 spec 的允許清單 `_ALLOWED_MEMORY_KINDS` 只有 `in_context`。

選了 `workflow_recall_preview` 之後：spec 把它強制轉回 `in_context`，表單回讀也顯示 `in_context`。**使用者的選擇連視覺上都留不住**，而且沒有任何訊息說明發生了什麼。

實測（2026-09-02）：兩個選項組出來的模組完全相同，對話輸出也完全相同。

## 缺的評估：這是未完成的功能，還是該移除的殘留

選項名稱帶著 `preview`，看起來是有人打算做「跨執行期回憶」但沒做完。SDK 那一側其實有 `PersistentMemory` 與 `InMemoryStore.search()`，所以底層能力存在，缺的是 Playground 這一端接上去。

**要決定的是：**

1. **接上去。** `_ALLOWED_MEMORY_KINDS` 加一個 kind，`build_workflow` 的 `_MEMORY_KINDS` 對應到 `InMemoryStore`。SDK 側已經有東西可以接。
2. **移除選項。** 從 `get_builder_steps` 拿掉，等真的要做再加回來。

在決定之前，現況是最差的：使用者看得到、選得到、什麼都不會發生。
