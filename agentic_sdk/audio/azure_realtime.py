"""The real input transport: a live transcription session over a websocket.

Kept apart from the module that uses it so the module can be driven by a fake,
and so the protocol details — which are the fiddly part — live in one place.

Two of those details cost an afternoon each when the spike first hit them, and
are guarded here rather than left for the next person:

- ``intent=transcription`` is not optional. Without it the socket opens and
  then answers every message with an error.
- An utterance is only transcribed once the service hears silence after it.
  Audio that stops dead never finishes, and looks exactly like a hung
  connection. A caller that gates on loudness must let the quiet tail through,
  which is what the speech gate's hangover is for.
"""

from __future__ import annotations

import asyncio
import base64
import json
import threading
from typing import Callable
from urllib.parse import urlencode, urlparse, urlunparse


class AzureRealtimeInput:
    """Streams microphone audio to a transcription deployment and reports back."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        language: str = "zh",
        api_version: str = "2025-04-01-preview",
        connect_timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._language = language
        self._url = _realtime_url(base_url, deployment=model, api_version=api_version)

        self._speech_started: list[Callable[[], None]] = []
        self._transcript: list[Callable[[str], None]] = []
        self._outgoing: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._failure: BaseException | None = None

        self._thread = threading.Thread(target=self._run, name="azure-realtime-input", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=connect_timeout):
            raise TimeoutError("speech service did not accept the connection in time")
        if self._failure is not None:
            raise self._failure

    # ── AudioInputTransport ─────────────────────────────────────────────

    def send(self, pcm16: bytes) -> None:
        if self._loop is None or self._outgoing is None or not pcm16:
            return
        asyncio.run_coroutine_threadsafe(self._outgoing.put(pcm16), self._loop)

    def on_speech_started(self, callback: Callable[[], None]) -> None:
        self._speech_started.append(callback)

    def on_transcript(self, callback: Callable[[str], None]) -> None:
        self._transcript.append(callback)

    def close(self) -> None:
        if self._loop is not None and self._outgoing is not None:
            asyncio.run_coroutine_threadsafe(self._outgoing.put(None), self._loop)

    # ── the session ─────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            asyncio.run(self._session())
        except BaseException as error:  # noqa: BLE001 - reported to the constructor
            self._failure = error
            self._ready.set()

    async def _session(self) -> None:
        import websockets

        self._loop = asyncio.get_running_loop()
        self._outgoing = asyncio.Queue()
        async with websockets.connect(
            self._url, additional_headers={"api-key": self._api_key}, max_size=None
        ) as socket:
            await socket.send(
                json.dumps(
                    {
                        "type": "transcription_session.update",
                        "session": {
                            "input_audio_format": "pcm16",
                            "input_audio_transcription": {
                                "model": self._model,
                                "language": self._language,
                            },
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "silence_duration_ms": 300,
                            },
                        },
                    }
                )
            )
            self._ready.set()
            await asyncio.gather(self._send_loop(socket), self._receive_loop(socket))

    async def _send_loop(self, socket) -> None:
        assert self._outgoing is not None
        while True:
            chunk = await self._outgoing.get()
            if chunk is None:
                await socket.close()
                return
            await socket.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }
                )
            )

    async def _receive_loop(self, socket) -> None:
        async for raw in socket:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            kind = str(event.get("type") or "")
            if kind == "input_audio_buffer.speech_started":
                _fan_out(self._speech_started)
            elif kind.endswith("transcription.completed"):
                text = str(event.get("transcript") or "").strip()
                if text:
                    _fan_out(self._transcript, text)


def _fan_out(callbacks: list, *args) -> None:
    for callback in list(callbacks):
        callback(*args)


def _realtime_url(base_url: str, *, deployment: str, api_version: str) -> str:
    """Build the websocket address from whatever form of endpoint was given.

    Callers hold their speech endpoint in different shapes — the bare resource,
    or the REST path a transcription request goes to — and both should work
    rather than only the one whoever wrote the config happened to store.
    """
    parsed = urlparse(base_url.strip())
    scheme = "wss" if parsed.scheme in {"https", "wss", ""} else "ws"
    query = urlencode(
        {"api-version": api_version, "deployment": deployment, "intent": "transcription"}
    )
    return urlunparse((scheme, parsed.netloc, "/openai/realtime", "", query, ""))
