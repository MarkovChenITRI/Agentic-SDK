"""The real output transport: streamed speech from a synthesis deployment.

Streaming rather than a whole file because the first piece arrives about a
second in while the full answer takes four, and a person waiting four seconds
for a reply has already decided the agent is slow.

PCM because it is the fastest of the formats to start and needs no decoding
before a browser can play it.
"""

from __future__ import annotations

from typing import Iterator


class AzureSpeechOutput:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        voice: str = "alloy",
        response_format: str = "pcm",
        timeout_sec: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._url = base_url
        self._model = model
        self._voice = voice
        self._response_format = response_format
        self._timeout = timeout_sec

    def speak(self, text: str) -> Iterator[bytes]:
        import httpx

        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice,
            "response_format": self._response_format,
        }
        with httpx.stream(
            "POST",
            self._url,
            headers={"api-key": self._api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=self._timeout,
        ) as response:
            response.raise_for_status()
            # Abandoning this generator closes the connection, which is how an
            # interruption stops synthesis instead of paying for a sentence
            # nobody will hear.
            yield from response.iter_bytes()
