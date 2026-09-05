# 用講的跟 Workflow 對話

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/R300-AI/Agentic-SDK/blob/main/notebooks/08-talk-to-a-workflow.ipynb)

示範語音輸出、語音輸入、語音與文字併行輸出，以及回答被中斷後的行為。四項各佔一章，全程連線真實端點。

建立需要口語互動的 Agent 時，這四項決定使用者實際感受到的反應方式。

## 涵蓋內容

| 章 | 執行的工作 | 涵蓋的模組 |
| --- | --- | --- |
| 一 | 以鍵盤輸入問題，同時產出語音與畫面兩個頻道 | `VoiceAnswerAction` |
| 二 | 以合成音訊模擬麥克風，轉為該回合的輸入 | `VoiceTextPerceive` |
| 三 | 量測語音開始輸出與文字產生完畢的時間差 | `VoiceAnswerAction` |
| 四 | 在回答進行中送入語音，檢視保留的回合記錄 | 兩者 |

語音與文字的差異在時序，不在介面。語音抵達的時機取決於使用者何時開口，且使用者可在回答進行中插話；兩者改變工作流接收輸入與結束回合的方式。

## 相關文件

- [輸入理解](../modules/perceive-modules.md)
- [回覆與動作](../modules/action-modules.md)
- [工作流程](../workflow/index.md)
