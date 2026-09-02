# 01: 畫廊分享出去的 Agent，答題時沒有自己的文件

**What to build:** 匿名點開畫廊裡的 Agent 時，它要嘛拿得到自己的參考文件，要嘛老實說拿不到。

**Blocked by:** 取得文件那半需要 AI Hub 端的變更，見下。

**Status:** ready-for-human

- [x] 失敗訊息不再假設使用者在賣東西
- [x] 分不出「查不到」與「根本沒有文件可查」時，不要說成前者
- [ ] AI Hub 端開放公開 agent 的 bundle 取得路徑（不在本 repo）

## 使用者遭遇的事

從 `https://ai-hub-portal.azurewebsites.net/gallery` 匿名點進公開的 Agent，點它自己的預設問題。畫廊公開六個，實測結果：

```
LaNew鞋墊顧問     aborted   SemanticRetrieve 沒有命中
用藥指導Chatbot    aborted   SemanticRetrieve 沒有命中
Timothy（傷口照護） aborted   SemanticRetrieve 沒有命中
腎臟科衛教chatbot   completed plan 跳過檢索
CMP-RAGdirty     completed 「沒有命中任何條目。」
CMP智慧工廠        completed 「沒有命中任何條目。」
```

三個 abort 的都回同一句：

> 目前沒有找到可支持這項決策的**產品資料**。已停止推薦與下一步送出，請交由服務人員人工確認產品資料、**庫存**與適用條件。

傷口照護的 Agent 和用藥指導的 Agent，跟使用者談庫存。

## 兩層原因

**一、匿名路徑從來不還原知識庫。** `aihub_bridge.start_runner_bridge_session` 的 `edit` 分支載入設定後會呼叫 `_restore_selected_agent_bundle`；`read` 分支沒有。那個函式要 credentials，匿名沒有。所以公開分享的語意 Agent，索引永遠是空的。

實測 AI Hub 端：

```
POST /api/playground/agents/{id}/config/public/load   200   （帶 Origin，不需登入）
GET  /api/playground/agents/{id}/bundle/load          400   AGENT_PLAYGROUND_CREDENTIALS_REQUIRED
```

有公開的設定端點，**沒有公開的 bundle 端點**。

**二、失敗訊息是為零售場景寫死的。** `_human_handoff_reason` 對任何「EvidenceCheckReflect + on_failure=end 且檢索沒命中」的 Agent，一律回「沒有找到可支持這項決策的產品資料」。Agent 在做什麼它不看。

## 一個可以判斷的區別

`SemanticRetrieve` 的 FAISS 檢索**沒有分數門檻**：只要索引裡有東西，top-k 一定回傳至少一筆。所以「宣告了 support_files 但命中數是 0」只有一個解釋——文件根本沒載進來，不是查不到。

這讓訊息可以說實話，而不是把「文件沒載入」講成「資料裡沒有」。

## 這張票在本 repo 能做完的部分

改訊息：不再假設零售場景，並且在文件沒載入時據實說明。這改變使用者看到的字，不會讓錯誤的答案變成對的。

## 需要 AI Hub 端配合的部分

要讓分享出去的 Agent 真的能用，AI Hub 得提供公開 agent 的 bundle 取得路徑（例如 `/api/playground/agents/{id}/bundle/public/load`，或讓公開設定回應直接附上下載連結）。下載本身不需要憑證——`bundle_store.download_bundle_zip` 只是 `httpx.get(download_url)`——卡住的是拿到那個連結。

**另外：`semantic_bundle_ref` 目前是空字串**，資料庫十五個 agent 全空，公開 API 回傳的也是空。Timothy 掛著十三個 PDF 卻沒有任何 bundle 參照。所以在開放公開路徑之前，得先確認這些 bundle 到底有沒有被存下來。


## 完成記錄（本 repo 這半）

訊息改掉了。原本兩種很不一樣的狀況共用同一句結尾，所以「傷口照護步驟查不到」和「產品編號查不到」講出來一模一樣。現在各自帶自己的結尾：

| 狀況 | 使用者看到 |
|---|---|
| 宣告了參考文件但索引是空的 | 這個 Agent 的參考文件目前沒有載入，所以沒有任何內容可以查。已停止作答，避免給出沒有依據的內容。 |
| 有文件但這題查不到 | 目前沒有在參考資料中找到可以支持這個回答的內容。已停止作答，避免給出沒有依據的內容。 |
| 使用者指名的產品編號不在 catalog | catalog 沒有可驗證產品編號 X 的資料。已停止推薦與下一步送出，請交由服務人員人工確認。 |

第三種才是真正該找人的情境，它只在使用者訊息裡真的出現「產品編號」時觸發，所以保留原本的措辭。

分辨第一種與第二種的依據寫在 `_documents_unavailable_reason` 的 docstring：語意檢索沒有分數門檻，索引裡只要有東西 top-k 就一定回傳至少一筆，所以「宣告了 support_files 卻零命中」只可能是文件沒載入。

`tests/test_playground_contracts.py::test_a_shared_agent_says_its_documents_are_missing` 釘住這件事，反向驗證過會紅。

## 剩下的（需要 AI Hub 端）

**這只改了字，沒有讓 Agent 拿回它的文件。** 部署後匿名點進 Timothy 仍然答不出傷口照護步驟——只是它現在會老實說原因，而不是叫使用者去問庫存。

要真正修好，需要先確認 bundle 有沒有被存下來（`semantic_bundle_ref` 十五個全空），再開放公開取得路徑。這兩件都不在本 repo。
