# 02: 查證 AI Hub 沒有殘留的舊版 agent

**What to build:** 確認 AI Hub 生產資料庫裡沒有殘留的舊版 agent 設定，讓刪除舊讀取路徑成為安全動作。

**Blocked by:** 無，可立即開始

**Status:** ready-for-human

- [ ] 查詢生產資料庫的 `agent_workspace_agent` 資料表，確認 `playground_python_source` 這個欄位已經不存在
- [ ] 欄位若仍存在，回報有多少筆資料的 `playground_contract_version` 不等於 `2`
- [ ] 把結果寫進本票的 Comments

## Comments

這張票需要資料庫存取權，agent 做不到，所以標 `ready-for-human`。

判斷依據：AI Hub 有一段受保護的遷移程式，只有在沒有任何「帶著程式碼、卻不是完整 v2 紀錄」的資料時，才會刪掉那個欄位。欄位消失就代表當時的殘留數量是零。

程式碼層面的四項佐證已經確認：AI Hub 的設定載入只回得出 v2 的程式碼；非 v2 的 agent 會回報自己沒有設定；兩支公開查詢都直接把非 v2 濾掉；Playground 這端取得 spec 的函式保證 session 一定有 v2 spec。
