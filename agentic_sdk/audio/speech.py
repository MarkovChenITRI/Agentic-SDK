"""Speech synthesis, through the same client every other module talks to.

Streaming rather than a whole file because the first piece arrives about a
second in while a full answer takes four, and a person waiting four seconds for
a reply has already decided the agent is slow.

PCM because it is the fastest of the formats to start and needs no decoding
before a browser can play it.

Nothing here names a vendor. What one endpoint needs and another does not
travels as ``extra_query`` and ``extra_headers``, which is how the OpenAI SDK
carries the same difference — see ADR-0003.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping


class SpeechOutput:
    """Turns text into audio on an OpenAI-compatible speech endpoint."""

    def __init__(
        self,
        *,
        model: str,
        client: Any = None,
        api_key: str | None = None,
        base_url: str | None = None,
        voice: str = "alloy",
        response_format: str = "pcm",
        extra_query: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        """Speak on the given client, or on one built from the usual two settings.

        ``client`` is here so a test — or a caller who already holds one — can
        hand over the client rather than the credentials to build it.
        """
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)
        self._client = client
        self._model = model
        self._voice = voice
        self._response_format = response_format
        self._extra_query = dict(extra_query or {})
        self._extra_headers = dict(extra_headers or {})

    def speak(self, text: str) -> Iterator[bytes]:
        request: dict[str, Any] = {
            "model": self._model,
            "voice": self._voice,
            "input": text,
            "response_format": self._response_format,
        }
        if self._extra_query:
            request["extra_query"] = self._extra_query
        if self._extra_headers:
            request["extra_headers"] = self._extra_headers
        # The context manager is what makes an interjection stop the synthesis:
        # abandoning this generator closes the response, and the endpoint stops
        # producing a sentence nobody will hear.
        with self._client.audio.speech.with_streaming_response.create(**request) as response:
            yield from response.iter_bytes()
