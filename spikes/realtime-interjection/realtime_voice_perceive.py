"""A perceive module that keeps listening after it has returned.

The module contract is one call, one return: the workflow asks perceive for
this turn's input and moves on to plan. Simultaneous voice needs the opposite —
something that is still listening while the action module is three paragraphs
into an answer, and that can stop it.

The contract turns out to hold both. A module is an object the workflow keeps,
so it outlives any single turn and can own a live audio session. And the
cancellation token is one object for the whole run, so the token this module
receives while it is perceiving is the same token that will stop the action
module later. Capture it on the way past, hand it to the listener, and the
listener can interrupt a turn it is no longer part of.

Nothing here belongs in the SDK yet: it holds a websockets dependency and an
event loop of its own. It exists to answer whether the shape is possible.
"""

from __future__ import annotations

import asyncio
import base64
import json
import threading
import time
from typing import Any

from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput, WorkflowState


class RealtimeVoicePerceive:
    name = "perceive"

    def __init__(
        self,
        *,
        websocket_url: str,
        api_key: str,
        deployment: str,
        language: str = "zh",
        on_event: "Any" = None,
    ) -> None:
        self._url = websocket_url
        self._api_key = api_key
        self._deployment = deployment
        self._language = language
        self._on_event = on_event

        self._heard: list[str] = []
        self._pending_audio: asyncio.Queue | None = None
        self._lock = threading.Lock()
        self._cancel_token: Any = None
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = threading.Thread(target=self._run_session, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=30)

    # ── the workflow's view: one call, one return ──────────────────────────

    def __call__(self, state: WorkflowState) -> ModuleOutput:
        # The token belongs to the run, not to this module's turn in it. Held
        # here so the listener can stop the action module further down.
        with self._lock:
            self._cancel_token = state.cancel
            spoken = " ".join(self._heard).strip()
            self._heard.clear()

        content = spoken or state.latest_user_message().strip()
        return ModuleOutput(
            next_module="retrieve",
            payload={"perceived_input": content, "query": content},
            context_updates=[
                ContextEntry(
                    type=ContextEntryType.PERCEIVED,
                    content=content,
                    metadata={"source": "realtime_voice_perceive", "spoken": bool(spoken)},
                )
            ],
        )

    # ── the caller's view: audio goes in whenever it arrives ───────────────

    def send_audio(self, pcm16_16khz: bytes) -> None:
        if self._loop is None or self._pending_audio is None:
            return
        asyncio.run_coroutine_threadsafe(self._pending_audio.put(pcm16_16khz), self._loop)

    def close(self) -> None:
        if self._loop is not None and self._pending_audio is not None:
            asyncio.run_coroutine_threadsafe(self._pending_audio.put(None), self._loop)

    # ── the listener: alive for as long as the module is ───────────────────

    def _run_session(self) -> None:
        asyncio.run(self._session())

    async def _session(self) -> None:
        import websockets

        self._loop = asyncio.get_running_loop()
        self._pending_audio = asyncio.Queue()
        async with websockets.connect(
            self._url, additional_headers={"api-key": self._api_key}, open_timeout=20, max_size=None
        ) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "transcription_session.update",
                        "session": {
                            "input_audio_format": "pcm16",
                            "input_audio_transcription": {"model": self._deployment, "language": self._language},
                            "turn_detection": {"type": "server_vad", "threshold": 0.5, "silence_duration_ms": 300},
                        },
                    }
                )
            )
            self._ready.set()
            await asyncio.gather(self._pump(ws), self._listen(ws))

    async def _pump(self, ws) -> None:
        assert self._pending_audio is not None
        while True:
            chunk = await self._pending_audio.get()
            if chunk is None:
                return
            await ws.send(
                json.dumps({"type": "input_audio_buffer.append", "audio": base64.b64encode(chunk).decode()})
            )

    async def _listen(self, ws) -> None:
        async for raw in ws:
            event = json.loads(raw)
            kind = event.get("type", "")
            if self._on_event is not None:
                self._on_event(kind, event)

            if kind == "input_audio_buffer.speech_started":
                # The whole point. Someone started talking; whatever this
                # workflow is in the middle of saying is no longer wanted, and
                # waiting for the words would take another three seconds.
                self._interrupt()
            elif kind.endswith("transcription.completed"):
                text = str(event.get("transcript") or "").strip()
                if text:
                    with self._lock:
                        self._heard.append(text)

    def _interrupt(self) -> None:
        with self._lock:
            token = self._cancel_token
        if token is not None and not token.cancelled:
            token.cancel("interjection", heard_at=time.monotonic())
