from __future__ import annotations

import struct

from agentic_sdk import Workflow
from agentic_sdk.audio import FakeAudioInput
from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput
from agentic_sdk.core.cancellation import CancellationToken
from agentic_sdk.modules import PassThroughRetrieve, VoiceTextPerceive


class SlowAnswer:
    """An action that is still talking when someone speaks over it."""

    name = "action"

    def __init__(self, audio: FakeAudioInput, *, speak_over_it: bool = True) -> None:
        self._audio = audio
        self._speak_over_it = speak_over_it
        self.finished = False

    def __call__(self, state):
        if self._speak_over_it:
            self._audio.start_speaking()
        state.cancel and state.cancel.raise_if_cancelled()
        self.finished = True
        return ModuleOutput(
            next_module=None,
            payload={"action_result": {"final_message": "講完了"}},
            context_updates=[ContextEntry(type=ContextEntryType.ACTION_RESULT, content="講完了")],
        )


def voice_workflow(audio: FakeAudioInput, action) -> Workflow:
    return Workflow(
        workflow_name="voice",
        perceive=VoiceTextPerceive(transport=audio),
        retrieve=PassThroughRetrieve(),
        action=action,
    )


def test_speaking_over_the_answer_stops_it():
    """The whole point: open your mouth and the agent stops talking."""
    audio = FakeAudioInput()
    action = SlowAnswer(audio)
    workflow = voice_workflow(audio, action)

    audio.transcribe("保固多久？")
    result = workflow.run(cancel=CancellationToken())

    assert result.interrupted is True
    assert action.finished is False


def test_being_interrupted_is_not_an_error():
    """A hop limit is the workflow protecting itself; this is the person steering.

    The two look identical from inside the run and must never look identical
    to the person, so the result does not carry an abort at all — everything
    downstream reads that flag to decide whether to show an error.
    """
    audio = FakeAudioInput()
    workflow = voice_workflow(audio, SlowAnswer(audio))

    audio.transcribe("保固多久？")
    result = workflow.run(cancel=CancellationToken())

    assert result.interrupted is True
    assert result.aborted is False
    assert result.abort_reason is None


def test_the_trace_says_which_module_was_interrupted():
    audio = FakeAudioInput()
    workflow = voice_workflow(audio, SlowAnswer(audio))
    events: list[dict] = []

    audio.transcribe("保固多久？")
    workflow.run(cancel=CancellationToken(), event_callback=events.append)

    aborted = [event for event in events if event.get("phase") == "abort"]
    assert aborted, "no abort event was emitted"
    assert aborted[-1]["module"] == "action"


def test_nobody_speaking_lets_the_answer_finish():
    """The interruption has to come from a person, not from the plumbing."""
    audio = FakeAudioInput()
    action = SlowAnswer(audio, speak_over_it=False)
    workflow = voice_workflow(audio, action)

    audio.transcribe("保固多久？")
    result = workflow.run(cancel=CancellationToken())

    assert result.interrupted is False
    assert action.finished is True


def test_interrupting_turn_after_turn_does_not_wear_the_workflow_down():
    audio = FakeAudioInput()
    workflow = voice_workflow(audio, SlowAnswer(audio))

    for _ in range(3):
        audio.transcribe("保固多久？")
        result = workflow.run(cancel=CancellationToken())
        assert result.interrupted is True
    assert result.visit_counts.get("action", 0) == 1
