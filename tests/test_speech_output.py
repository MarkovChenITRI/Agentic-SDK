"""The speaking transport, built on the same client every other module uses."""

from __future__ import annotations

from types import SimpleNamespace

from agentic_sdk.audio.speech import SpeechOutput


class _Streamed:
    def __init__(self, pieces, record):
        self._pieces = pieces
        self._record = record

    def __enter__(self):
        return SimpleNamespace(iter_bytes=lambda: iter(self._pieces))

    def __exit__(self, *_exc):
        self._record.append("closed")
        return False


class _Elsewhere(SpeechOutput):
    """Audio fetched some other way — the one method a subclass replaces."""

    def __init__(self, pieces=(b"one", b"two", b"three"), **kwargs):
        self.asked = None
        self.events = []
        self._pieces = pieces
        super().__init__(**kwargs)

    def _open_stream(self, text):
        self.asked = {"input": text, "model": self._model, "voice": self._voice,
                      "response_format": self._response_format}
        return _Streamed(self._pieces, self.events)


def test_it_asks_for_what_the_answer_needs():
    voice = _Elsewhere(model="tts-1", voice="alloy")

    list(voice.speak("保固十二個月"))

    assert voice.asked == {"input": "保固十二個月", "model": "tts-1",
                           "voice": "alloy", "response_format": "pcm"}


def test_the_audio_arrives_in_pieces():
    assert list(_Elsewhere(model="m").speak("嗨")) == [b"one", b"two", b"three"]


def test_abandoning_it_closes_the_response():
    """An interjection stops the synthesis, not just the listening to it."""
    voice = _Elsewhere(model="m")
    stream = voice.speak("嗨")
    next(stream)
    stream.close()

    assert voice.events == ["closed"]


def test_the_shipped_transport_talks_to_openai_and_says_so():
    import inspect

    accepted = set(inspect.signature(SpeechOutput.__init__).parameters)

    assert "client" not in accepted
    assert "extra_query" not in accepted
