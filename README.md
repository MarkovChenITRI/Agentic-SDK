# Agentic SDK

Agentic SDK 是一個 Python 程式庫，把一個 AI agent 的執行拆成四層。架構取自 Park 等人 2023 年的
[Generative Agents](https://arxiv.org/abs/2304.03442)。

| 層 | 負責什麼 |
| --- | --- |
| Workflow | 跑完一輪。決定下一站交給哪個模組、管住執行上限、把每一站的進度送出去 |
| Module | 一類工作的執行單位。模組收到當下的狀態，做完交出結果與下一站是誰 |
| Memory | 記住前面談過什麼。同一個對話的前後文由它承接，每個模組都讀得到 |
| Data | 在模組之間傳遞。一輪之內共用同一份狀態，模組各自往上面添東西 |

四層各自替換，互不牽動。換一個自訂模組不會動到執行的迴圈與記憶的存法，
換一種記憶的存法不會動到任何模組。

跑完一輪也不是把模組排好順序走一遍。每個模組做完會交代下一站是誰，
所以同一輪裡可以先查一次資料、發現不夠再查一次，也可以在檢查沒過之後重新規劃。
停下來的時機由模組決定，另有節點次數上限擋住繞不出來的情況。

## 五類模組

Module 這一層分成五類工作，對應該架構的四個機制加上獨立出來的執行。
每一類都附現成的模組，換掉其中一類時，其餘四類沿用現成的。

| 類別 | 做什麼 | 現成模組 |
| --- | --- | --- |
| Perceive | 整理使用者輸入 | 原樣傳遞、文字、文字加圖片、語音 |
| Plan | 決定下一站交給哪一類 | 依有沒有資料可查來判斷 |
| Retrieve | 找出回答需要的資料 | 不查、關鍵字比對、語意相似度 |
| Action | 產生回覆或動作 | 固定文字、模型生成、工具請求、語音回答 |
| Reflect | 檢查回覆 | 查有沒有依據、查有沒有答到問題 |

這五類涵蓋的不只一種 agent。問答、工具型代理、語音助理用的是同一組類別，
差別只在每一類裝哪個模組。語音助理把 Perceive 換成語音、Action 換成語音回答，
中間三類不動。

模組交出的是資料，由應用程式接手執行。Action 產生標準格式的工具請求，外部 API 由應用程式呼叫；
語音模組產生與接收音訊資料，播放與收音由應用程式的音訊裝置負責；Workflow 送出每一站的進度事件，
畫面怎麼呈現由應用程式決定。

可替換的東西有三種，落在不同的層。前兩種是換掉一整個物件，第三種只換參數。

1. **一個模組（Module 層）。** 傳入自訂物件取代該類的現成模組，其餘四類與另外三層不變。
2. **記憶的實作（Memory 層）。** 換掉存放對話的方式，五類模組完全不變。
3. **模組使用的推論服務（模組參數）。** 把 `base_url` 指向另一個服務，程式碼結構不變。

需要模型的模組都走 OpenAI 相容介面，所以第三種只需要改一個網址。各模組需要哪些端點見[模組家族](https://r300-ai.github.io/Agentic-SDK/modules/)。

## 網頁版 Playground

專案附一個網頁版的 Playground，不寫程式也能使用。在頁面上選定每一類要用哪個模組、
填入知識庫內容，即可與組出來的 agent 對話；結果可以存成一個 agent 重複使用，也可以匯出成 Python 程式碼，
匯出的內容就是下面幾節的寫法。啟動方式與環境設定見 [playground/README.md](playground/README.md)。

## 安裝

需要 Python 3.11 以上、3.13 以下，開發環境建議 3.12。下面第二行的 import 用來確認裝好了。

```bash
python -m pip install "git+https://github.com/R300-AI/Agentic-SDK.git@v0.1.0"
python -c "import agentic_sdk; print('Agentic SDK import ok')"
```

不指定標籤會裝到 `main` 的最新內容。`main` 隨時可能改變既有行為，而且重新安裝之後程式不會報錯，只是結果不一樣。要固定行為就指定標籤。

## 三個例子

三個例子分別示範三件事。第一個組出一條完整的流程，不使用任何模型服務，複製貼上即可執行；第二個把 Action 換成模型生成，同時示範推論服務怎麼指定；第三個把 Plan 換成自訂物件，示範一個模組要寫成什麼樣子。

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

### 換掉一個模組

能換的不只是模型。五類模組都是同一種東西，一個收 `WorkflowState`、回 `ModuleOutput` 的可呼叫物件，所以自訂一個模組只需要寫出這兩者之間的關係。下面換掉 Plan，其餘四類照舊。

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

這個自訂物件沒有繼承任何基底類別，只有 `name` 與 `__call__` 兩樣東西。
模組的完整合約見[五大模組的共同寫法](https://r300-ai.github.io/Agentic-SDK/tutorials/module-writing-basics/)。

## 延伸閱讀

上面三個範例只用到關鍵字檢索與直接回覆。其餘功能各有教材，可依序讀完，也可單獨查閱；
九份教材的完整順序見 [Notebook 教材總覽](https://r300-ai.github.io/Agentic-SDK/tutorials/)，
可直接執行的檔案在 `notebooks/`。

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

由工業技術研究院的團隊開發與維護，參與方式見[加入貢獻的逐步導引](https://r300-ai.github.io/Agentic-SDK/contributing/)。
依賴套件各自的授權列於 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

## 授權

本專案採 [PolyForm Noncommercial License 1.0.0](LICENSE) 並附加標示條款，版權屬工業技術研究院。
| 用途 | 可不可以 |
| --- | --- |
| 研究、教學、個人專案、內部概念驗證 | 可以，免費 |
| 商業使用 | 需另循工研院技術移轉取得授權 |

商用與非商用的界線由工研院技術移轉單位認定。任何使用都必須在文件、關於畫面與成果發表中顯示下列標示。

> Powered by Agentic SDK, provided by the Industrial Technology Research Institute (ITRI).

