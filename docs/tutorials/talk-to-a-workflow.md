# 用講的跟 Workflow 對話

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/R300-AI/Agentic-SDK/blob/main/notebooks/08-talk-to-a-workflow.ipynb)

本文件示範語音輸入與輸出的四項行為，並涵蓋 `VoiceTextPerceive` 與 `VoiceAnswerAction` 兩個模組。全程連線真實端點，不使用替身物件。

語音與文字最主要的差異不在介面，而在時序。語音抵達的時機取決於使用者何時開口，而非呼叫端何時發起請求；且使用者可在回答進行中插話。這兩點改變工作流接收輸入與結束回合的方式。

## 涵蓋內容

- 靜音片段不上傳的原因，以及語句結束後仍需送出一段靜音的原因。
- 模組先行收取輸入，`run()` 不需再次取得使用者說出的內容。
- 中斷後僅保留實際送達使用者的內容，未送達的部分不進入下一回合的上下文。
- 被中斷的回合 `interrupted` 為真、`aborted` 為假的原因。
- 音訊擷取與播放不屬於 SDK 的職責，以及兩端的接續方式。

## 相關文件

- [輸入理解](../modules/perceive-modules.md)
- [回覆與動作](../modules/action-modules.md)
- [工作流程](../workflow/index.md)
