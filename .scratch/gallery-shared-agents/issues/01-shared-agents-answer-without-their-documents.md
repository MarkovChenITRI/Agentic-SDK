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

## 剩下的（需要 AI Hub 端）— 依設計文件更正

查了 `eosl-aihub-pages` 的交握設計文件，我先前兩個判斷是錯的：

**錯誤一：我說「bundle 可能沒被存下來」。** 沒有根據。`playground-file-save.md` 寫明固定儲存位置是 `playground-agents/{agent_id}/bundle/agentic_playground_bundle.zip`——**路徑由 agent_id 推導**。程式碼也吻合：`restore_runtime_bundle` 只吃 `agent_id`，從頭到尾不讀 `semantic_bundle_ref`。那個欄位是空的不代表檔案不在。

**錯誤二：我把匿名拿不到 bundle 講成缺陷。** `connection-and-responsibility.md` 的「Runner 唯讀模式與 AI Hub 保存邊界」明確定義：

> 非擁有者或未登入使用者從 Gallery 進入工作流時……由 Playground 依 `owner` 與 `agentId` 載入**公開 config**。這條路徑不需要 AI Hub 登入，也不提供保存、重新載入為擁有者或其他擁有者限定操作。

唯讀路徑的設計範圍就是 config。bundle 的存取在 `playground-file-save.md` 裡兩條流程都寫著「AI Hub **驗證使用者權限**後」簽發短效連結——它是擁有者操作。

所以匿名拿不到文件不是壞掉，是**設計上沒有涵蓋這個情境**。

## 真正的落差

同一份文件把 Gallery 的匿名入口定位成「使用者**試用**別人的 workflow」。但語意檢索的 Agent 沒有文件就試不了——十五個 agent 裡八個是語意檢索。所以「試用」在最常見的 Agent 型態上是空的。

`semantic_bundle_ref` 也印證了這個設計缺口：`save_contract_v2` 有這個參數、公開 config API 也回傳它，但唯一的呼叫端 `aihub.py:121` 沒有傳，所以十五筆全空。讀的那一側準備好了，寫的那一側沒接上——不過就算接上也不夠，見下。

## AI Hub 要補什麼

需要一個公開的 bundle 取得端點，比照既有的 `config/public/load`：

```
POST /api/playground/agents/{agent_id}/bundle/public/load
```

權限判斷不看使用者，看**這個 Agent 是不是已選 Gallery 類型**——就是 `PUT /api/me/agents/{id}/gallery-type` 設定的那個值，文件寫明「只有選成智慧大健康或智慧工廠次系統的 Agent 才會出現在公開 Gallery」。已經公開展示的 Agent，它的參考文件本來就跟著公開了。

**只給 `semantic_bundle_ref` 不夠。** 儲存帳戶 `agenticsdk` 的 `allowBlobPublicAccess` 是 `False`，容器 `playground-agent-files` 不可匿名讀。所以一定要 AI Hub 簽發短效下載連結，光有 blob 路徑沒有用。

Playground 這側要改的很小：`aihub_bridge.start_runner_bridge_session` 的 `read` 分支比照 `edit` 分支呼叫還原，只是改用公開端點、不帶 credentials。等 AI Hub 那條路開通再接。

## 登入路徑的狀態

沒有發現問題。`entry.py:99`（handoff 進 Runner）和 `entry.py:184`（選 Agent）兩處都有 `_restore_selected_agent_bundle`，而且還原失敗會擋下來報錯，不會靜靜地用空索引跑。

**但我沒有實測。** 那要用 Agent 擁有者的帳號登入走一次，我沒有帳號，也不會去資料庫撈使用者密碼。
