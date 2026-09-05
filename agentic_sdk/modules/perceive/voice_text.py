"""Perceive that listens as well as reads.

The module contract is one call, one return: the workflow asks perceive for
this turn's input and moves on. Speech does not fit that on its own, because
the audio arrives whenever the person feels like talking, not when the workflow
asks. What makes it fit is that a module is an object the workflow keeps, so it
outlives any single turn — it can hold a live session and hand over whatever it
has heard when its turn comes round.

It hears; it does not speak. Speaking is an action, and the two directions
never shared a connection anyway. See docs/adr/0001-where-voice-lives.md.
"""

from __future__ import annotations

from typing import Any

from agentic_sdk.audio.speech_gate import (
    DEFAULT_HANGOVER_CHUNKS,
    DEFAULT_SPEECH_THRESHOLD,
    SpeechGate,
)
from agentic_sdk.audio.transport import AudioInputTransport, require_speech_endpoint
from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput, WorkflowState


class VoiceTextPerceive:
    name = "perceive"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        language: str = "zh",
        transport: AudioInputTransport | None = None,
        speech_threshold: int = DEFAULT_SPEECH_THRESHOLD,
        hangover_chunks: int = DEFAULT_HANGOVER_CHUNKS,
    ) -> None:
        """Listen on the given speech endpoint, or through a transport of your own.

        ``transport`` exists so a test can drive a whole conversation without a
        network or a credential. Leave it out and the endpoint settings build
        the real one, which is how the module is normally used — the shape then
        matches every other module: api_key, base_url, model.
        """
        if transport is None:
            # Checked before the import so a caller who forgot the endpoint is
            # told that, rather than being told about a module they have never
            # heard of.
            require_speech_endpoint(api_key=api_key, base_url=base_url, model=model)
            from agentic_sdk.audio.azure_realtime import AzureRealtimeInput

            transport = AzureRealtimeInput(
                api_key=api_key, base_url=base_url, model=model, language=language
            )
        self.transport = transport
        self._gate = SpeechGate(threshold=speech_threshold, hangover_chunks=hangover_chunks)
        self._heard: list[str] = []
        self._spoken = False
        self._cancel: Any = None
        transport.on_transcript(self._remember)
        transport.on_speech_started(self._interrupt)

    # ── the workflow's view ─────────────────────────────────────────────

    def __call__(self, state: WorkflowState) -> ModuleOutput:
        # Whatever the workflow recorded as this turn's message is the turn's
        # message, spoken or typed. Preferring what was heard over what the
        # caller passed would leave the conversation record and the perceived
        # input disagreeing about what was said.
        # The token belongs to the run, not to this module's turn in it. Held
        # so the listener can stop a later module — an answer being spoken over
        # is not this module's turn any more.
        self._cancel = state.cancel
        content = state.latest_user_message().strip()
        spoken, self._spoken = self._spoken, False
        self._heard.clear()
        return ModuleOutput(
            next_module="retrieve",
            payload={"perceived_input": content, "query": content},
            context_updates=[
                ContextEntry(
                    type=ContextEntryType.PERCEIVED,
                    content=content,
                    metadata={"source": "voice_text_perceive", "spoken": spoken},
                )
            ],
        )

    # ── the caller's view ───────────────────────────────────────────────

    def pending_input(self) -> str:
        """What has been heard and is waiting for a turn to carry it.

        Taking it marks the coming turn as spoken, so the perceived entry says
        where its content came from without having to compare strings.
        """
        waiting = " ".join(self._heard).strip()
        if waiting:
            self._spoken = True
        return waiting

    def hear(self, pcm16: bytes) -> None:
        """Offer a chunk of microphone audio. Quiet chunks go no further."""
        if self._gate.should_send(pcm16):
            self.transport.send(pcm16)

    def close(self) -> None:
        self.transport.close()

    # ── the transport's view ────────────────────────────────────────────

    def _interrupt(self) -> None:
        """Someone started talking. Whatever is being said is no longer wanted.

        Fired on voice activity rather than on words, because the words take
        nearly four seconds to arrive and the answer would still be going.
        """
        token = self._cancel
        if token is not None and not token.cancelled:
            token.cancel("interjection")

    def _remember(self, text: str) -> None:
        cleaned = str(text or "").strip()
        if cleaned:
            self._heard.append(cleaned)
