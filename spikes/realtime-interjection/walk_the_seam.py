"""Walk a person through building and using a voice agent, and photograph it.

Every screenshot is the real Playground: real choices clicked in the Builder,
real deployments bound, real microphone audio, real transcription, real
synthesis. Nothing here is a stand-in for anything.

    .venv/bin/python spikes/realtime-interjection/walk_the_seam.py <microphone.wav> <output dir>
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


async def main() -> int:
    microphone = Path(sys.argv[1]).resolve()
    shots = Path(sys.argv[2]).resolve()
    shots.mkdir(parents=True, exist_ok=True)
    for old in shots.glob("*.png"):
        old.unlink()

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

            print("── Builder：使用者一步一步選 ──")
            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/builder")
            await asyncio.sleep(4)
            await browser.shoot("builder-opened")

            for step, choice, caption in [
                ("memory_type", "in_context", "memory"),
                ("input_type", "voice", "input-voice"),
                ("retrieve_policy", "none", "retrieve-none"),
                ("output_format", "voice", "output-voice"),
                ("failure_policy", "retry", "failure-retry"),
            ]:
                question = await browser.evaluate(VISIBLE_QUESTION)
                clicked = await browser.evaluate(CLICK_CHOICE % (step, choice))
                await asyncio.sleep(1.5)
                print(f"  {question}")
                print(f"    → 選「{clicked}」")
                await browser.shoot(f"chose-{caption}")
                await browser.evaluate(NEXT_STEP)
                await asyncio.sleep(2)

            question = await browser.evaluate(VISIBLE_QUESTION)
            print(f"  {question}")
            await browser.shoot("review-before-binding")
            await asyncio.sleep(2)
            bound = await browser.evaluate(BIND_ENDPOINTS)
            await asyncio.sleep(3)
            print(f"  綁定部署: {bound}")
            await browser.shoot("bound-deployments")

            incomplete = await browser.evaluate(
                "Array.from(document.querySelectorAll('[data-review-item]'))"
                ".filter((i) => !i.classList.contains('is-complete'))"
                ".map((i) => i.innerText.replace(/\\s+/g, ' ').slice(0, 90))"
            )
            for row in incomplete:
                print(f"    未完成: {row}")
            ready = await browser.evaluate(
                "document.querySelectorAll('[data-review-item].is-complete').length"
                " + '/' + document.querySelectorAll('[data-review-item]').length"
            )
            print(f"  檢查表: {ready}")

            print("── Runner：使用者開口說話 ──")
            await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/run")
            await asyncio.sleep(5)
            await browser.shoot("runner-listening")

            seen_states = []
            for second in range(40):
                await asyncio.sleep(1)
                state = await browser.evaluate(
                    "document.querySelector('[data-voice-bar]')?.dataset.voiceState + '|'"
                    " + (document.querySelector('[data-voice-state-text]')?.textContent || '')"
                    " + ' | init=' + (document.querySelector('[data-initialization-message]')?.textContent || '')"
                    " + ' | overlay=' + document.querySelector('[data-initialization-overlay]')?.hidden"
                )
                if not seen_states or seen_states[-1] != state:
                    seen_states.append(state)
                    print(f"  {second:>2}s 語音列: {state}")
                if second in (9, 15, 25):
                    spectrum = await browser.evaluate(
                        "Array.from(document.querySelectorAll('[data-voice-spectrum] i'))"
                        ".map((bar) => Number((bar.style.transform.match(/[\\d.]+/) || [0])[0]).toFixed(2))"
                        ".join(' ')"
                    )
                    print(f"  {second:>2}s 頻譜: {spectrum}")
                if second == 9:
                    await browser.shoot("heard-the-question")
                if second == 16:
                    await browser.shoot("answering-aloud")
                if second == 26:
                    await browser.shoot("after-the-interruption")
                if second == 36:
                    await browser.evaluate(
                        "document.querySelector('[data-voice-toggle=\"voice\"]')?.click() || true"
                    )
                    await asyncio.sleep(1)
                    await browser.shoot("back-to-voice")
                if second == 32:
                    await browser.evaluate(
                        "document.querySelector('[data-voice-toggle=\"text\"]')?.click() || true"
                    )
                    await asyncio.sleep(1)
                    await browser.shoot("switched-to-typing")

            state = await browser.evaluate(
                "({status: document.querySelector('[data-run-status]')?.textContent || '',"
                " thread: document.querySelector('[data-result-thread]')?.innerText?.slice(0, 500) || ''})"
            )
            print(f"  狀態列: {state['status']}")
            print("── 畫面上的對話 ──")
            print(state["thread"])
            await browser.shoot("conversation")
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
