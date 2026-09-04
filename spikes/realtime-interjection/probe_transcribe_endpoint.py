"""探 Azure realtime WebSocket 端點：哪一種 URL 形式接得上。"""
import asyncio, json, subprocess, sys
import websockets

def kv(name):
    return subprocess.run(["az","keyvault","secret","show","--vault-name","agentic-sdk-models",
                           "--name",name,"--query","value","-o","tsv"],capture_output=True,text=True).stdout.strip()

KEY=kv("TRANSCRIBE-API-KEY"); DEP=kv("TRANSCRIBE-DEPLOYMENT-NAME")
HOST="b2044-mrx9rt3z-eastus2.cognitiveservices.azure.com"

CANDIDATES = [
 f"wss://{HOST}/openai/realtime?api-version=2025-04-01-preview&deployment={DEP}&intent=transcription",
 f"wss://{HOST}/openai/realtime?api-version=2024-10-01-preview&deployment={DEP}&intent=transcription",
 f"wss://{HOST}/openai/realtime?api-version=2025-04-01-preview&deployment={DEP}",
 f"wss://{HOST}/openai/realtime?api-version=2025-03-01-preview&deployment={DEP}&intent=transcription",
]

async def probe(url):
    try:
        async with websockets.connect(url, additional_headers={"api-key": KEY}, open_timeout=15) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            d = json.loads(msg)
            return f"連上  第一則: type={d.get('type')}"
    except Exception as e:
        return f"失敗  {type(e).__name__}: {str(e)[:110]}"

async def main():
    for url in CANDIDATES:
        tail = url.split("?",1)[1]
        print(f"  {tail[:78]}")
        print(f"     {await probe(url)}")

asyncio.run(main())
