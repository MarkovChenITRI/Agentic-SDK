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


class _Client:
    """Stands in for an OpenAI client, recording what it was asked for."""

    def __init__(self, pieces=(b"one", b"two", b"three")):
        self.asked = None
        self.events = []
        self.audio = SimpleNamespace(
            speech=SimpleNamespace(
                with_streaming_response=SimpleNamespace(create=self._create)
            )
        )
        self._pieces = pieces

    def _create(self, **kwargs):
        self.asked = kwargs
        return _Streamed(self._pieces, self.events)


def test_it_asks_the_endpoint_the_way_the_openai_sdk_does():
    """Not a hand-rolled request: the same client the rest of the SDK uses.

    The previous transport assembled its own URL and its own vendor header,
    which is how one vendor's product details ended up inside a library that
    claims to be vendor-neutral.
    """
    client = _Client()
    voice = SpeechOutput(client=client, model="tts-1", voice="alloy")

    list(voice.speak("保固十二個月"))

    assert client.asked["model"] == "tts-1"
    assert client.asked["voice"] == "alloy"
    assert client.asked["input"] == "保固十二個月"
    assert client.asked["response_format"] == "pcm"


def test_the_audio_arrives_in_pieces():
    client = _Client()

    assert list(SpeechOutput(client=client, model="m").speak("嗨")) == [b"one", b"two", b"three"]


def test_abandoning_it_closes_the_response():
    """An interjection stops the synthesis, not just the listening to it."""
    client = _Client()
    stream = SpeechOutput(client=client, model="m").speak("嗨")
    next(stream)
    stream.close()

    assert client.events == ["closed"]


def test_a_vendor_that_needs_more_than_three_settings_can_have_it():
    """Vendor differences travel as parameters, not as branches in the module."""
    client = _Client()
    voice = SpeechOutput(client=client, model="m", extra_query={"api-version": "2025-03-01-preview"})

    list(voice.speak("嗨"))

    assert client.asked["extra_query"] == {"api-version": "2025-03-01-preview"}
