# Contributors

本專案由工業技術研究院內多個單位共同開發。這一頁記錄兩件事：每位貢獻人在
貢獻當時隸屬哪個單位，以及每個單位負責哪一塊。技轉標的的界定與學術引用都
從這裡取值。

## 貢獻人

一列代表一段隸屬關係，不是一個人。同一個帳號換部門時新增一列，填上新的期間，
既有的列保持原狀——那段期間的貢獻歸屬於當時的單位，事後不因人事異動而改變。

| GitHub 帳號 | 姓名 | 單位 | 期間 | 貢獻範疇 |
| --- | --- | --- | --- | --- |
| [@MarkovChenITRI](https://github.com/MarkovChenITRI) | Markov Chen | 電光所 異質整合晶片系統組（R 組） | 2026-06 起 | 工作流程核心、五個角色模組、Playground、文件網站 |
| [@Terrykuo20031222](https://github.com/Terrykuo20031222) | 未定 | 未定 | 2026-08 | 合併分支 |
| 未定 | 未定 | 機械所 機器人技術組（Q 組） | 2026-09 起 | 即時語音互動 |

期間只寫起訖月份。人離開該單位時填上結束月份，另起一列記錄新單位。

## 單位與貢獻範疇

| 單位 | 貢獻範疇 | 起始 |
| --- | --- | --- |
| 電光所 異質整合晶片系統組（R 組） | 工作流程核心、五個角色模組、Playground、文件網站 | 專案建立 |
| 機械所 機器人技術組（Q 組） | 即時語音互動：音訊傳輸層、語音感知與語音回答模組、Playground 語音工作階段、語音中止機制 | 2026-09 |

### Q 組貢獻的路徑

| 範疇 | 路徑 |
| --- | --- |
| 音訊傳輸層 | `agentic_sdk/audio/` |
| 語音角色模組 | `agentic_sdk/modules/perceive/voice_text.py`、`agentic_sdk/modules/action/voice_answer.py` |
| Playground 語音工作階段 | `playground/services/voice_session.py`、`playground/static/js/runner/voice-conversation.js` |
| 語音測試 | `tests/test_voice_*.py`、`tests/test_speech_output.py` |
| 語音決策紀錄 | `docs/adr/0001-where-voice-lives.md`、`docs/adr/0003-how-a-voice-endpoint-is-defined.md` |

## 提交歷史為什麼對不上這一頁

GitHub 的 Contributors 圖表只讀提交的 author 與 co-author 欄位。語音功能併入
之前的提交未帶 `Co-authored-by:` 尾標，因此該圖表無法反映上表的分工，而改寫
已推送的歷史會使既有 clone 失效。

往後的提交帶尾標即可讓圖表自行累積。尾標使用的信箱建議用單位配發的信箱而非
GitHub 的 noreply 位址，該次提交的隸屬單位因而直接留在歷史裡，不必回頭查這一頁。
