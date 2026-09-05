# Notebook 教材

這一區放的是 Agentic SDK 的流程方法教材。模組細節請回到「模組家族」查；每份 Notebook 只處理一個可驗證的主題。先以 00 確認 SDK 能跑，再逐步建立 workflow、顯示執行階段、配置畫面事件、處理多輪對話、驗證回覆、呼叫工具，理解模組共同規範，最後處理語音輸入與輸出。

需要一支可以直接跑的完整程式時，repo 的 [`examples/`](https://github.com/R300-AI/Agentic-SDK/tree/main/examples) 有幾支——其中 `examples/voice/desktop_voice_agent.py` 用一個 WAV 當麥克風，沒有音效裝置也跑得動。

## 建議學習順序

| 順序 | 教材 | Notebook |
| --- | --- | --- |
| 00 | [跑出第一條 Agentic SDK Workflow](getting-started.md) | `00-getting-started.ipynb` |
| 01 | [做出一條可以跑的工作流程](build-and-run-a-workflow.md) | `01-build-and-run-a-workflow.ipynb` |
| 02 | [讓畫面知道 Agent 跑到哪一步](watch-a-workflow-run.md) | `02-watch-a-workflow-run.ipynb` |
| 03 | [設定工作流程的畫面事件](configure-workflow-events.md) | `03-configure-workflow-events.ipynb` |
| 04 | [讓 Agent 接得住前後文](multi-turn-conversation.md) | `04-multi-turn-conversation.ipynb` |
| 05 | [讓 Agent 檢查回答有沒有依據](search-documents-and-answer.md) | `05-search-documents-and-answer.ipynb` |
| 06 | [讓 Agent 判斷什麼時候要叫工具](call-tools-from-a-workflow.md) | `06-call-tools-from-a-workflow.ipynb` |
| 07 | [五大模組的共同寫法](module-writing-basics.md) | `07-from-playground-to-code.ipynb` |
| 08 | [用講的跟 Workflow 對話](talk-to-a-workflow.md) | `08-talk-to-a-workflow.ipynb` |