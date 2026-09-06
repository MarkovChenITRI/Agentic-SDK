# Agentic SDK

Agentic SDK 是一個 Python 程式庫，用來組裝 AI agent 從收到問題到給出回答的完整流程。

流程固定拆成下列五個步驟，每一步是一個可以整個換掉的 Python 物件。只想改其中一步的人，不必先把其餘四步造出來。

| 步驟 | 做什麼 | 現成模組 |
| --- | --- | --- |
| Perceive | 整理使用者輸入 | 原樣傳遞、文字、文字加圖片、語音 |
| Plan | 決定下一步跑哪一個步驟 | 依有沒有資料可查來判斷 |
| Retrieve | 找出回答需要的資料 | 不查、關鍵字比對、語意相似度 |
| Action | 產生回覆或動作 | 固定文字、模型生成、工具請求（不代為執行）、語音回答 |
| Reflect | 檢查回覆 | 查有沒有依據、查有沒有答到問題 |

五步不是跑一遍就結束。Plan 決定下一步跑哪一個步驟，那一步跑完再問 Plan 一次，所以可以來回查資料或重新規劃。Plan 說結束就停，另有步數上限防止繞不出來。

## 替換單一模組

一個想法通常只落在其中一個模組上。拆開之後，驗證那個想法不必先把其餘四個造出來。

1. **換推論服務。** 把 `base_url` 指到自己的服務，完整一條 agent 就跑在那台機器上，量到的不只是單次推論。
2. **換規劃或記憶的機制。** 傳入自己寫的物件，輸入、檢索、回答、檢查沿用現成的。
3. **換應用邏輯。** 先用現成模組組出能跑的，再逐個替換成自己的。

需要模型的模組都走 OpenAI 相容介面，各模組需要哪些端點見[模組家族](https://r300-ai.github.io/Agentic-SDK/modules/)。

## 安裝

需要 Python 3.11 以上、3.13 以下，開發環境建議 3.12。

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

不指定標籤會裝到 `main` 的最新內容。`main` 隨時可能改變既有行為，而且重新安裝之後程式不會報錯，只是結果不一樣。要固定行為就指定標籤。

## 三個例子

先跑通一條完整的流程，再看換掉其中一格長什麼樣。三個例子對應上面那三種替換。

### 一條完整的流程

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

`PassThroughPerceive` 原樣保留輸入，`KeywordRetrieve` 逐字比對關鍵字取出條目，`DirectAnswerAction` 直接回傳取到的內容。沒有命中時回傳 `KeywordRetrieve(fallback=...)` 設定的那句。

### 換掉推論服務

把回覆改由模型整理，`base_url` 指到哪裡就跑在哪裡。Azure AI Foundry、本機的 Ollama、自家硬體上的服務都是同一個寫法。

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

### 換掉規劃機制

換掉的不只是模型。一個模組就是一個收 `WorkflowState`、回 `ModuleOutput` 的可呼叫物件，五格都能這樣換。下面換掉 Plan，其餘四格照舊。

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
# 走過的步驟依序是 perceive、plan、retrieve、action
```

模組的完整合約見[五大模組的共同寫法](https://r300-ai.github.io/Agentic-SDK/tutorials/module-writing-basics/)。

## 這個專案不做什麼

先講清楚邊界，省得裝完才發現不對題。

| 不做 | 誰來做 |
| --- | --- |
| 執行工具 | SDK 產生標準的工具請求，實際呼叫外部 API 由應用程式負責 |
| 播放聲音與擷取麥克風 | 音訊裝置由應用程式接，SDK 只負責產生與接收音訊資料 |
| 提供模型 | 自備 OpenAI 相容的端點 |
| 管理前端畫面 | SDK 送出事件，畫面怎麼呈現由應用程式決定 |

## 延伸閱讀

上面三個範例只用到關鍵字檢索與直接回覆。真正常見的需求各有教材，可以照順序讀完，也可以只挑當下要解的那一項。

| 想做的事 | 去哪裡 |
| --- | --- |
| 把整批文件餵進去做語意檢索 | [教材 05](https://r300-ai.github.io/Agentic-SDK/tutorials/search-documents-and-answer/) |
| 讓模型判斷什麼時候該叫工具 | [教材 06](https://r300-ai.github.io/Agentic-SDK/tutorials/call-tools-from-a-workflow/) |
| 把每一步的進度顯示在畫面上 | [教材 02](https://r300-ai.github.io/Agentic-SDK/tutorials/watch-a-workflow-run/)、[教材 03](https://r300-ai.github.io/Agentic-SDK/tutorials/configure-workflow-events/) |
| 用語音對話並且中途打斷 | [教材 08](https://r300-ai.github.io/Agentic-SDK/tutorials/talk-to-a-workflow/) |
| 自己寫一個步驟 | [五大模組的共同寫法](https://r300-ai.github.io/Agentic-SDK/tutorials/module-writing-basics/) |
| 查某個步驟有哪些現成模組與參數 | [模組家族](https://r300-ai.github.io/Agentic-SDK/modules/) |

九份教材的完整順序見 [Notebook 教材總覽](https://r300-ai.github.io/Agentic-SDK/tutorials/)，可直接執行的檔案在 `notebooks/`。

## 不寫程式也能試

專案另附一個網頁示範程式，用滑鼠組出一條流程並跑起來，滿意的話存成 Agent 重複使用。安裝與環境設定見 [playground/README.md](playground/README.md)。

## 貢獻者

[![Contributors](https://contrib.rocks/image?repo=R300-AI/Agentic-SDK)](https://github.com/R300-AI/Agentic-SDK/graphs/contributors)

由工業技術研究院的團隊開發與維護。想參與的團隊請讀[加入貢獻的逐步導引](https://r300-ai.github.io/Agentic-SDK/contributing/)。

依賴套件各自的授權列於 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

## 授權

本專案採 [PolyForm Noncommercial License 1.0.0](LICENSE) 並附加標示條款，版權屬工業技術研究院。

| 用途 | 可不可以 |
| --- | --- |
| 研究、教學、個人專案、內部概念驗證 | 可以，免費 |
| 商業使用 | 需另循工研院技術移轉取得授權 |

任何使用都必須在文件、關於畫面與成果發表中顯示：

> Powered by Agentic SDK, provided by the Industrial Technology Research Institute (ITRI).

商用與非商用的界線由工研院技術移轉單位認定。

