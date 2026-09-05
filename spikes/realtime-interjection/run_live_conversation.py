"""Hold a real voice conversation in the local Playground, end to end.

Nothing here is a stand-in. The microphone is a WAV of speech synthesised by
the real deployment, the transcription is the real deployment, the answer comes
from the real model, and the reply is spoken by the real deployment and played
in a real browser. The point is the thing the tests cannot show: that someone
can talk to an agent in the runner and cut it off mid-sentence.

    .venv/bin/python spikes/realtime-interjection/run_live_conversation.py <microphone.wav>
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets


PORT = 8099
CHROME_PORT = 9223
REPO = Path(__file__).resolve().parents[2]


def chrome_binary() -> str:
    cached = sorted(Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux64/chrome"))
    if cached:
        return str(cached[-1])
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if found := shutil.which(name):
            return found
    raise SystemExit("no chrome on this machine")


class Browser:
    def __init__(self, socket) -> None:
        self._socket = socket
        self._next_id = 0

    async def call(self, method: str, **params):
        self._next_id += 1
        await self._socket.send(json.dumps({"id": self._next_id, "method": method, "params": params}))
        while True:
            message = json.loads(await self._socket.recv())
            if message.get("id") == self._next_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    async def evaluate(self, expression: str):
        result = await self.call(
            "Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"].get("text", "script failed"))
        return result["result"].get("value")


BUILD_A_VOICE_AGENT = """
(async () => {
  const post = async (path, body) => {
    const response = await fetch(path, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    return {status: response.status, body: await response.json().catch(() => ({}))};
  };
  const steps = [
    ['memory_type', 'in_context'],
    ['input_type', 'voice'],
    ['retrieve_policy', 'none'],
    ['output_format', 'voice'],
    ['failure_policy', 'retry'],
  ];
  const answered = [];
  for (const [step, choice] of steps) {
    answered.push([step, (await post('/playground/builder/state', {step, choice})).status]);
  }
  const keywords = {status: 0};
  const bound = await post('/playground/builder/endpoints', {
    selections: {action: 'gpt-54', plan: 'gpt-54', reflect: 'gpt-54', perceive: 'gpt-54',
                 retrieve: 'embedded-large', transcribe: 'transcribe', tts: 'tts'},
  });
  return {answered, keywords: keywords.status, bound: bound.status, ready: bound.body.builder_review_ready,
          review: (bound.body.builder_review_state || []).map((item) => [item.title || item.key || '?', item.ready, item.detail || item.value || '']),
          configured: bound.body.configured_roles};
})()
"""

WATCH_THE_CONVERSATION = """
window.__errors = [];
window.addEventListener('error', (event) => window.__errors.push(String(event.message)));
window.addEventListener('unhandledrejection', (event) => window.__errors.push('rejected: ' + event.reason));
window.__seen = [];
window.__audioIn = [];
window.__audioOut = [];
window.__fetches = [];
const realFetch = window.fetch;
window.fetch = async (...args) => {
  const url = String(args[0]);
  try {
    const response = await realFetch(...args);
    if (url.includes('execute')) { window.__fetches.push([url, response.status]); }
    return response;
  } catch (error) {
    window.__fetches.push([url, 'threw: ' + error]);
    throw error;
  }
};
const RealWebSocket = window.WebSocket;
window.WebSocket = function (...args) {
  const socket = new RealWebSocket(...args);
  const send = socket.send.bind(socket);
  socket.send = (frame) => {
    if (typeof frame === 'string') { window.__seen.push(['sent', frame]); }
    else { window.__audioIn.push(frame.byteLength); }
    return send(frame);
  };
  socket.addEventListener('message', (event) => {
    if (typeof event.data === 'string') { window.__seen.push(['recv', event.data]); }
    else { window.__audioOut.push(event.data.byteLength); }
  });
  return socket;
};
window.WebSocket.prototype = RealWebSocket.prototype;
for (const name of ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED']) {
  window.WebSocket[name] = RealWebSocket[name];
}
"""



async def main() -> int:
    microphone = Path(sys.argv[1]).resolve()
    if not microphone.exists():
        raise SystemExit(f"no microphone track at {microphone}")

    server = subprocess.Popen(
        [str(REPO / ".venv/bin/python"), "-m", "uvicorn", "playground.main:app", "--port", str(PORT)],
        cwd=REPO,
        env={key: value for key, value in os.environ.items() if key != "PLAYGROUND_TEST_MODE"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    chrome = subprocess.Popen(
        [
            chrome_binary(),
            "--headless=new",
            f"--remote-debugging-port={CHROME_PORT}",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-audio-capture={microphone}",
            "--autoplay-policy=no-user-gesture-required",
            "--no-sandbox",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(10)
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{CHROME_PORT}/json").read())
        page = next(target for target in targets if target["type"] == "page")

        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=None) as socket:
            browser = Browser(socket)
            await browser.call("Page.enable")
            await browser.call("Runtime.enable")

            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/build")
            await asyncio.sleep(4)
            built = await browser.evaluate(BUILD_A_VOICE_AGENT)
            print("── 建一個語音 agent ──")
            print(f"  builder steps : {built['answered']}")
            print(f"  keywords      : {built['keywords']}")
            print(f"  endpoints     : {built['bound']}  ready={built['ready']}  configured={built['configured']}")
            for row in built["review"]:
                print(f"    review: {row}")

            await browser.call(
                "Page.addScriptToEvaluateOnNewDocument", source=WATCH_THE_CONVERSATION
            )
            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/run")
            await asyncio.sleep(3)

            probe = await browser.evaluate(
                "({voice: document.querySelector(\"[data-page='runner']\")?.dataset.voice,"
                " url: location.pathname,"
                " errors: (window.__errors||[]).slice(0,5),"
                " moduleFetch: 0, hasMedia: typeof navigator.mediaDevices,"
                " secure: window.isSecureContext,"
                " statusEl: !!document.querySelector('[data-run-status]')})"
            )
            print(f"  runner 頁面: {probe}")
            direct = await browser.evaluate(
                """
                (async () => {
                  try {
                    const module = await import('/static/js/runner/voice-conversation.js');
                    return {loaded: true, bound: typeof module.bindVoiceConversation};
                  } catch (error) {
                    return {loaded: false, why: String(error)};
                  }
                })()
                """
            )
            print(f"  模組載入: {direct}")
            dom = await browser.evaluate(
                "({script: !!document.querySelector(\"script[src*='runner-page']\"),"
                " composer: !!document.querySelector('[data-input-composer]'),"
                " overlay: !!document.querySelector('[data-initialization-overlay]'),"
                " overlayHidden: document.querySelector('[data-initialization-overlay]')?.hidden,"
                " landmarks: Array.from(document.querySelectorAll('[data-page]')).map(e=>e.dataset.page)})"
            )
            print(f"  頁面骨架: {dom}")
            print("── 對話中（45 秒）──")
            for second in range(45):
                await asyncio.sleep(1)
                if second in (5, 10, 20, 44):
                    state = await browser.evaluate(
                        "({overlay: document.querySelector('[data-initialization-overlay]')?.hidden,"
                        " message: document.querySelector('[data-initialization-message]')?.textContent || ''})"
                    )
                    print(f"  {second:>2}s 初始化: {state}")

            traffic = await browser.evaluate(
                "({seen: window.__seen || [], audioIn: (window.__audioIn||[]).length,"
                " audioOut: (window.__audioOut||[]).reduce((a,b)=>a+b,0),"
                " status: document.querySelector('[data-run-status]')?.textContent || '',"
                " reply: document.querySelector('[data-result-thread]')?.innerText?.slice(0,400) || '',"
                " fetches: window.__fetches || [], errors: (window.__errors||[]).slice(0,6)})"
            )
            print(f"  麥克風音框送出 : {traffic['audioIn']}")
            print(f"  收到合成音訊   : {traffic['audioOut']} bytes")
            print(f"  畫面狀態       : {traffic['status']}")
            print(f"  執行請求       : {traffic['fetches']}")
            print(f"  頁面錯誤       : {traffic['errors']}")
            interesting = [(k, f) for k, f in traffic["seen"] if '"listening"' not in f]
            print(f"  （另有 {len(traffic['seen']) - len(interesting)} 則 listening 回報）")
            for kind, frame in interesting[:30]:
                print(f"  {kind}: {frame[:200]}")
            print("── 畫面上的回覆 ──")
            print(traffic["reply"][:400])
        return 0
    finally:
        for process in (chrome, server):
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
