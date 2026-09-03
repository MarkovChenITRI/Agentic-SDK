# 01: 畫廊分享出去的 Agent，答題時沒有自己的文件

**What to build:** 匿名點開畫廊裡的 Agent 時，它要嘛拿得到自己的參考文件，要嘛老實說拿不到。

**Blocked by:** 無

**Status:** done

- [x] 失敗訊息不再假設使用者在賣東西
- [x] 分不出「查不到」與「根本沒有文件可查」時，不要說成前者
- [x] AI Hub 放寬既有 `bundle/load` 的權限判斷（在 `ai-hub-webui`，已部署）

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

## 完成記錄：沿用既有端點，改權限判斷

**不需要新端點。** `GET /api/playground/agents/{id}/bundle/load` 一直都在，卡的只是它一律要求帳密。AI Hub 的原始碼在 `~/Documents/GitHub/ai-hub-webui`。

### AI Hub 側

`utils/agent_workspace/playground_bundle.py` 新增 `load_public_agent_bundle`，和 `load_agent_bundle` 只差在問的問題不同：不問「你是不是擁有者」，問「這個 Agent 是不是已上架 Gallery」。判斷沿用現成的 `read_public_playground_agent`，它的 SQL 本來就在檢查 `gallery_domain IS NOT NULL AND <> ''`。

`utils/routes/playground_routes.py` 的 `bundle/load` 在請求沒有宣稱任何身分時走公開分支；有宣稱身分的一樣要驗證，沒有放寬。

### Playground 側

- `_request_bundle_url`：只有非 download 才強制要憑證。放不放行由 AI Hub 決定。
- `_bundle_download_headers`：接受 `None`。
- `aihub_bridge` 的 `read` 分支：比照 `edit` 分支還原，失敗就擋下來報錯。

### 實測（真資料庫、真儲存體）

```
Timothy（已上架 Gallery）  OK   blob=playground-agents/agt_bf22b5544fb64d45/bundle/agentic_playground_bundle.zip
                               簽出 SAS 連結
血液生化（未上架）          404  找不到指定的 Agent。
```

閘門正確：上架的給連結，沒上架的擋掉。

### 還沒驗到的一段

拿 SAS 去下載檔案時回 `AuthorizationPermissionMismatch`。原因是**執行測試的 az 帳號缺 Storage Blob Data Reader**，簽出來的 SAS 沒有實際讀取權。線上 App Service 的 managed identity 有這個角色，擁有者路徑現在就靠它運作。

所以「檔案確實在、內容是那 13 份 PDF」這件事我沒有親眼確認。要補這一段，需要在 `agenticsdk` 儲存帳戶上給測試帳號 Storage Blob Data Reader。

### 安全性

POC 站，已確認可接受：已上架 Gallery 的 Agent，其參考文件可經 API 取得（需帶 Playground 的 Origin）。網頁上沒有下載入口。

## 部署注意

`ai-hub-webui` **不是 git repo**，這兩個檔案的修改沒有版本控制。部署 AI Hub 之前要確認這兩處有被帶上去。


## 更正（2026-09-03）：不需要新端點，AI Hub 那半已完成

我先前寫「AI Hub 要補一個公開 bundle 端點」，那是錯的判斷，而且我當時把「不在本 repo」當成做不到的理由。**`bundle/load` 早就存在**，卡的只是它對所有呼叫者一律要帳密；而 AI Hub 的原始碼就在 `~/Documents/GitHub/ai-hub-webui`（`R300-AI/ai-hub-webui`）。

### AI Hub 側（commit `990b53c`，已部署）

`load_public_agent_bundle` 問的問題和 `load_agent_bundle` 不同：不問「你是不是擁有者」，問「這個 Agent 有沒有上架 Gallery」。判斷沿用現成的 `read_public_playground_agent`。路由在請求完全沒宣稱身分時走公開分支；有宣稱身分的照原本驗證。

部署後線上實測：

```
Timothy（已上架）    HTTP=200  簽出 blob 下載連結，實際下載到 66,962,477 bytes
血液生化（未上架）    HTTP=404
Origin 錯誤          HTTP=403
帳密錯誤             HTTP=401
```

### Playground 側

匿名的兩個入口都補上還原，且**還原失敗降級而非擋下**——擁有者被擋下能自己修，畫廊訪客只會拿到死頁。失敗原因留在 session，並在 agent 真的需要文件時進入 `debug_messages`。

**兩個入口**：`aihub_bridge.start_runner_bridge_session` 的 read 分支，以及 `entry.py` 的 `navigate_from_shared_agent_to_runner`。後者是 code review 才發現的漏修——那四個 bundle/session helper 在兩個檔案裡各有一份逐字相同的副本，改一處就會漏另一處。收斂成一個模組列為後續工作，不在這次。

### 已知的後續問題

Timothy 的 bundle 是 67 MB。`restore_agent_bundle_zip` 每次還原都用新的 `upload_id`，**每個 session 一份解壓副本，沒有回收機制**。先前只有擁有者會走這條路，現在每個匿名訪客都會。需要以 agent_id 加 ETag 做快取，另開票追。
