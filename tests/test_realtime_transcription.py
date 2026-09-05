"""The listening transport, on the SDK's realtime client rather than a hand-rolled one."""

from __future__ import annotations

import base64
import queue
import time
from types import SimpleNamespace

from agentic_sdk.audio.realtime import RealtimeTranscription


class _Connection:
    def __init__(self, incoming):
        self.sent = []
        self.closed = False
        self._incoming = incoming

    def send(self, event):
        self.sent.append(event)

    def recv(self):
        item = self._incoming.get()
        if item is None:
            raise StopIteration
        return item

    def close(self):
        self.closed = True


class _Manager:
    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        return self._connection

    def __exit__(self, *_exc):
        return False


class _Client:
    """Stands in for an OpenAI client holding a realtime connection."""

    def __init__(self):
        self.incoming = queue.Queue()
        self.connection = _Connection(self.incoming)
        self.asked = None
        self.beta = SimpleNamespace(realtime=SimpleNamespace(connect=self._connect))

    def _connect(self, **kwargs):
        self.asked = kwargs
        return _Manager(self.connection)


def open_session(**kwargs):
    client = _Client()
    return client, RealtimeTranscription(client=client, model="transcribe-1", **kwargs)


def settle():
    time.sleep(0.05)


def test_it_connects_the_way_the_openai_sdk_does():
    client, session = open_session()

    assert client.asked["model"] == "transcribe-1"
    session.close()


def test_a_vendor_that_needs_extra_parameters_can_have_them():
    """Vendor differences are parameters, not branches inside the transport."""
    client, session = open_session(
        extra_query={"intent": "transcription", "api-version": "2025-04-01-preview"},
        extra_headers={"api-key": "k"},
    )

    assert client.asked["extra_query"]["intent"] == "transcription"
    assert client.asked["extra_headers"] == {"api-key": "k"}
    session.close()


def test_it_asks_the_service_to_decide_where_an_utterance_ends():
    """Server-side voice activity is what makes an interruption possible at all."""
    client, session = open_session()

    opening = client.connection.sent[0]
    assert opening["type"] == "transcription_session.update"
    assert opening["session"]["input_audio_format"] == "pcm16"
    assert opening["session"]["turn_detection"]["type"] == "server_vad"
    session.close()


def test_audio_goes_out_as_the_protocol_wants_it():
    client, session = open_session()

    session.send(b"\x01\x02\x03\x04")
    settle()

    appended = [event for event in client.connection.sent if event["type"] == "input_audio_buffer.append"]
    assert base64.b64decode(appended[-1]["audio"]) == b"\x01\x02\x03\x04"
    session.close()


def test_someone_starting_to_speak_is_reported_before_any_words():
    client, session = open_session()
    began = []
    session.on_speech_started(lambda: began.append(True))

    client.incoming.put({"type": "input_audio_buffer.speech_started"})
    settle()

    assert began == [True]
    session.close()


def test_a_finished_utterance_is_reported():
    client, session = open_session()
    heard = []
    session.on_transcript(heard.append)

    client.incoming.put(
        {"type": "conversation.item.input_audio_transcription.completed", "transcript": "保固多久？"}
    )
    settle()

    assert heard == ["保固多久？"]
    session.close()
