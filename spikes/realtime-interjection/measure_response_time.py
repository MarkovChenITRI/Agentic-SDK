"""How long a voice agent takes to answer something it already knows.

Reports the parts separately, because they are paid at different places: the
service deciding an utterance ended, the model producing the spoken half, and
the synthesis returning its first bytes. Only the last two are ours.

    .venv/bin/python spikes/realtime-interjection/measure_response_time.py <question.wav>
"""

from __future__ import annotations

import asyncio
import base64
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
    def __init__(self, socket, shots: Path) -> None:
        self._socket = socket
        self._next_id = 0
        self._shots = shots
        self._taken = 0

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

    async def shoot(self, name: str) -> Path:
        self._taken += 1
        shot = await self.call("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        path = self._shots / f"{self._taken:02d}-{name}.png"
        path.write_bytes(base64.b64decode(shot["data"]))
        print(f"  📷 {path.name}")
        return path


CLICK_CHOICE = """
(() => {
  const card = document.querySelector(
    '[data-choice-card][data-step-key="%s"][data-choice-label="%s"]'
  );
  if (!card) { return 'no card'; }
  card.scrollIntoView({block: 'center'});
  card.click();
  return card.innerText.trim().split('\\n').slice(0, 2).join(' / ');
})()
"""

NEXT_STEP = """
(() => {
  const next = Array.from(document.querySelectorAll('[data-step-continue]'))
    .find((button) => button.offsetParent !== null && !button.disabled);
  if (!next) { return 'no next'; }
  next.click();
  return 'next';
})()
"""

VISIBLE_QUESTION = """
(() => {
  const heading = Array.from(document.querySelectorAll('h1, h2'))
    .find((node) => node.offsetParent !== null && node.innerText.trim().startsWith('Q'));
  return heading ? heading.innerText.trim().replace(/\\s+/g, ' ') : '(看不到題目)';
})()
"""

BIND_ENDPOINTS = """
(() => {
  const chosen = {};
  document.querySelectorAll('[data-builder-endpoint-select]').forEach((select) => {
    const wanted = {transcribe: 'transcribe', tts: 'tts'}[select.name] || 'gpt-54';
    const option = Array.from(select.options).find((o) => o.value === wanted)
      || Array.from(select.options).find((o) => o.value);
    if (option) {
      select.value = option.value;
      chosen[select.name] = option.textContent;
      select.dispatchEvent(new Event('change', {bubbles: true}));
    }
  });
  return chosen;
})()
"""


WATCH_THE_CONVERSATION = """
window.__marks = [];
window.__audioOut = [];
const mark = (label) => window.__marks.push([label, Math.round(performance.now())]);
const realFetch = window.fetch;
window.fetch = async (...args) => {
  const url = String(args[0]);
  if (url.includes('execute')) { mark('run.start'); }
  const response = await realFetch(...args);
  if (url.includes('execute')) { mark('run.responded'); }
  return response;
};
const RealWebSocket = window.WebSocket;
window.WebSocket = function (...args) {
  const socket = new RealWebSocket(...args);
  socket.addEventListener('message', (event) => {
    if (typeof event.data === 'string') {
      const kind = JSON.parse(event.data).type;
      if (kind === 'speech_started' || kind === 'transcript' || kind === 'spoken') {
        mark('ws.' + kind);
      }
    } else {
      if (!window.__audioOut.length) { mark('audio.first'); }
      window.__audioOut.push(event.data.byteLength);
    }
  });
  return socket;
};
window.WebSocket.prototype = RealWebSocket.prototype;
for (const name of ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED']) {
  window.WebSocket[name] = RealWebSocket[name];
}
"""


def report(marks) -> None:
    """The three waits a person actually feels, named for what they are."""
    at = {}
    for label, when in marks:
        at.setdefault(label, when)
    rounds = []
    for label, when in marks:
        if label == "ws.transcript":
            rounds.append({"transcript": when})
        elif rounds:
            rounds[-1].setdefault(label, when)
    print("── 每一輪 ──")
    for index, round_ in enumerate(rounds, start=1):
        transcript = round_.get("transcript")
        started = round_.get("run.start")
        audio = round_.get("audio.first")
        done = round_.get("ws.spoken")
        if transcript is None:
            continue
        parts = [f"第 {index} 輪"]
        if started is not None:
            parts.append(f"轉寫→送出 {started - transcript}ms")
        if audio is not None:
            parts.append(f"轉寫→第一個聲音 {audio - transcript}ms")
        if done is not None:
            parts.append(f"轉寫→說完 {done - transcript}ms")
        print("  " + " | ".join(parts))


WATCH_THE_CONVERSATION = """
window.__marks = [];
window.__audioOut = [];
const mark = (label) => window.__marks.push([label, Math.round(performance.now())]);
const realFetch = window.fetch;
window.fetch = async (...args) => {
  const url = String(args[0]);
  if (url.includes('execute')) { mark('run.start'); }
  const response = await realFetch(...args);
  if (url.includes('execute')) { mark('run.responded'); }
  return response;
};
const RealWebSocket = window.WebSocket;
window.WebSocket = function (...args) {
  const socket = new RealWebSocket(...args);
  socket.addEventListener('message', (event) => {
    if (typeof event.data === 'string') {
      const kind = JSON.parse(event.data).type;
      if (kind === 'speech_started' || kind === 'transcript' || kind === 'spoken') {
        mark('ws.' + kind);
      }
    } else {
      if (!window.__audioOut.length) { mark('audio.first'); }
      window.__audioOut.push(event.data.byteLength);
    }
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
    shots = Path("/tmp")

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
            "--window-size=1280,1600",
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
            browser = Browser(socket, shots)
            await browser.call("Page.enable")
            await browser.call("Runtime.enable")
            await browser.call(
                "Emulation.setDeviceMetricsOverride",
                width=1280, height=1600, deviceScaleFactor=1, mobile=False,
            )

            print("── Builder：建一個語音 agent ──")
            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/builder")
            await asyncio.sleep(4)


            for step, choice, caption in [
                ("memory_type", "in_context", "memory"),
                ("input_type", "voice", "input-voice"),
                ("retrieve_policy", "none", "retrieve-none"),
                ("output_format", "voice", "output-voice"),
                ("failure_policy", "retry", "failure-retry"),
            ]:
                await browser.evaluate(CLICK_CHOICE % (step, choice))
                await asyncio.sleep(1.5)
                await browser.evaluate(NEXT_STEP)
                await asyncio.sleep(2)

            question = await browser.evaluate(VISIBLE_QUESTION)
            print(f"  {question}")

            await asyncio.sleep(2)
            bound = await browser.evaluate(BIND_ENDPOINTS)
            await asyncio.sleep(3)
            print(f"  綁定部署: {bound}")


            ready = await browser.evaluate(
                "document.querySelectorAll('[data-review-item].is-complete').length"
                " + '/' + document.querySelectorAll('[data-review-item]').length"
            )
            print(f"  檢查表: {ready}")

            print("── Runner：問一句不需要查資料的問題 ──")
            await browser.call(
                "Page.addScriptToEvaluateOnNewDocument", source=WATCH_THE_CONVERSATION
            )
            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/run")
            for _ in range(60):
                await asyncio.sleep(1)
            marks = await browser.evaluate("window.__marks || []")
            thread = await browser.evaluate(
                "document.querySelector('[data-result-thread]')?.innerText?.slice(0, 300) || ''"
            )

            print("── 事件時間軸（毫秒，頁面載入起算）──")
            for label, at in marks:
                print(f"  {at:>7} {label}")
            report(marks)
            print("── 畫面上的回覆 ──")
            print(thread)
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
