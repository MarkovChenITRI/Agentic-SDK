from __future__ import annotations

import struct

import pytest

from agentic_sdk import Workflow
from agentic_sdk.audio import FakeAudioInput
from agentic_sdk.modules import DirectAnswerAction, PassThroughRetrieve, VoiceTextPerceive


def pcm(*samples: int) -> bytes:
    """One channel of 16-bit audio, the format the transcription service takes."""
    return struct.pack(f"<{len(samples)}h", *samples)


def silence(frames: int = 1600) -> bytes:
    return pcm(*([0] * frames))


def speech(frames: int = 1600, level: int = 8000) -> bytes:
    # Alternating so the frames have energy rather than a constant offset.
    return pcm(*([level, -level] * (frames // 2)))


def test_a_spoken_question_reaches_the_workflow():
    """The point of the module: talk, and the agent answers what you said."""
    audio = FakeAudioInput()
    workflow = Workflow(
        workflow_name="voice",
        perceive=VoiceTextPerceive(transport=audio),
        retrieve=PassThroughRetrieve(),
        action=DirectAnswerAction(),
    )

    audio.transcribe("保固多久？")
    result = workflow.run()

    perceived = next(entry for entry in result.entries if entry.type.value == "perceived")
    assert perceived.content == "保固多久？"
    assert perceived.metadata["spoken"] is True


def test_silence_is_never_sent_to_the_service():
    """Silence bills like speech and comes back transcribed as words nobody said.

    Three seconds of pure silence was billed 30 audio tokens — the same as three
    seconds of talking — and transcribed as 「这里」. An unfiltered microphone in
    a quiet room would keep inventing input.
    """
    audio = FakeAudioInput()
    perceive = VoiceTextPerceive(transport=audio)

    perceive.hear(silence())
    perceive.hear(silence())

    assert audio.sent == []


def test_speech_is_sent_and_the_tail_of_it_survives():
    """Cutting at the moment energy drops clips the end of the last word."""
    audio = FakeAudioInput()
    perceive = VoiceTextPerceive(transport=audio, hangover_chunks=2)

    perceive.hear(silence())
    perceive.hear(speech())
    perceive.hear(silence())
    perceive.hear(silence())
    perceive.hear(silence())

    # The speech itself, then exactly the two quiet chunks that follow it —
    # and nothing from before it. Counting alone would pass a gate that sent
    # the leading silence and dropped one of the trailing chunks.
    assert audio.sent == [speech(), silence(), silence()]


def test_the_threshold_can_be_moved_for_a_noisy_room():
    quiet_room = VoiceTextPerceive(transport=FakeAudioInput(), speech_threshold=1000)
    noisy_room = VoiceTextPerceive(transport=FakeAudioInput(), speech_threshold=9000)

    quiet_room.hear(speech(level=5000))
    noisy_room.hear(speech(level=5000))

    assert quiet_room.transport.sent != []
    assert noisy_room.transport.sent == []


def test_a_module_built_without_a_transport_needs_its_endpoint():
    """The transport is the test seam, not something a caller has to assemble.

    Omitting it is the normal way to use the module, so omitting the endpoint
    too has to fail loudly rather than produce a module that silently hears
    nothing.
    """
    with pytest.raises(ValueError):
        VoiceTextPerceive()


def test_a_voice_agent_starts_without_being_told_what_was_said():
    """Speech arrives when the person talks, not when run() is called.

    Workflow.run demanded the words up front, so starting a voice agent would
    have meant typing what had just been spoken — which is the thing voice
    exists to avoid.
    """
    audio = FakeAudioInput()
    perceive = VoiceTextPerceive(transport=audio)
    workflow = Workflow(
        workflow_name="voice",
        perceive=perceive,
        retrieve=PassThroughRetrieve(),
        action=DirectAnswerAction(),
    )

    audio.transcribe("退貨要幾天？")
    result = workflow.run()

    assert result.entries[0].content == "退貨要幾天？"
    assert perceive.pending_input() == ""


def test_a_workflow_with_nothing_to_go_on_still_refuses():
    """The relaxation is for a module that has input, not for no input at all."""
    workflow = Workflow(
        workflow_name="voice",
        perceive=VoiceTextPerceive(transport=FakeAudioInput()),
        retrieve=PassThroughRetrieve(),
        action=DirectAnswerAction(),
    )

    with pytest.raises(ValueError):
        workflow.run()


def test_audio_goes_in_one_end_and_an_answer_comes_out_the_other():
    """The halves are tested apart; this is the whole path in one go."""
    audio = FakeAudioInput()
    perceive = VoiceTextPerceive(transport=audio)
    workflow = Workflow(
        workflow_name="voice",
        perceive=perceive,
        retrieve=PassThroughRetrieve(),
        action=DirectAnswerAction(),
    )

    perceive.hear(silence())
    perceive.hear(speech())
    audio.transcribe("保固多久？")
    result = workflow.run()

    assert audio.sent != [], "the speech never reached the service"
    assert result.final_message == "保固多久？"


def test_a_typed_message_is_not_overruled_by_something_overheard():
    """The conversation record and the perceived input must agree.

    Preferring what was heard would leave memory saying one thing and the
    perceived entry another, about the same turn.
    """
    audio = FakeAudioInput()
    perceive = VoiceTextPerceive(transport=audio)
    workflow = Workflow(
        workflow_name="voice",
        perceive=perceive,
        retrieve=PassThroughRetrieve(),
        action=DirectAnswerAction(),
    )

    audio.transcribe("背景有人在講話")
    result = workflow.run("我用打的問保固")

    perceived = next(entry for entry in result.entries if entry.type.value == "perceived")
    assert perceived.content == "我用打的問保固"
    assert perceived.metadata["spoken"] is False
