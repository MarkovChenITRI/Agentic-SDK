"""Drive the voice page in a real browser and report what actually happened.

Everything else about the browser half is read, not run. This opens Chrome
with a fake microphone, loads the real module from the running Playground, and
reports four things that cannot be checked any other way: whether the
microphone opens, whether audio reaches the server, whether refusing
permission produces an explanation, and whether an interruption stops the
playback.

Not part of the test suite: it needs a browser and a listening port, and a
suite that needs those stops being run.

    .venv/bin/python spikes/realtime-interjection/verify_in_browser.py
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
CHROME_PORT = 9222
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
    """Just enough DevTools Protocol to load a page and run script in it."""

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
            "Runtime.evaluate",
            expression=expression,
            awaitPromise=True,
            returnByValue=True,
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"].get("text", "script failed"))
        return result["result"].get("value")


async def verify(browser: Browser, *, grant_microphone: bool) -> dict:
    await browser.call("Page.enable")
    await browser.call("Runtime.enable")
    await browser.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/playground/build")
    await asyncio.sleep(2)
    if not grant_microphone:
        # Chrome's fake device makes every request succeed. Refusing has to be
        # simulated, because a refusal is exactly what has never been tested.
        await browser.evaluate(
            "navigator.mediaDevices.getUserMedia = () =>"
            " Promise.reject(new DOMException('denied', 'NotAllowedError'));"
            "true"
        )
    return await browser.evaluate(
        """
        (async () => {
          // Wrapped before the module is imported, so every frame it sends and
          // every socket it opens is visible. Nothing is added to the module
          // for the sake of watching it.
          const sent = [];
          const sockets = [];
          const RealWebSocket = window.WebSocket;
          window.WebSocket = function (...args) {
            const socket = new RealWebSocket(...args);
            sockets.push(socket);
            const send = socket.send.bind(socket);
            socket.send = (frame) => {
              sent.push(typeof frame === 'string' ? frame : frame.byteLength);
              return send(frame);
            };
            return socket;
          };
          window.WebSocket.prototype = RealWebSocket.prototype;
          // The constants too: the module compares readyState against
          // WebSocket.OPEN, and a wrapper without it silently sends nothing.
          for (const name of ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED']) {
            window.WebSocket[name] = RealWebSocket[name];
          }

          const module = await import('/static/js/runner/voice-conversation.js');
          const page = document.createElement('div');
          page.dataset.voice = 'true';
          const said = [];
          const session = module.bindVoiceConversation(page, {
            onTranscript: (text) => said.push(['transcript', text]),
            onStatus: (message) => said.push(['status', message]),
          });
          await new Promise((done) => setTimeout(done, 2500));

          const microphoneFrames = sent.filter((frame) => typeof frame === 'number');
          let interjected = null;
          if (sockets.length) {
            // Hand the page a piece of synthesised audio, then tell it someone
            // started speaking — the two halves of an interruption.
            const audio = new Int16Array(24000);
            for (let index = 0; index < audio.length; index += 1) {
              audio[index] = Math.sin(index / 8) * 12000;
            }
            sockets[0].dispatchEvent(new MessageEvent('message', { data: audio.buffer }));
            await new Promise((done) => setTimeout(done, 300));
            sockets[0].dispatchEvent(
              new MessageEvent('message', { data: JSON.stringify({ type: 'speech_started' }) })
            );
            await new Promise((done) => setTimeout(done, 200));
            interjected = sent.filter(
              (frame) => typeof frame === 'string' && frame.includes('interject')
            );
          }

          return {
            sessionId: session ? session.sessionId : '',
            messages: said,
            audioState: window.__voiceContextState || '',
            microphoneFrames: microphoneFrames.length,
            microphoneBytes: microphoneFrames.reduce((total, size) => total + size, 0),
            interjected,
            resampled: Array.from(
              new Int16Array(module.toServiceAudio(new Float32Array([0, 0.5, -0.5, 1, -1, 2]), 48000))
            ),
          };
        })()
        """
    )


async def main() -> int:
    server = subprocess.Popen(
        [str(REPO / ".venv/bin/python"), "-m", "uvicorn", "playground.main:app", "--port", str(PORT)],
        cwd=REPO,
        env={**os.environ, "PLAYGROUND_TEST_MODE": "true"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    chrome = subprocess.Popen(
        [
            chrome_binary(),
            "--headless=new",
            f"--remote-debugging-port={CHROME_PORT}",
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            "--autoplay-policy=no-user-gesture-required",
            "--no-sandbox",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(5)
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{CHROME_PORT}/json").read())
        page = next(target for target in targets if target["type"] == "page")

        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=None) as socket:
            allowed = await verify(Browser(socket), grant_microphone=True)
            refused = await verify(Browser(socket), grant_microphone=False)

        print("── microphone allowed ──")
        for kind, text in allowed["messages"]:
            print(f"  {kind}: {text}")
        print(f"  session: {allowed['sessionId']}")
        print(f"  resampled 48k→16k: {allowed['resampled']}")
        print(f"  audio context: {allowed['audioState']}")
        print(f"  microphone frames sent: {allowed['microphoneFrames']} ({allowed['microphoneBytes']} bytes)")
        print(f"  interject after speech_started: {allowed['interjected']}")
        print("── microphone refused ──")
        for kind, text in refused["messages"]:
            print(f"  {kind}: {text}")
        return 0
    finally:
        for process in (chrome, server):
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
