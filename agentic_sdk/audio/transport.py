"""The boundary between a voice module and whatever carries the audio.

Both directions are named here, though only the input side has a user yet. They
belong together: a caller configuring speech configures both, and defining the
second one later would mean discovering the shape twice.

The point of the boundary is that a test can drive a whole conversation —
someone starts speaking, says this, stops — without a network or a credential.
Every module that touches audio takes one of these; the real implementations
are one kind, and the fakes below are another.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, Protocol


class AudioInputTransport(Protocol):
    """Carries microphone audio out and speech events back.

    Two events matter and they arrive at different times. Speech *starting* is
    the interruption signal — measured at about 600ms, while a transcript takes
    nearly four seconds — so a caller that waits for words has already missed
    its chance to stop talking over someone.
    """

    def send(self, pcm16: bytes) -> None:
        """Hand over a chunk of 16-bit mono audio at the service's rate."""

    def on_speech_started(self, callback: Callable[[], None]) -> None:
        """Called the moment the service hears someone begin, before any words."""

    def on_transcript(self, callback: Callable[[str], None]) -> None:
        """Called with a finished utterance."""

    def close(self) -> None: ...


class AudioOutputTransport(Protocol):
    """Turns text into audio, in pieces, and can be told to stop mid-sentence."""

    def speak(self, text: str) -> Iterator[bytes]:
        """Yield audio for the text, first piece as early as the service allows.

        Abandoning the iterator stops the synthesis: a person who interrupts is
        not waiting for the rest of a sentence nobody will hear.
        """


class FakeAudioInput:
    """An input transport a test drives by hand.

    Nothing is timed and nothing is decoded — the test says when someone starts
    speaking and what they said, which is the only part a module's behaviour
    depends on.
    """

    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.closed = False
        self._speech_started: list[Callable[[], None]] = []
        self._transcript: list[Callable[[str], None]] = []

    # ── the transport side ──────────────────────────────────────────────

    def send(self, pcm16: bytes) -> None:
        self.sent.append(pcm16)

    def on_speech_started(self, callback: Callable[[], None]) -> None:
        self._speech_started.append(callback)

    def on_transcript(self, callback: Callable[[str], None]) -> None:
        self._transcript.append(callback)

    def close(self) -> None:
        self.closed = True

    # ── what a test drives ──────────────────────────────────────────────

    def start_speaking(self) -> None:
        for callback in list(self._speech_started):
            callback()

    def transcribe(self, text: str) -> None:
        for callback in list(self._transcript):
            callback(text)


def require_speech_endpoint(**settings: Any) -> None:
    """Refuse a module that has neither a transport nor an endpoint to build one.

    Without this the module would be constructed happily and then hear nothing,
    which is the failure this project keeps finding: something that looks
    configured and quietly does not work.
    """
    missing = [name for name, value in settings.items() if not str(value or "").strip()]
    if missing:
        raise ValueError(
            f"{', '.join(missing)} required when no transport is given. Pass the "
            f"speech endpoint's settings, or pass a transport of your own."
        )
