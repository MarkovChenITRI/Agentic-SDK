from __future__ import annotations

from agentic_sdk import Workflow
from agentic_sdk.audio import FakeAudioInput
from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput
from agentic_sdk.core.cancellation import CancellationToken
from agentic_sdk.modules import PassThroughRetrieve, VoiceTextPerceive


HEARD = "保固期限是十二個月"
UNHEARD = "，另外還有延長保固方案可以加購。"


class AnswerCutOffPartWayThrough:
    """Produces a whole answer, of which only the beginning was spoken aloud."""

    name = "action"

    def __init__(self, audio: FakeAudioInput) -> None:
        self._audio = audio

    def __call__(self, state):
        state.report_spoken_progress(HEARD)
        self._audio.start_speaking()
        state.cancel.raise_if_cancelled()
        raise AssertionError("should have been interrupted")


def voice_workflow(audio: FakeAudioInput) -> Workflow:
    return Workflow(
        workflow_name="voice",
        perceive=VoiceTextPerceive(transport=audio),
        retrieve=PassThroughRetrieve(),
        action=AnswerCutOffPartWayThrough(audio),
    )


def test_the_interruption_reports_what_was_heard_not_what_was_written():
    """Speech lags generation, so the tail was written and never spoken.

    Keeping it would let the next turn refer back to a sentence nobody heard.
    """
    audio = FakeAudioInput()
    workflow = voice_workflow(audio)

    audio.transcribe("保固多久？")
    result = workflow.run(cancel=CancellationToken())

    assert result.interrupt_payload["heard"] == HEARD
    assert UNHEARD not in str(result.interrupt_payload)


def test_only_what_was_heard_survives_in_the_conversation():
    audio = FakeAudioInput()
    workflow = voice_workflow(audio)

    audio.transcribe("保固多久？")
    workflow.run(cancel=CancellationToken())

    assistant_turns = [turn.content for turn in workflow.memory.turns if turn.role == "assistant"]
    assert assistant_turns == [HEARD]
    assert all(UNHEARD not in turn for turn in assistant_turns)


def test_the_next_turn_is_told_it_was_cut_off():
    """Without being told, the agent answered 「沒有足夠資料指出前一段停在哪」."""
    audio = FakeAudioInput()
    workflow = voice_workflow(audio)

    audio.transcribe("保固多久？")
    workflow.run(cancel=CancellationToken())

    interrupted_turn = [turn for turn in workflow.memory.turns if turn.metadata.get("interrupted")]
    assert interrupted_turn, "nothing in the conversation says the turn was cut off"
    assert interrupted_turn[-1].content == HEARD


def test_an_answer_nobody_heard_leaves_nothing_behind():
    """Interrupted before a word was spoken: there is nothing to carry on from."""
    audio = FakeAudioInput()

    class SilentAction:
        name = "action"

        def __call__(self, state):
            audio.start_speaking()
            state.cancel.raise_if_cancelled()
            raise AssertionError("should have been interrupted")

    workflow = Workflow(
        workflow_name="voice",
        perceive=VoiceTextPerceive(transport=audio),
        retrieve=PassThroughRetrieve(),
        action=SilentAction(),
    )

    audio.transcribe("保固多久？")
    result = workflow.run(cancel=CancellationToken())

    assert result.interrupt_payload.get("heard", "") == ""
    assert [turn.content for turn in workflow.memory.turns if turn.role == "assistant"] == []


def test_the_model_is_told_it_was_cut_off_and_what_was_heard():
    """Being told is the difference between carrying on and starting again."""
    from agentic_sdk.memory import InContextMemory
    from agentic_sdk.modules.action.generative import _build_messages
    from agentic_sdk.core import WorkflowState

    memory = InContextMemory(workflow_name="w")
    memory.append_message("user", "保固多久？")
    memory.append_message("assistant", HEARD, metadata={"source": "workflow.run", "interrupted": True})
    memory.append_message("user", "那延長保固呢？")
    state = WorkflowState(workflow_name="w", user_message="那延長保固呢？", memory=memory)

    prompt = " ".join(str(message.get("content", "")) for message in _build_messages(state, None))

    assert HEARD in prompt
    assert "打斷" in prompt
    assert "不要從頭重述" in prompt
