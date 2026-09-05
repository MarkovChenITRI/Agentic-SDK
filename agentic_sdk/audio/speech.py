"""Speech synthesis, through the same client every other module talks to.

Streaming rather than a whole file because the first piece arrives about a
second in while a full answer takes four, and a person waiting four seconds for
a reply has already decided the agent is slow.

PCM because it is the fastest of the formats to start and needs no decoding
before a browser can play it.

This talks to OpenAI and to nothing else. An endpoint that is reached
differently is handled by subclassing and overriding ``_open_stream`` —
everything else, including stopping mid-sentence when someone interrupts, is
inherited. See ADR-0003.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping


class SpeechOutput:
    """Turns text into audio on an OpenAI-compatible speech endpoint."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        voice: str = "alloy",
        response_format: str = "pcm",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._voice = voice
        self._response_format = response_format

    def _open_stream(self, text: str) -> Any:
        """Ask for the audio, and nothing else.

        The one method a different endpoint has to replace. What comes back
        must be a context manager whose ``iter_bytes()`` yields audio:

            class MySpeech(SpeechOutput):
                def _open_stream(self, text):
                    return SomeClient(...).audio.speech.with_streaming_response.create(...)
        """
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return client.audio.speech.with_streaming_response.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format=self._response_format,
        )

    def speak(self, text: str) -> Iterator[bytes]:
        # The context manager is what makes an interjection stop the synthesis:
        # abandoning this generator closes the response, and the endpoint stops
        # producing a sentence nobody will hear.
        with self._open_stream(text) as response:
            yield from response.iter_bytes()
