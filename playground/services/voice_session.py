"""Finding a running answer from outside the request that started it.

The person speaking and the workflow answering are on different connections:
one is a websocket carrying audio, the other an HTTP request streaming a reply.
The interjection arrives on the first and has to stop something running on the
second, so the two need a name in common.

They share a process, which is what makes this a dictionary rather than
infrastructure — and why the Playground refuses to start with more than one
worker. Across processes the interjection would land somewhere the workflow
is not, and nothing would report it.
"""

from __future__ import annotations

import threading

from agentic_sdk.audio.transport import AudioInputTransport
from agentic_sdk.core.cancellation import CancellationToken
from agentic_sdk.modules.perceive.voice_text import VoiceTextPerceive


class VoiceSessionRegistry:
    """Which answer belongs to which listening session."""

    def __init__(self) -> None:
        self._tokens: dict[str, CancellationToken] = {}
        self._listeners: dict[str, VoiceTextPerceive] = {}
        self._lock = threading.Lock()

    def listen(self, session_id: str, transport: AudioInputTransport) -> VoiceTextPerceive:
        """Give this session somewhere to send its microphone.

        The listening module rather than the raw transport, because the gate in
        front of it is the thing standing between a quiet room and a stream of
        words nobody said.
        """
        listener = VoiceTextPerceive(transport=transport)
        with self._lock:
            self._listeners[str(session_id)] = listener
        return listener

    def listener(self, session_id: str) -> VoiceTextPerceive | None:
        with self._lock:
            return self._listeners.get(str(session_id))

    def open(self, session_id: str) -> CancellationToken:
        """Start a session, replacing any answer still running under that name.

        A reload opens the same session again. Leaving the first one registered
        would strand an answer nobody can reach and nobody is listening to.
        """
        token = CancellationToken()
        with self._lock:
            self._tokens[str(session_id)] = token
        return token

    def interject(self, session_id: str, *, heard_seconds: float | None) -> bool:
        """Stop this session's answer. False if there is nothing to stop.

        ``heard_seconds`` is how long the person actually listened, which only
        whatever is playing the audio knows: speech lags generation, so it is
        not how much was written. ``None`` when the interruption was noticed
        somewhere that cannot know — the transcription service hears someone
        begin, but has never played a note. Unknown has to stay unknown:
        reporting nought there would erase an answer the person did hear.
        """
        with self._lock:
            token = self._tokens.get(str(session_id))
        if token is None:
            return False
        token.cancel(
            "interjection",
            heard_seconds=None if heard_seconds is None else float(heard_seconds),
        )
        return True

    def close(self, session_id: str) -> None:
        with self._lock:
            self._tokens.pop(str(session_id), None)
            listener = self._listeners.pop(str(session_id), None)
        if listener is not None:
            # The transcription session bills for as long as it is open, and
            # nobody is on the other end of this one any more.
            listener.close()

    def token(self, session_id: str) -> CancellationToken | None:
        with self._lock:
            return self._tokens.get(str(session_id))


def open_transcription() -> AudioInputTransport | None:
    """Start a transcription session on the configured endpoint, if there is one.

    Returns nothing when no speech endpoint is configured, so the page can say
    so — an agent that silently never hears anything looks like a broken
    microphone, and the person spends the next minute talking louder.
    """
    from playground.services.key_vault_config import key_vault_settings

    endpoint = next(
        (item for item in key_vault_settings().speech_endpoints if item.id == "transcribe"),
        None,
    )
    if endpoint is None:
        return None
    from agentic_sdk.audio.azure_realtime import AzureRealtimeInput

    return AzureRealtimeInput(
        api_key=endpoint.api_key,
        base_url=endpoint.endpoint,
        model=endpoint.deployment_name,
    )


def open_synthesis():
    """Start a synthesis session on the configured endpoint, if there is one."""
    from playground.services.key_vault_config import key_vault_settings

    endpoint = next(
        (item for item in key_vault_settings().speech_endpoints if item.id == "tts"),
        None,
    )
    if endpoint is None:
        return None
    from agentic_sdk.audio.azure_speech import AzureSpeechOutput

    return AzureSpeechOutput(
        api_key=endpoint.api_key,
        base_url=endpoint.endpoint,
        model=endpoint.deployment_name,
    )


def speech_unavailable_message() -> str:
    return "這個 Playground 還沒有設定語音服務，所以聽不到你說話。你可以改用打字的。"


def unknown_session_message() -> str:
    return "這個語音會話已經結束了。重新整理頁面就會開始新的一個。"


registry = VoiceSessionRegistry()
"""The one every request shares, for the same reason they share a process."""
