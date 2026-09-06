# Contributors

本專案由工業技術研究院內多個單位共同開發。下表記錄各單位的貢獻範疇，
供使用者、引用者與技轉作業辨識來源。

| 單位 | 貢獻範疇 | 起始 |
| --- | --- | --- |
| 電子與光電系統研究所 異質整合晶片系統組（R 組） | 工作流程核心、五個角色模組、Playground、文件網站 | 專案建立 |
| 機械與機電系統研究所 機器人技術組（Q 組） | 即時語音互動：音訊傳輸層、語音感知與語音回答模組、Playground 語音工作階段、語音中止機制 | 2026-09 |

## Q 組貢獻的路徑

| 範疇 | 路徑 |
| --- | --- |
| 音訊傳輸層 | `agentic_sdk/audio/` |
| 語音角色模組 | `agentic_sdk/modules/perceive/voice_text.py`、`agentic_sdk/modules/action/voice_answer.py` |
| Playground 語音工作階段 | `playground/services/voice_session.py`、`playground/static/js/runner/voice-conversation.js` |
| 語音測試 | `tests/test_voice_*.py`、`tests/test_speech_output.py` |
| 語音決策紀錄 | `docs/adr/0001-where-voice-lives.md`、`docs/adr/0003-how-a-voice-endpoint-is-defined.md` |

GitHub 的 Contributors 圖表只讀提交的 author 與 co-author 欄位。語音功能併入前的提交
未帶 `Co-authored-by:` 尾標，因此該圖表無法反映上表的分工，改寫已推送的歷史則會使既有
clone 失效。往後由各單位成員產出的提交加上 `Co-authored-by:` 尾標，圖表即可自行累積。
