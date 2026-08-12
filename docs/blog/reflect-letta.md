# 用 Letta 將對話整理成可保存的長期記憶

長對話最容易先壞在看似不起眼的地方：使用者在第十輪提到的偏好，到了第五十輪仍然重要，但已不適合把整段對話原封不動塞進模型。模型讀得越多，花費與等待時間越難控制；模型讀得太少，又會忘記前面已經確認的事。

我們把 Letta 接到 AI Hub 的文字與嵌入模型服務，讓它負責保存需要跨對話留下的內容，Agentic SDK 則負責決定這一輪要不要更新記憶、要找回哪一段內容，以及如何把找回結果帶回回覆流程。關鍵不是把 Letta 當成另一個模型，而是把它當成模型服務旁的長期記憶層。

本文會從這個問題出發，說明記憶資料如何流經模型卡、Letta 與 `Workflow`，並用一個可重做的模組骨架說明我們怎麼把判斷寫進 Reflect。

## 從一段追問看見記憶問題

以旅遊規劃助手為例，使用者第一天說明預算、飲食限制與同行者需求，幾天後卻只問「那第二天改成下雨，行程怎麼調整？」如果系統只看最新一句話，回答會缺少先前確認的條件；如果每次都附上完整對話，內容會不斷膨脹，也把大量不再相關的寒暄送進模型。

我們把內容拆成兩層：目前回合的完整對話留在 `InContextMemory`，需要跨回合保留的偏好、決定與可追溯摘要寫進 Letta。回覆前先根據這一輪問題找回相關記憶，回覆完成後再判斷是否有新的內容值得保存。

```text
使用者訊息 -> Agentic SDK Workflow -> Letta 找回相關記憶
    -> AI Hub 文字模型服務 -> 產生回覆 -> Reflect 檢查
    -> 需要保留：Letta 保存摘要
    -> 不需要保留：結束本輪工作流程
```

## 用 Letta 將長期記憶整理成摘要並保存

模型卡記錄文字或嵌入模型、執行環境與部署條件。Letta 使用這些模型服務管理核心記憶、長期記憶，以及找回過去對話的內容。這個分工讓工作流程只關心「需要什麼記憶」，不需要知道模型跑在哪張 GPU、向量儲存放在哪裡。

每個部署組態都保存模型卡版本、模型名稱、執行環境、端點網址、Letta 版本、記憶儲存位置與憑證參照。這些欄位看起來像部署細節，卻是重現問題的必要條件：同一段對話得到不同結果時，我們能分辨是模型版本、嵌入版本，還是保存的記憶內容改變。

## 讓記憶服務使用 OpenAI 相容的模型服務

Agentic SDK 的模型節點以 `api_key`、`base_url` 與 `model` 連到 OpenAI 相容的模型服務。記憶服務與工作流程共用這組設定，因此應用程式不必為特定硬體或供應商另外撰寫連線邏輯。

設定的重點是把端點集中在部署資料，而不是寫死在模組裡：

```python title="letta_deployment.py"
memory_deployment = {
    "chat": {"base_url": chat_url, "api_key": api_key, "model": chat_model},
    "embedding": {"base_url": embedding_url, "api_key": api_key, "model": embedding_model},
    "memory_namespace": "travel-planner",
}
```

當文字模型或嵌入模型升級時，只需要更新模型卡與這份部署設定。工作流程和業務程式維持同一個公開介面，這也是我們選擇 OpenAI 相容端點而非在每個模組接入特定供應商用戶端的原因。

## 由 Reflect 決定何時寫入與找回記憶

`LettaReflect` 與 `LettaPersistentMemory` 根據回覆結果、可用證據與寫入結果，決定是否整理摘要、保存內容、找回記憶或明確回報失敗。這個做法只依賴 SDK 的 `PersistentMemory`、`WorkflowState`、`ContextEntry` 與 `ModuleOutput` 公開介面，因此不需要改動 `Workflow` 的執行規則。

下面的骨架展示了 Reflect 的責任邊界。它不生成最終回覆，也不直接改寫模型內容；它只留下下一步所需的結構化結果，讓工作流程決定是否再次執行 Action。

```python title="letta_reflect.py"
class LettaReflect:
    name = "reflect"

    def __init__(self, memory) -> None:
        self.memory = memory

    def __call__(self, state):
        reply = state.lookup("latest_final_message") or ""
        if not reply:
            return {"next_module": None}

        summary = self.memory.summarize(state.latest_user_message(), reply)
        if summary.should_save:
            self.memory.save(namespace="travel-planner", content=summary.content)
        return {"payload": {"memory_saved": summary.should_save}, "next_module": None}
```

實作時，找回內容會以 `ContextEntry` 放回本輪狀態，而不是直接覆蓋使用者訊息。這使得回覆、事件追蹤和除錯紀錄都能看見系統用了哪些記憶。

## 匯出可直接用在工作流程的記憶設定

模型卡部署記錄會產生版本化設定，內容包含模型服務連線、Letta 連線與記憶命名空間。應用程式讀取設定後即可附加到 `Workflow`：

```python title="app.py"
workflow = Workflow(
    workflow_name="旅遊規劃助手",
    memory_store=letta_memory,
    action=travel_action,
    reflect=LettaReflect(letta_memory),
)
```

這段組裝刻意很短。模型服務、記憶命名空間與憑證都由部署設定處理；應用程式只表達這條工作流程需要長期記憶和一個回覆模組。

## 確認長期記憶能正確寫入與找回

我們以三輪對話驗證這條流程：第一輪保存飲食限制，第二輪加入住宿偏好，第三輪只詢問雨天備案。驗證重點不是模型能不能寫出一段文字，而是第三輪是否只找回與行程相關的記憶，且不遺漏前兩輪已確認的限制。

另外也測試空結果、錯誤端點、錯誤憑證與跨對話重新建立。每次測試記錄模型卡版本、執行環境、命令、測試資料與追蹤資料。這些資料讓我們能把「模型回答不同」拆成可檢查的問題，而不是把所有差異都歸因於模型隨機性。

## 隨模型部署一併提供長期記憶

完成整合後，開發者可在工作流程中使用能保留來源脈絡的長期記憶。這個案例也讓 AI Hub 的模型部署不只交付一個端點，而能一併提供該模型需要的記憶服務與版本化設定。

## 我們學到的事

長期記憶不是把更多內容塞進內容長度限制，而是為每一筆可保留資訊建立清楚的保存理由、命名空間與找回路徑。把這個責任留給 Letta 和 Reflect，讓 Action 專注回答眼前問題，工作流程才能在對話變長後仍保持可理解與可維護。

## 參考資料

- [Letta 文件](https://docs.letta.com/)
- [Letta GitHub 專案](https://github.com/letta-ai/letta)
- [工作流程](../workflow/index.md)
- [記憶類型](../workflow/memory-types.md)