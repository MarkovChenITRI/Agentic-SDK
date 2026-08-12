# 用 Fara 看懂畫面並操作電腦

固定網頁定位方式很容易在版面或內容改變時失效。按鈕換了位置、標籤改了文字或彈出提示視窗後，原本能用的選取器可能立刻失效。這在需要跨多個版本的內部系統上特別棘手：自動化腳本看起來成功執行，卻可能把資料填進錯誤欄位，或在不該送出的頁面按下確認。

我們用一個可重置的採購測試網站驗證 Fara 1.5。任務是「找出尚未核對的請款單，填入已核對金額，但不要送出」。第一版只讓模型輸出動作並直接交給控制器。它在表單改版後仍找到金額欄位，卻也提出點擊「送出請款」的操作。這不是模型辨識失敗，而是系統把「提出下一步」誤當成「可以執行下一步」。

最後的做法是把 Fara 部署為 AI Hub 模型卡，並透過 OpenAI 相容端點接入 Agentic SDK。Action 只負責根據任務、畫面與操作歷程提出一個動作；Reflect 擁有執行權，檢查動作是否落在允許範圍、頁面是否真的往前推進，以及是否應該交由人員確認。模型不再直接控制瀏覽器，而是在可中止、可重播的迴圈中提出下一個操作。

## 為什麼不直接讓模型連到瀏覽器

把完整瀏覽器控制權直接交給模型，會讓每一次錯誤判斷都直接變成外部副作用。我們改成「截圖、提出一個動作、驗證結果」三個階段。模型只負責提出操作，控制器只負責執行已核准的操作，Reflect 決定是否繼續。

這個區分讓「填入金額」和「送出請款」成為兩種不同的事件。前者是測試案例明確允許的輸入；後者是有外部副作用的操作，必須停止自動迴圈並要求人工確認。下表是 Action 與 Reflect 之間保留的最小契約，操作紀錄不再只是一段模型文字。

| 欄位 | Action 提供的內容 | Reflect 檢查的問題 |
| --- | --- | --- |
| `kind` | `click`、`type`、`scroll` 或 `key` | 這個動作是否在允許清單內？ |
| `target` | 座標或頁面元素描述 | 是否位於目前允許的網域與畫面區域？ |
| `value` | 要輸入的金額或按鍵 | 是否可寫入這個欄位，且不含敏感資料？ |
| `reason` | 模型採取此步驟的依據 | 前一步畫面真的支持這個判斷嗎？ |

流程從任務開始，依序擷取畫面、呼叫 Fara 模型服務、取得單一步驟操作並交給操作政策。政策允許時，瀏覽器控制器執行操作，再由 Reflect 比對操作前後的畫面；政策要求確認時，流程停在可檢閱的操作紀錄；任務完成或中止時，才回傳結果。

## 將 Fara 看懂畫面與操作電腦的能力做成模型卡

模型卡記錄 Fara 的版本、權重精度、vLLM 執行環境、CUDA 目標、內容長度、畫面輸入、單一步驟操作輸出、授權條件與研究預覽限制。模型卡不只用來列出模型名稱；它也是控制器判斷輸入輸出格式是否相容的依據。這讓部署版本更換時，團隊可以明確重跑畫面處理、動作格式與安全政策三類驗證，而不是只確認端點仍能回應。

將畫面輸入與操作輸出明確列在模型卡中，讓部署平台、Action 模組和測試工具都依同一份契約運作。當我們更新模型版本時，可以立即知道需要重新驗證的是畫面處理、操作格式還是安全政策。

## 在 A100 上部署可透過 OpenAI SDK 使用的 Fara 推論服務

部署路徑是 Fara 權重、vLLM、`NC24ads_A100_v4 VM`，再提供版本化端點與 `api_key`、`base_url`、`model` 設定。Fara 官方公開 vLLM 與 OpenAI 相容服務的自架方式，讓我們可以沿用 SDK 已有的模型連線介面。

應用程式不需要知道 A100 或 vLLM 的細節，只需要讀取版本化組態：

```python title="fara_deployment.py"
fara_endpoint = {
    "base_url": "https://models.example.ai/fara/v1",
    "api_key": os.environ["AI_HUB_API_KEY"],
    "model": "fara-1.5",
    "max_actions": 12,
}
```

把操作上限放在同一份設定裡，是因為它和模型能力一樣屬於部署契約。某個模型版本如果在相同任務下需要更多步驟，就必須重新驗證，而不是讓應用程式悄悄放寬限制。

## 讓 Action 逐步執行 Fara 產生的操作

`FaraComputerUseAction` 將任務、先前操作與畫面傳給模型服務，一次取得一個操作並記錄結果。瀏覽器控制器負責擷取畫面與執行點擊、輸入、按鍵或捲動；`FaraReflect` 檢查座標、回傳格式、頁面是否前進、操作上限與人工確認條件。

核心迴圈保持單純，讓每個外部副作用都有紀錄：

```python title="fara_workflow.py"
class FaraComputerUseAction:
    name = "action"

    def __call__(self, state):
        screenshot = controller.capture()
        action = fara_client.next_action(
            task=state.latest_user_message(),
            screenshot=screenshot,
            history=state.lookup("computer_history") or [],
        )
        return {"payload": {"proposed_action": action}, "next_module": "reflect"}


class FaraReflect:
    name = "reflect"

    def __call__(self, state):
        action = state.lookup("proposed_action")
        decision = policy.check(action, visit_count=state.visit_counts.get("action", 0))
        if decision.requires_approval:
            return {"payload": {"approval_required": True}, "next_module": None}
        controller.execute(decision.action)
        return {"next_module": "action" if not controller.task_complete() else None}
```

重要的是 `FaraReflect` 不是事後產生一段警告文字，而是在操作前阻擋不合規的座標、網域、輸入欄位或操作次數。以採購測試網站為例，模型提出 `click`「送出請款」後，政策回傳 `approval_required`，控制器沒有送出 HTTP 請求，且操作紀錄保留這次拒絕。這讓安全控制是流程的一部分，而不是依賴使用者記得遵守的約定。

## 從模型卡匯出可直接用在工作流程的 Fara 設定

模型卡設定包含模型版本、A100 端點、Fara 模型、隔離測試環境與操作政策。應用程式只需要將 Action 和 Reflect 放進 `Workflow`：

```python title="app.py"
workflow = Workflow(
    workflow_name="受控電腦操作",
    action=FaraComputerUseAction(),
    reflect=FaraReflect(),
    entry_module="action",
)
```

這個組裝方式保留了 SDK 的標準控制流程：Action 提出下一步，Reflect 檢查並決定是否回到 Action。當需要加上登入、付款或刪除資料等高風險動作時，政策只要回傳人工確認即可中止自動迴圈。

## 用操作記錄確認 Fara 是否部署成功

我們不只確認任務能走到結尾，也針對最常造成錯誤自動化的情境建立測試紀錄。

| 測試情境 | 預期行為 | 記錄的結果 |
| --- | --- | --- |
| 金額欄位改變位置 | 根據新畫面重新定位並輸入 | Reflect 比對欄位值與畫面變更後繼續 |
| 點到可見但無關的按鈕 | 不把頁面切換誤判為成功 | 偵測不到預期內容時停止並附上截圖 |
| 提出送出、刪除或付款操作 | 不執行，要求人工確認 | 控制器未呼叫外部動作，紀錄標示為 `approval_required` |
| 反覆提出相同操作 | 終止迴圈而非持續嘗試 | 到達操作上限後回傳可重播的失敗紀錄 |

每一步保存操作前後的畫面、模型回傳的動作、政策判斷和控制器結果。這讓我們在流程失敗時可以回答具體問題：是模型看錯畫面、政策阻擋了操作，還是網頁本身沒有如預期更新。它也讓測試結果能直接成為更新 Fara 模型卡時的回歸檢查，而不是一次性的展示。

## 讓工作流程在安全限制下操作電腦

完成整合後，開發者可選擇 Fara 模型卡並在工作流程中加入受控的視覺操作。AI Hub 也能在模型卡中管理電腦操作需要的輸入、輸出與安全欄位，而不是把這些關鍵限制分散在各個應用程式。

## 可直接帶走的做法

- 每次只讓模型提出一個動作，將跨步驟規劃留在操作歷程，而不是一次執行一串指令。
- 將允許動作、網域、欄位與最大步數寫成可版本化的政策，不放在提示文字裡。
- 對每次操作保存提案、政策判斷、執行結果和前後畫面，讓失敗可重播。
- 把有外部副作用的動作視為中止條件，由人員接手，而不是讓模型猜測是否可以繼續。

視覺電腦操作的難處不只在於模型看不看得懂畫面，更在於每一次操作是否能被驗證、重播和中止。把模型輸出限制為單一步驟，再讓 Reflect 持有真正的執行權，能讓工作流程從展示性自動化走向可維運的工具操作。

## 參考資料

- [Fara GitHub 專案](https://github.com/microsoft/fara)
- [Fara 論文](https://arxiv.org/abs/2606.20785)
- [回覆與動作模組](../modules/action-modules.md)
- [安全控制模組](../modules/reflect-modules.md)