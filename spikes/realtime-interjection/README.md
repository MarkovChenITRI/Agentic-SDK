# Spike：即時插話

回答一個問題：**使用者能不能在 Agent 回答到一半開口打斷，而它真的停下來、聽懂、接著回應？**

結論是可以，四個未知數都有實測數字。這份紀錄留下數字和踩過的坑，因為下一個做的人不該再花一次同樣的時間。

## 量到的數字

| 環節 | 實測 | 量法 |
| --- | --- | --- |
| 開口 → `speech_started` | **~610 ms** | `measure_transcribe_latency.py` |
| 說完 → 完整轉寫 | +440 ms | 同上 |
| 取消 → 工作流停止（模組之間） | **217 ms** | `measure_cancel_between_modules.py` |
| 取消 → 工作流停止（生成中） | **932 ms** | `measure_cancel_mid_stream.py` |
| TTS 首位元組 / 全長 | 1.0 s / 3.9 s | `curl`，見下 |
| 跨區 RTT（台灣 → eastus2） | ~200 ms | `curl` 建線時間 |

**開口到閉嘴最壞約 1.5 秒。**

## 最重要的一件事：打斷不必等轉寫

`input_audio_buffer.speech_started` 在開口後 610 ms 就到，而完整轉寫要 3.9 秒。

所以打斷分兩段：**一出聲就停**（用 VAD 訊號），**說完才重新規劃**（用轉寫文字）。等轉寫再停就晚了三秒，那不叫插話。

## 服務設定

轉寫和語音合成都部署在 `b2044-mrx9rt3z-eastus2`，不是 southeastasia——那邊只有 `whisper`。Key Vault 的 `TRANSCRIBE-*` 與 `TTS-*` 一度指向 southeastasia，症狀是 401「use a correct regional API endpoint」，兩邊金鑰都是 85 字元所以看長度分不出來。

即時轉寫走 WebSocket：

```
wss://<host>/openai/realtime?api-version=2025-04-01-preview&deployment=<dep>&intent=transcription
```

`intent=transcription` 不可省略，省了會連上但立刻回 `error`。`api-version=2025-03-01-preview` 直接 404。REST 端點也支援 `stream=true`，逐字回 `transcript.text.delta`，但那是**先上傳完整音檔**再串流結果，不適合即時。

TTS 的 `response_format=pcm` 首位元組最快且免解碼，可以直接餵瀏覽器的 AudioContext。

## 踩到的兩個坑

**尾端沒有靜音，VAD 永遠不會判定語句結束。** 送完音訊就停會讓轉寫一直不回來，看起來像連線壞掉。真實麥克風不會有這問題，測試音檔要自己補一秒靜音。

**取樣率必須 16 kHz。** TTS 產出的 pcm 是 24 kHz，中間要重採樣。`measure_transcribe_latency.py` 用了 `audioop`，它在 Python 3.13 之後會移除，正式實作要換掉。

## 核心改了什麼

取消能力做在 SDK 核心，音訊留在 Playground 層——模組標準不該知道麥克風存在。

- `agentic_sdk/core/cancellation.py`：`CancellationToken` 與 `WorkflowInterrupted`
- `Workflow.run(..., cancel=...)`：模組之間檢查一次
- `chat_stream(..., should_stop=...)`：每個 chunk 檢查一次，這是長回答唯一值得中斷的地方
- 五個會串流的模組把 `state.should_stop` 交給傳輸層
- `WorkflowResult` 多了 `interrupted` 與 `interrupt_payload`

**中斷與失敗分開。** hop 上限和逾時是工作流自保，該顯示錯誤；被人插話是使用者在主導，對他顯示錯誤很荒謬。五個模組原本的 `except Exception` 會把取消當成模型錯誤吞掉，所以取消要先被接住再往上拋。

## 為什麼狀態是乾淨的

`state.apply(output)` 在模組**回傳之後**才執行，模組執行期間唯一碰 state 的是 `emit_token_delta`，而它只轉發不寫入。所以砍掉執行中的模組不會留下半寫入的狀態——實測確認，生成中取消後 context 只有已完成模組的 entry，沒有殘缺的 `action_result`。

這是這次改造能做得乾淨的原因，不是運氣。

## 932 ms 那個數字要修，但不是修核心

取消檢查在「收到下一個 chunk」時才執行：

```python
for chunk in stream:
    if should_stop(): raise StreamCancelled(...)
```

模型思考時兩個 chunk 可能隔快一秒，取消就得等。兩個方向：

1. 串流消費放到獨立執行緒，主執行緒等待取消事件，取消就直接關連線。停止延遲接近零。
2. 前端收到取消訊號立刻停止渲染與播放，不等後端確認。

**建議 2。** 使用者要的是「我一開口它就不講了」，那是畫面和聲音的事；後端多花 900 毫秒收尾他看不見。

## 還沒做的

- `produced_characters` 已經回報使用者聽到了多少，但**接續那一輪要怎麼用它**還沒設計（重述、承接、還是當新問題）
- 瀏覽器端的麥克風擷取與音訊播放
- 語音與畫面雙頻道輸出：`spoken` 與 `displayed` 分開生成。`IncrementalJsonFieldParser` 已經支援欄位完成即吐出，所以 `spoken` 一好就能送去 TTS，不必等 `displayed` 生成完
- 前端停止播放的實作

## 怎麼跑這些腳本

需要 `az login` 且對 `agentic-sdk-models` Key Vault 有讀取權。

```bash
.venv/bin/python spikes/realtime-interjection/probe_transcribe_endpoint.py
.venv/bin/python spikes/realtime-interjection/measure_transcribe_latency.py
.venv/bin/python spikes/realtime-interjection/measure_cancel_between_modules.py
CANCEL_AT=10 .venv/bin/python spikes/realtime-interjection/measure_cancel_mid_stream.py
```

`measure_transcribe_latency.py` 需要 `/tmp/speech.pcm`，由 TTS 產生：

```bash
curl -s -o /tmp/speech.pcm -X POST "$TTS_URL" -H "api-key: $TTS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"agentic-sdk-gpt-4o-mini-tts","input":"等一下，我想先問價格。","voice":"alloy","response_format":"pcm"}'
```
