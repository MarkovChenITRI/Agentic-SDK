# Agentic SDK

用 Python 把一次問答拆成五個步驟，接成一條可以逐步替換的流程。

每個步驟都有多個現成模組可以換，因此同一套組裝方式涵蓋的範圍很廣：

- 輸入可以是打字、圖片，或直接開口說話。
- 查資料可以用關鍵字，也可以用語意相似度。
- 回答可以是固定文字、模型生成、標準工具請求，或唸出聲音。
- 每一步都送出事件，畫面照著顯示流程跑到哪一步。
- 使用者中途開口就能打斷，記錄下來的是實際交付出去的那一段，不是模型寫完的整段。

不寫程式的話，附的網頁示範程式用滑鼠也能組出同一條流程。

## 授權先看

本專案採 [PolyForm Noncommercial License 1.0.0](LICENSE) 並附加標示條款，版權屬工業技術研究院。

| 用途 | 可不可以 |
| --- | --- |
| 研究、教學、個人專案、內部概念驗證 | 可以，免費 |
| 商業使用 | 需另循工研院技術移轉取得授權 |

任何使用都必須在文件、關於畫面與成果發表中顯示：

> Powered by Agentic SDK, provided by the Industrial Technology Research Institute (ITRI).

商用與非商用的界線由工研院技轉單位認定。窗口的聯絡方式尚未公告，需要時請先開一張 issue 詢問。

## 核心概念

一次問答拆成五個步驟，每一步是一個可替換的物件，用不到的留空。

| 步驟 | 做什麼 | 現成模組 |
| --- | --- | --- |
| Perceive | 整理使用者輸入 | 原樣傳遞、文字、文字加圖片、語音 |
| Plan | 決定下一步要查資料、回答，還是結束 | 依支援資料判斷 |
| Retrieve | 取得支援資料 | 不查、關鍵字、語意相似度 |
| Action | 產生回覆或動作 | 固定文字、模型生成、工具請求、語音回答 |
| Reflect | 檢查回覆 | 檢查依據、檢查回覆內容 |

每一格都可以換成自己寫的物件，規格見[模組家族](https://r300-ai.github.io/Agentic-SDK/modules/)。

## 安裝

需要 Python 3.11 以上、3.13 以下，開發環境建議 3.12。

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

不指定標籤會裝到 `main` 的最新內容。`main` 隨時可能改變既有行為，而且重新安裝之後程式不會報錯，只是結果不一樣。要固定行為就指定標籤。

## 快速開始

三個範例由淺入深。第一個不需要任何模型服務，複製貼上就能跑。

### 1. 不用模型也能跑

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

### 2. 多輪對話

同一個 `session_id` 的前後文自動保留，第二輪不必重述第一輪。不同 `session_id` 各自獨立，多個使用者不會串在一起。

```python
first = workflow.run("特休有幾天？", session_id="user-42")
second = workflow.run("那病假呢？", session_id="user-42")

for turn in second.memory.turns:
    print(turn.role, turn.content)
# user      特休有幾天？
# assistant 年資滿一年可休七天特休。
# user      那病假呢？
# assistant 病假一年三十天，超過三十天需附診斷證明。
```

### 3. 換成模型生成回覆

把 `DirectAnswerAction` 換成 `GenerativeAction`，回覆改由模型整理，其餘不動。任何 OpenAI 相容的服務都可以，例如 Azure AI Foundry 或本機的 Ollama。

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

五個步驟都是這樣替換的：換掉一個物件，其餘照舊。

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
