"""Decides which audio is worth sending.

A microphone in a quiet room still produces bytes, and sending them is not
free in either sense: three seconds of pure silence bills the same as three
seconds of talking, and the service transcribed it as 「这里」 — a word nobody
said. An agent listening to an empty room would keep inventing input for
itself and interrupting its own answers with it.

So the gate is about behaving correctly, not about saving money, which is why
it sits in front of every send rather than behind a flag.
"""

from __future__ import annotations

import array
import math


DEFAULT_SPEECH_THRESHOLD = 500
"""Loudness a chunk must reach to count as someone talking.

Measured as RMS over 16-bit samples, so it is a fraction of 32768. The default
is deliberately low: letting a little room noise through costs a few tokens,
while setting it too high clips the beginning of quiet speech, and a sentence
missing its first word is worse than a sentence with a rustle in front of it.
"""

DEFAULT_HANGOVER_CHUNKS = 3
"""How many quiet chunks to keep sending after the talking stops.

Speech ends softly. Cutting at the moment loudness drops takes the tail off the
last word, and the service — which decides an utterance is over by hearing
silence — never gets the silence it is waiting for.
"""


class SpeechGate:
    """Opens on speech, closes a moment after it stops."""

    def __init__(
        self,
        *,
        threshold: int = DEFAULT_SPEECH_THRESHOLD,
        hangover_chunks: int = DEFAULT_HANGOVER_CHUNKS,
    ) -> None:
        self._threshold = max(0, int(threshold))
        self._hangover_chunks = max(0, int(hangover_chunks))
        self._remaining = 0

    def should_send(self, pcm16: bytes) -> bool:
        if loudness(pcm16) >= self._threshold:
            self._remaining = self._hangover_chunks
            return True
        if self._remaining > 0:
            self._remaining -= 1
            return True
        return False


def loudness(pcm16: bytes) -> float:
    """Root mean square of a chunk of 16-bit mono audio.

    Averaging the squares rather than the values themselves is what makes this
    a measure of energy: audio swings either side of zero, so the plain average
    of a loud chunk is about the same as the plain average of silence.
    """
    if len(pcm16) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(pcm16[: len(pcm16) - (len(pcm16) % 2)])
    if not samples:
        return 0.0
    total = 0
    for sample in samples:
        total += sample * sample
    return math.sqrt(total / len(samples))
