# 用講的跟 Workflow 對話

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/R300-AI/Agentic-SDK/blob/main/notebooks/08-talk-to-a-workflow.ipynb)

這份教材示範語音輸入與輸出的四個特性。前三段用假的音訊傳輸驅動，不需要網路、憑證或麥克風，在 Colab 直接跑得動；最後一段才換成真的語音部署。

語音和文字最大的差別不在介面，而在時序：話什麼時候來取決於人什麼時候想講，而且人可以在 Agent 講到一半時插話。這兩件事會改變工作流程接收輸入與結束回合的方式。

## 你會學到

- 為什麼安靜的片段不能上傳，以及說完之後為什麼還要多送一小段安靜。
- 讓模組先收下聽到的話，`Workflow.run()` 不必再被告知一次。
- 被打斷之後只保留對方真正聽到的部分，沒聽到的不進入下一輪上下文。
- 為什麼被打斷的回合 `interrupted` 為真、`aborted` 為假。
- SDK 不擷取麥克風也不播放聲音，這兩端要接在哪裡。

## 相關文件

- [輸入理解](../modules/perceive-modules.md)
- [回覆與動作](../modules/action-modules.md)
- [工作流程](../workflow/index.md)
