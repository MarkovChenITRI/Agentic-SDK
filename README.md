# Agentic SDK

Agentic SDK 讓一條 agent 在網頁上點出來、匯出成 Python、換到另一個推論服務上執行，
三件事都不必重寫；換模型只改一個網址，自訂一個環節只要寫一個普通的 Python 物件，
不必繼承任何基底類別。架構取自 Park 等人 2023 年的
[Generative Agents](https://arxiv.org/abs/2304.03442)，分成四層，每一層都附現成的實作。

| 層 | 負責什麼 |
| --- | --- |
| Workflow | 跑完一輪對話。決定接下來交給哪個模組、管住一輪最多跑幾個模組、把每個模組的進度送出去給畫面用 |
| Module | 一輪裡的五類工作，各有現成模組可挑：**Perceive** 整理使用者輸入（打字、圖片或語音）、**Plan** 決定接下來交給誰、**Retrieve** 找資料（關鍵字或語意）、**Action** 產生回覆（文字、模型生成、工具請求或語音）、**Reflect** 檢查回覆有沒有依據 |
| Memory | 記住同一個對話前面談過什麼，五類模組都讀得到 |
| Data | 模組之間傳遞的內容，一輪之內共用同一份，每個模組把自己的結果加上去 |

## 一輪怎麼跑

每個模組做完會指定接下來交給誰，所以同一輪裡可以查完資料發現不夠再查一次，也可以在 Reflect
沒過之後回頭重新規劃，直到某個模組指定結束為止；Workflow 另有次數上限，避免在同幾個模組之間繞不出來。

## 可以換掉哪些東西

四層裡有三處可以換成自己的實作：換掉五類裡的任何一類模組（傳入一個自訂物件即可，其餘四類照舊）、
換掉 Memory 存放對話的方式（五類模組完全不變）、或換掉模組使用的推論服務（把 `base_url`
指向另一個服務，程式碼結構不變，因為需要模型的模組都走 OpenAI 相容介面）。
Workflow 與 Data 兩層是固定的，各模組需要哪些端點見[模組家族](https://r300-ai.github.io/Agentic-SDK/modules/)。

## 交出去之後由誰接手

模組交出的是資料，實際的動作由使用這個程式庫的應用程式執行：Action 產生標準格式的工具請求，
外部 API 由應用程式呼叫；語音模組產生與接收音訊資料，播放與收音由應用程式的音訊裝置負責；
Workflow 送出每個模組的進度事件，畫面怎麼呈現由應用程式決定。

## 網頁版 Playground

專案內附一個網頁版的 Playground，不寫程式也能使用：在頁面上挑選每一類要用哪個模組、填入知識庫內容，
就能與組出來的 agent 對話，結果可以存起來重複使用，也可以匯出成 Python 程式碼。
它跑在 repo 裡，需要先 clone 專案，啟動方式與環境設定見 [playground/README.md](playground/README.md)。

## 安裝

需要 Python 3.11 以上、3.13 以下，開發環境建議 3.12；下面第一行的 `@v0.1.0` 是版本標籤，
指定它才會固定在該版的行為，省略時裝到 `main` 的最新內容，而 `main` 改變行為時程式不會報錯、只是結果不一樣。

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

## 三個例子

第一個用三類模組組出一條可執行的流程，不需要任何模型服務；第二個把 Action 換成模型生成；
第三個把 Plan 換成自訂物件。沒有指定的類別不會出現在這一輪，所以第一個例子只跑 Perceive、Retrieve、Action 三類。

### 用現成模組組一條流程

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import DirectAnswerAction, KeywordRetrieve, PassThroughPerceive

workflow = Workflow(
    workflow_name="請假問答",
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {"keywords": ["特休", "年假"], "content": "年資滿一年可休七天特休。"},
            {"keywords": ["病假"], "content": "病假一年三十天，超過三十天需附診斷證明。"},
        ],
    ),
    action=DirectAnswerAction(),
)

result = workflow.run("特休有幾天？")
print(result.final_message)   # 年資滿一年可休七天特休。
```

`PassThroughPerceive` 原樣保留輸入，`KeywordRetrieve` 逐字比對關鍵字取出條目，`DirectAnswerAction`
直接回傳取到的內容；沒有命中時回傳預設的 `No matching entries.`，改成自己的句子傳 `KeywordRetrieve(fallback="...")`。

### 換掉推論服務

```python
from agentic_sdk.modules import GenerativeAction

workflow = Workflow(
    workflow_name="請假問答",
    perceive=PassThroughPerceive(),
    retrieve=KeywordRetrieve(
        items=[
            {"keywords": ["特休", "年假"], "content": "年資滿一年可休七天特休。"},
        ],
    ),
    action=GenerativeAction(
        api_key="ollama",
        base_url="http://localhost:11434/v1/",
        model="llama3.2:1b",
    ),
)

print(workflow.run("我到職滿一年了，可以請幾天特休？").final_message)
```

把回覆改由模型整理，`base_url` 指到哪裡就跑在哪裡，Azure AI Foundry、本機的 Ollama、
自家硬體上的服務都是同一個寫法；這個例子連的是本機的 Ollama，需要先在本機把它跑起來。

### 換掉一個模組

```python
from agentic_sdk.core import ModuleOutput

class AlwaysRetrieveOnce:
    """自訂的規劃機制：第一次先查資料，查過就回答。"""

    name = "plan"

    def __call__(self, state):
        looked_up = state.lookup("latest_retrieved_content")
        return ModuleOutput(next_module="action" if looked_up else "retrieve")


workflow = Workflow(
    workflow_name="自訂規劃",
    perceive=PassThroughPerceive(),
    plan=AlwaysRetrieveOnce(),
    retrieve=KeywordRetrieve(
        items=[{"keywords": ["特休"], "content": "年資滿一年可休七天特休。"}],
    ),
    action=DirectAnswerAction(),
)

print(workflow.run("特休有幾天？").final_message)
# 依序經過 perceive、plan、retrieve、action
```

自訂模組不必繼承任何基底類別，只要有 `name` 說明它屬於哪一類、有 `__call__` 收下當前狀態並回傳
下一站是誰；`ModuleOutput(next_module=None)` 表示這一輪結束。完整合約見[五大模組的共同寫法](https://r300-ai.github.io/Agentic-SDK/tutorials/module-writing-basics/)。

## 延伸閱讀

上面三個例子只用到關鍵字檢索與直接回覆，其餘功能各有教材，共九份，
完整順序見 [Notebook 教材總覽](https://r300-ai.github.io/Agentic-SDK/tutorials/)，可直接執行的檔案在 `notebooks/`。

| 功能 | 教材 |
| --- | --- |
| 語意檢索整批文件 | [教材 05](https://r300-ai.github.io/Agentic-SDK/tutorials/search-documents-and-answer/) |
| 工具呼叫 | [教材 06](https://r300-ai.github.io/Agentic-SDK/tutorials/call-tools-from-a-workflow/) |
| 執行事件與進度顯示 | [教材 02](https://r300-ai.github.io/Agentic-SDK/tutorials/watch-a-workflow-run/)、[教材 03](https://r300-ai.github.io/Agentic-SDK/tutorials/configure-workflow-events/) |
| 語音對話與中途打斷 | [教材 08](https://r300-ai.github.io/Agentic-SDK/tutorials/talk-to-a-workflow/) |
| 自訂模組 | [五大模組的共同寫法](https://r300-ai.github.io/Agentic-SDK/tutorials/module-writing-basics/) |
| 現成模組與參數 | [模組家族](https://r300-ai.github.io/Agentic-SDK/modules/) |

## 貢獻者

[![Contributors](https://contrib.rocks/image?repo=R300-AI/Agentic-SDK)](https://github.com/R300-AI/Agentic-SDK/graphs/contributors)

由工業技術研究院的團隊開發與維護，參與方式與目前的貢獻者名單見 [CONTRIBUTING.md](CONTRIBUTING.md)。
