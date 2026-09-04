"""量即時轉寫延遲：以真實語速送音訊，記錄每個事件的時間戳。"""
import asyncio, base64, json, subprocess, time, audioop, sys
import websockets

def kv(n):
    return subprocess.run(["az","keyvault","secret","show","--vault-name","agentic-sdk-models",
                           "--name",n,"--query","value","-o","tsv"],capture_output=True,text=True).stdout.strip()

KEY=kv("TRANSCRIBE-API-KEY"); DEP=kv("TRANSCRIBE-DEPLOYMENT-NAME")
URL=(f"wss://b2044-mrx9rt3z-eastus2.cognitiveservices.azure.com/openai/realtime"
     f"?api-version=2025-04-01-preview&deployment={DEP}&intent=transcription")

pcm24 = open("/tmp/speech.pcm","rb").read()
pcm16, _ = audioop.ratecv(pcm24, 2, 1, 24000, 16000, None)   # 服務要 16kHz
pcm16 = pcm16 + b"\x00" * (16000*2)   # 尾端補 1 秒靜音，讓 VAD 判定語句結束
CHUNK_MS = 100
BYTES = int(16000 * 2 * CHUNK_MS / 1000)

async def main():
    async with websockets.connect(URL, additional_headers={"api-key": KEY}, open_timeout=20, max_size=None) as ws:
        print("  已連線")
        await ws.send(json.dumps({"type":"transcription_session.update","session":{
            "input_audio_format":"pcm16",
            "input_audio_transcription":{"model":DEP,"language":"zh"},
            "turn_detection":{"type":"server_vad","threshold":0.5,"silence_duration_ms":300},
        }}))
        events=[]
        async def reader():
            async for raw in ws:
                d=json.loads(raw); t=d.get("type","")
                events.append((time.monotonic(), t, d))
                if t.endswith("completed") or t=="error": break
        task=asyncio.create_task(reader())
        await asyncio.sleep(0.3)
        t0=time.monotonic()
        for i in range(0, len(pcm16), BYTES):
            await ws.send(json.dumps({"type":"input_audio_buffer.append",
                                      "audio": base64.b64encode(pcm16[i:i+BYTES]).decode()}))
            await asyncio.sleep(CHUNK_MS/1000)          # 用真實語速送
        t_end=time.monotonic()
        print(f"  送完音訊（{(t_end-t0):.2f}s，模擬真實語速）")
        try: await asyncio.wait_for(task, timeout=25)
        except asyncio.TimeoutError: print("  等待逾時（可能仍在處理）")
        print("  事件時間軸（相對於開始說話）：")
        for ts,t,d in events:
            extra=""
            if "delta" in d: extra=f"  delta={d['delta']!r}"
            if "transcript" in d: extra=f"  transcript={str(d['transcript'])[:40]!r}"
            print(f"    +{ts-t0:6.2f}s  {t}{extra}")
asyncio.run(main())
