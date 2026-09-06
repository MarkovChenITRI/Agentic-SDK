# Agentic SDK

裝上程式庫、組出第一條工作流程，再照教材與文件擴充。

適用於用 Python 把 Agent 的判斷拆成可測試、可替換的角色，從概念驗證一路做到正式應用。

## 核心概念

一條工作流程由五個角色組成，各自負責一段判斷，全部可選。

| 角色 | 負責什麼 |
| --- | --- |
| Perceive | 整理使用者輸入，產生後續步驟可用的感知結果 |
| Plan | 決定下一步要查資料、要回覆，還是結束 |
| Retrieve | 從關鍵字或語意檢索取得支援資料 |
| Action | 產生回覆、呼叫工具，或執行自訂邏輯 |
| Reflect | 檢查結果的品質與依據，必要時重新規劃 |

最小的一條只需要 `Workflow` 加上實際會用到的角色，其餘留空。同一個 `session_id` 的前後文由 `MemoryStore` 自動保留，需要模型的角色都讀得到。

## 安裝

需要 Python 3.11 以上、3.13 以下，開發環境建議 3.12。

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

指定標籤安裝可取得該版本固定的行為。不指定標籤會裝到 `main` 的最新內容，既有程式在下次重新安裝後可能得到不同結果而不出現錯誤訊息。

## 快速開始

跑通一條不需要模型的工作流程，再把回覆換成模型生成。兩段各自可以整段複製執行，第二段只比第一段多一個角色的差異。

### 一、最小可執行的工作流程

三個角色、一份關鍵字知識庫，不需要任何模型服務。

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

`PassThroughPerceive` 保留原始輸入，`KeywordRetrieve` 依關鍵字取出支援資料，`DirectAnswerAction` 直接回傳檢索到的內容。

### 二、接上模型生成回覆

把 `DirectAnswerAction` 換成 `GenerativeAction`，回覆改由模型整理。任何 OpenAI 相容的服務都可以，例如 Azure AI Foundry、Ollama。

```python
from agentic_sdk import Workflow
from agentic_sdk.modules import GenerativeAction, KeywordRetrieve, PassThroughPerceive

workflow = Workflow(
    workflow_name="Foundry 回覆 Agent",
    description="用 OpenAI 相容模型整理檢索結果並生成自然語句回覆。",
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

換掉的只有一個角色，其餘不動。五個角色都是這樣替換的。

## 接下來讀什麼

上面兩段是起點，其餘能力各有教材與說明。教材可以從頭照順序讀完，也可以只挑當下要解的那一項；文件則是查完就走的參考。

| 想做的事 | 去哪裡 |
| --- | --- |
| 照順序學一遍，邊看邊改 | [Notebook 教材](https://r300-ai.github.io/Agentic-SDK/tutorials/)，00 到 08 共九份 |
| 查某個角色有哪些現成模組與參數 | [模組家族](https://r300-ai.github.io/Agentic-SDK/modules/) |
| 了解工作流程怎麼跑、記憶怎麼運作 | [工作流程](https://r300-ai.github.io/Agentic-SDK/workflow/) |
| 知道某個設計為什麼這樣定 | [設計決策](https://r300-ai.github.io/Agentic-SDK/) 的 ADR 章節 |
| 不寫程式，先在網頁上組一條試試 | 下一節的示範程式 |

`notebooks/` 目錄放的是可直接執行的檔案，教材頁面是它們的說明。

## 示範程式

專案另附一個網頁示範程式，不必寫程式就能組出一條工作流程並跑起來，滿意的話可以存成 Agent 重複使用。安裝與環境設定見 [playground/README.md](playground/README.md)。

## 貢獻者

[![Contributors](https://contrib.rocks/image?repo=R300-AI/Agentic-SDK)](https://github.com/R300-AI/Agentic-SDK/graphs/contributors)

本專案由工業技術研究院內多個單位共同開發。電光所 異質整合晶片系統組負責工作流程核心、五個角色模組、示範程式與文件；機械所 機器人技術組負責即時語音互動。

想參與的團隊請讀[加入貢獻的逐步導引](https://r300-ai.github.io/Agentic-SDK/contributing/)。

## 授權

本專案採 [PolyForm Noncommercial License 1.0.0](LICENSE) 並附加標示與商業使用條款，版權屬工業技術研究院。非商業用途一律允許，商業使用需另循工研院技術移轉取得授權。

任何使用都必須在文件、關於畫面與成果發表中顯示下列標示：

> Powered by Agentic SDK, provided by the Industrial Technology Research Institute (ITRI).

依賴套件各自的授權列於 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
