# Agentic SDK

Agentic SDK 是一個用 Python 組合 Agent 工作流程的程式庫。五種模組接起來就是一條可測試、可替換、可觀察的 Agent 流程，各模組的職責見下一節。

SDK 以 `MemoryStore` 統一管理對話記憶；`InContextMemory` 與 `PersistentMemory` 提供兩種可替換的記憶方式。`InContextMemory` 依時間順序保存同一個 `session_id` 的完整對話歷史，所有需要模型的模組都可透過 `MemoryStore` 讀取這份前文。

## 核心概念

一個 workflow 由幾個可選模組組成：

- Perceive：整理使用者輸入，產生可供後續步驟使用的感知結果。
- Plan：決定下一步要 Retrieve、Action，或結束流程。
- Retrieve：從規則、關鍵字或語意檢索中取得支援資料。
- Action：產生最終回覆、呼叫工具，或執行自訂處理邏輯。
- Reflect：檢查結果品質或資料依據，必要時中止或重新規劃。

最小 workflow 只需要 `Workflow` 加上實際會用到的模組。所有模組都可以用一般 Python 物件替換，因此適合從小型 PoC 擴充到正式應用。

`Workflow.run(...)` 仍支援最簡單的單輪呼叫。`Workflow` 預設會以 `InContextMemory` 承接同一個 `session_id` 的完整對話歷史；要替換記憶實作時，在建立 workflow 時傳入 memory 物件，例如 `memory = InContextMemory()` 搭配 `Workflow(memory_type=memory)`。`memory_type` 也接受 `"in_context"`、`"persistent"` 或既有的 memory class 形式。`WorkflowState` 則保留執行中的中繼結果、payload 與觀測資料。

## 安裝

需要 Python 3.11 以上、3.13 以下；本 repo 的開發環境建議使用 Python 3.12。

指定版本標籤安裝，取得該版本固定的行為：

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

不指定標籤則安裝 `main` 分支的最新內容：

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git"
```

`main` 隨時可能包含改變既有行為的變更。已經寫好的程式在下次重新安裝之後，可能得到不同的結果而不會出現錯誤訊息。要停留在特定行為上，請指定標籤。

從 GitHub 安裝時，pip 使用 `git+https://...` 格式；也可使用命名形式：`python -m pip install "agentic-sdk @ git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"`。

## 快速開始

### 1. 最小可執行 Workflow

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import DirectAnswerAction, KeywordRetrieve, PassThroughPerceive

workflow = Workflow(
    workflow_name="知識問答 Agent",
    description="根據內建關鍵字知識庫回答常見問題。",
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {
                "keywords": ["agentic sdk", "sdk"],
                "content": "Agentic SDK 是一個以 workflow 組裝 agent 行為的 Python library。",
            },
            {
                "keywords": ["tsip"],
                "content": "TSiP 是工研院主導的國產 AI 晶片落地藍圖。",
            },
        ],
    ),
    action=DirectAnswerAction(),
)

result = workflow.run("TSiP 是什麼？")
print(result.final_message)
```

`PassThroughPerceive` 會保留原始輸入，`KeywordRetrieve` 依關鍵字取得支援資料，`DirectAnswerAction` 則直接回傳檢索到的內容。

用同一個 `session_id` 再次呼叫同一個 `Workflow` 時，新的使用者輸入與前一次 assistant 回覆都會保留在 `result.memory` 中。

這段快速開始同時是 [00：跑出第一條 Agentic SDK Workflow](docs/tutorials/getting-started.md) 的可執行基準；完整的 00–08 學習順序見 [Notebook 教材總覽](docs/tutorials/index.md)。

### 2. 使用 OpenAI-compatible 生成回覆

可搭配任何 OpenAI-compatible endpoint，例如 Azure AI Foundry、Ollama 或其他相容服務。

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import GenerativeAction, KeywordRetrieve, PassThroughPerceive

workflow = Workflow(
    workflow_name="Foundry 回覆 Agent",
    description="用 OpenAI-compatible 模型整理檢索結果並生成自然語句回覆。",
    events_schema={
        "retrieve": {"label": "正在查找參考資料"},
        "action": {"label": "正在準備回覆"},
    },
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {
                "keywords": ["tsip"],
                "content": "TSiP 是工研院主導的國產 AI 晶片落地藍圖。",
            },
        ],
    ),
    action=GenerativeAction(
        api_key="ollama",
        base_url="http://localhost:11434/v1/",
        model="llama3.2:1b",
    ),
)

result = workflow.run("TSiP 是什麼？")
print(result.final_message)
```

### 3. 觀察 workflow 與直接串流 Action 回覆

省略 `events_schema` 時，`Workflow` 會送出每個實際執行步驟的開始、完成與中止事件。模型產生的文字以 `token_delta` 送出，結構化欄位則以完整 JSON 值的 `structured_field` 送出。

各步驟的標準名稱如下。

| 模組 | 事件上顯示的名稱 |
| --- | --- |
| Perceive | 理解輸入 |
| Plan | 判斷工具順序 |
| Retrieve | 整理相關來源 |
| Action | 準備輸出回覆 |
| Reflect | 檢查回覆 |

傳入 `events_schema` 則是明確覆寫／限制：只有列出的 module 會送出 stage event，`fields` 只送出列出的 dot path；若明確要保留完整欄位觀測，可指定 `"*"`. 下例刻意只觀察部分欄位：

```python
events_schema = {
    "perceive": {
        "label": "理解輸入",
        "fields": ["summary", "details.next_step"],
    },
    "plan": {
        "label": "判斷工具順序",
        "fields": ["thought", "next_module"],
    },
    "action": {"label": "準備輸出回覆"},
}

workflow = Workflow(
    perceive=TextPerceive(api_key=API_KEY, base_url=BASE_URL, model=MODEL),
    plan=NextStepPlan(api_key=API_KEY, base_url=BASE_URL, model=MODEL),
    action=GenerativeAction(api_key=API_KEY, base_url=BASE_URL, model=MODEL),
    events_schema=events_schema,
)
```

`Workflow.stream(...)` 會依序提供回覆步驟產生的使用者可見文字。可串流的回覆會即時提供文字片段，其他回覆會在完成時提供最終文字。完整迭代後可從 `stream.result` 取得 `WorkflowResult`：

```python
def on_event(event):
    if event["type"] == "stage" and event["phase"] == "start":
        print(f"\n【{event['module']}】{event['label']}")
    elif event["type"] == "stage" and event["phase"] == "finish":
        for item in event["fields"]:
            print(f"\n{item['field']}：{item['value']}")


stream = workflow.stream("TSiP 是什麼？", event_callback=on_event)
for delta in stream:
    print(delta, end="", flush=True)

result = stream.result
```

`run(..., event_callback=on_event)` 與 `stream(..., event_callback=on_event)` 使用同一份 `events_schema`，送出的事件種類相同。`stream()` 接受的參數也與 `run()` 一致。

callback 處理文字片段時，iterator 以完成等待為主。設定 `yield_action_deltas=True` 可同時從 iterator 取得文字片段。

### 4. 使用 ToolCallAction 產生 OpenAI 標準工具呼叫

`ToolCallAction` 使用 OpenAI SDK 的 `tools` / `tool_choice` 標準格式，並把模型回傳的 `message.tool_calls` 正規化到 `result.entities["latest_tool_calls"]`。

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import KeywordRetrieve, PassThroughPerceive, ToolCallAction

tools = [
    {
        "type": "function",
        "function": {
            "name": "submit_booking",
            "description": "提交球場預約資料。",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "預約人姓名。",
                    },
                    "booking_time": {
                        "type": "string",
                        "description": "使用者想預約的日期與時間。",
                    },
                },
                "required": ["customer_name", "booking_time"],
                "additionalProperties": False,
            },
        },
    }
]

workflow = Workflow(
    workflow_name="預約工具 Agent",
    description="根據使用者輸入判斷是否要發出預約工具呼叫。",
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {
                "keywords": ["booking", "預約", "球場"],
                "content": "球場預約需要留下姓名與預約時間。",
            },
        ],
    ),
    action=ToolCallAction(
        api_key="<API key>",
        base_url="<OpenAI-compatible base_url>",
        model="<支援 tool calling 的模型>",
        tools=tools,
    ),
)

result = workflow.run("我想預約明天下午三點的球場，姓名是王小明。")
print(result.final_message)
print(result.entities["latest_tool_calls"])
```

SDK 會產生並保存標準工具請求結果。應用程式讀取工具名稱與參數後，自行呼叫外部 API、顯示確認內容或提交資料。

### 5. 自訂 Action

Action 也可以是一般 Python class。自訂 Action 會收到 `WorkflowState`，可以透過 `state.lookup(...)` 讀取前面模組產生的資料。

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import KeywordRetrieve, PassThroughPerceive


class SummaryAction:
    def __call__(self, state):
        summary = state.lookup("latest_retrieved_content") or "沒有命中任何條目。"
        return f"自訂 Action 回傳：{summary}"


workflow = Workflow(
    workflow_name="摘要處理 Agent",
    description="把檢索內容交給自訂 Action 做二次整理。",
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {
                "keywords": ["agentic sdk", "sdk"],
                "content": "Agentic SDK 以 workflow 組裝 agent 行為。",
            },
        ],
    ),
    action=SummaryAction(),
)

result = workflow.run("請介紹 Agentic SDK")
print(result.final_message)
```

自訂模組可透過 `state.memory` 讀取完整對話，這個欄位使用通用的 `MemoryStore` 介面；要讀取最新一輪使用者文字，可使用 `state.latest_user_message()`。

## 延伸閱讀

上面五段涵蓋常用的組合方式。多輪對話、文件檢索、語音互動與自訂模組的完整教材放在文件站，可以照順序讀完，也可以只挑當下要解的那一項。

| 想做的事 | 去哪裡 |
| --- | --- |
| 照順序學一遍，邊看邊改 | [Notebook 教材](https://r300-ai.github.io/Agentic-SDK/tutorials/)，00 到 08 共九份 |
| 查某個角色有哪些現成模組與參數 | [模組家族](https://r300-ai.github.io/Agentic-SDK/modules/) |
| 了解工作流程怎麼跑、記憶怎麼運作 | [工作流程](https://r300-ai.github.io/Agentic-SDK/workflow/) |
| 用語音跟工作流程對話 | [教材 08](https://r300-ai.github.io/Agentic-SDK/tutorials/talk-to-a-workflow/) |
| 知道某個設計為什麼這樣定 | [設計決策](https://r300-ai.github.io/Agentic-SDK/)的 ADR 章節 |

`notebooks/` 目錄放的是可直接執行的檔案，教材頁面是它們的說明。

## 示範程式

專案另附一個 Flask 示範程式，用來展示工作流程的建立、執行與互動方式。安裝、啟動與示範環境設定請閱讀 [playground/README.md](playground/README.md)。

## 貢獻者

[![Contributors](https://contrib.rocks/image?repo=R300-AI/Agentic-SDK)](https://github.com/R300-AI/Agentic-SDK/graphs/contributors)

本專案由工業技術研究院內多個單位共同開發。

| 單位 | 貢獻範疇 |
| --- | --- |
| 電光所 異質整合晶片系統組（R 組） | 工作流程核心、五個角色模組、Playground、文件網站 |
| 機械所 機器人技術組（Q 組） | 即時語音互動 |

想參與的團隊請讀[加入貢獻的逐步導引](https://r300-ai.github.io/Agentic-SDK/contributing/)。

## 授權

本專案採 [PolyForm Noncommercial License 1.0.0](LICENSE) 並附加標示與商業使用條款，
版權屬工業技術研究院。非商業用途一律允許，商業使用需另循工研院技術移轉取得授權。

任何使用都必須在文件、關於畫面與成果發表中顯示下列標示：

> Powered by Agentic SDK, provided by the Industrial Technology Research Institute (ITRI).

依賴套件各自的授權列於 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
