# 06: 瀏覽器聽得到、講得出來

**What to build:** 畫廊訪客點進一個語音 Agent，直接開口就能對話，講到一半打斷它會立刻安靜。拒絕麥克風權限時，畫面說明它需要什麼。

**Blocked by:** 03, 04, 05

**Status:** done

- [x] Playground 提供 WebSocket 端點轉發音訊，金鑰不進瀏覽器
- [x] 瀏覽器擷取麥克風並串流；瀏覽器播放合成音訊
- [x] 收到插話訊號時**立刻停止播放**，不等後端確認
- [x] 停止後回報已播放時長，並截斷上下文
- [x] 麥克風權限被拒時說明原因，不是靜靜地不動
- [x] 進入畫面即可開口，不需要先按按鈕

## 三個步驟的順序有意義

先停播放（使用者感知的延遲是一個影格），再記已播時長，最後截斷上下文。前端先停是為了體感，後端收尾是為了正確——兩件事分開。

## 如果這張塞不進一個 context window

沿這條線切成兩張：**瀏覽器聽得到**（端點 + 麥克風 + 權限）與**瀏覽器講得出來**（播放 + 打斷處理 + 截斷）。切點在「音訊進」與「音訊出」之間。

## 瀏覽器那半怎麼驗的

這台機器沒有裝 playwright，但 playwright 快取的 chromium 還在，Chrome 和 Firefox 也在。
`spikes/realtime-interjection/verify_in_browser.py` 直接用 DevTools Protocol 開一個帶假麥克風的
無頭 Chrome，從跑著的 Playground 載入**真正的模組**，四件事都是實跑出來的：

- 麥克風不用按按鈕就開起來，狀態顯示「可以開始說話了。」
- 2.5 秒內送出 **104 個音框、70,928 bytes** 的 16 kHz PCM——閘門讓聲音過、擷取與降取樣都是通的
- 丟一段合成音訊再送 `speech_started`，頁面立刻停播並回報 `heard_seconds: 0.2987`
- 把 `getUserMedia` 改成拒絕，畫面說明它要麥克風權限，不是靜靜地不動

驗的過程中真的抓到一個 bug：session id 長成 `voice-...-.4vfok`，因為
`Math.random().toString(36).slice(1, 7)` 把 `0.` 的小數點一起切進去了。

另外補了一段 `AudioContext` 的處理：瀏覽器會讓 AudioContext 停在 suspended，
這時頁面看起來在聽、實際上一個音訊事件都不會有。現在會先 resume，還是不行就請使用者點一下畫面。
（這不是 0 音框的原因——那次是檢測腳本自己包 WebSocket 時漏了 `WebSocket.OPEN` 常數。）
