# Agentic SDK

不論做的是哪一種 AI agent，一輪互動從聽懂使用者開始，到檢查結果為止，中間走過的環節都是同樣那五個。變的只是每個環節怎麼實作——輸入可能是打字、圖片或說話，回應可能是一段文字、一次工具呼叫，或一句唸出來的話。Agentic SDK 把這五個環節固定成五個 Python 物件，各自附上現成的實作與彼此之間的接線，開發者換掉想自己動手的那一個，其餘四個照舊運作。

| 步驟 | 做什麼 | 現成模組 |
| --- | --- | --- |
| Perceive | 整理使用者輸入 | 原樣傳遞、文字、文字加圖片、語音 |
| Plan | 決定下一步跑哪一個步驟 | 依有沒有資料可查來判斷 |
| Retrieve | 找出回答需要的資料 | 不查、關鍵字比對、語意相似度 |
| Action | 產生回覆或動作 | 固定文字、模型生成、工具請求（不代為執行）、語音回答 |
| Reflect | 檢查回覆 | 查有沒有依據、查有沒有答到問題 |

這五個環節不是自訂的分類，取自 Park 等人 2023 年的論文
[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)。
該論文提出的代理架構以一條記憶流承接全部經驗，再由觀察、檢索、反思與規劃四個機制在其上運作，
論文的評估也指出觀察、規劃與反思三者各自關鍵。Agentic SDK 沿用這組分工，把觀察對應到 Perceive，
把論文中含在「行為」裡的執行獨立成 Action，記憶流則做成所有步驟共用的 `MemoryStore`。

這五步不是排好順序跑一遍就結束。每一步跑完都會回到 Plan，由它決定下一步走到哪裡，所以同一輪裡可以先查一次資料、發現不夠再查一次，也可以在檢查沒過之後重新規劃。停下來的時機由 Plan 自己決定，另有步數上限擋住繞不出來的情況。

## 替換單一模組

想自己動手的那一步落在哪裡，決定了怎麼下手。實務上分成三種：有人要換的是底下跑推論的機器，有人要換的是流程中間的判斷方式，有人要換的是整套業務邏輯。三種的替換方式不同，但共同點是其餘部分都不必自己寫。

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

三個例子照上面那三種替換排列。第一個不需要任何模型服務，複製貼上就能跑，先確認整條流程在自己的環境裡是活的；第二個把回覆交給模型，示範推論服務怎麼換；第三個換掉規劃機制，示範自訂模組怎麼寫。

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

能換的不只是模型。五個步驟都是同一種東西：一個收 `WorkflowState`、回 `ModuleOutput` 的可呼叫物件，所以自訂一個步驟只需要寫出這兩者之間的關係。下面換掉 Plan，其餘四步照舊。

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

下面四件事這個程式庫不做，事先講清楚，省得裝完才發現不對題。它們不是還沒做，是刻意留給應用程式決定——工具怎麼執行、音訊裝置怎麼接、模型從哪裡來、畫面怎麼呈現，每一項的答案都隨部署環境而不同。

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

