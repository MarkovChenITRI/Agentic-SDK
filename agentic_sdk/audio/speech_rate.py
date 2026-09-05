"""Turning a playback duration back into a position in the text.

Whatever played the audio reports one number: how many seconds of it were
heard. What the conversation record needs is the words. Nothing but the rate
of speech connects the two, so the conversion lives here — beside the rest of
the audio code, and out of the workflow engine, which under ADR-0001 is not
supposed to know a speaker exists.
"""

from __future__ import annotations


SPEAKING_CHARACTERS_PER_SECOND = 4.5
"""How much text a synthesised voice gets through in a second.

A measured average rather than a property of any one sentence, which is why
the result is trimmed back to a punctuation mark: being a few characters out
either way should not leave half a word in the transcript.
"""


def heard_portion(spoken: str, heard_seconds: float | None) -> str:
    """The part of an answer that was played before it was cut off.

    Without a reported duration the whole thing stands. Unknown is not nought:
    something that noticed the interruption without playing the audio — the
    transcription service hearing someone begin — has nothing to report, and
    treating that as nothing-was-heard would delete an answer the person did
    hear.
    """
    if heard_seconds is None or not spoken:
        return spoken
    played = int(float(heard_seconds) * SPEAKING_CHARACTERS_PER_SECOND)
    if played >= len(spoken):
        return spoken
    cut = max((spoken.rfind(mark, 0, played + 1) for mark in "，。！？；、,.!?;"), default=-1)
    return spoken[: cut if cut > 0 else played].strip()
