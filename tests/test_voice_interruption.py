from __future__ import annotations

from types import SimpleNamespace

import pytest

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


def test_a_stream_stopped_mid_answer_reports_being_stopped():
    """The generation path itself, not a module's handling of it.

    Every module used to translate this exception for itself, and the one that
    forgot answered the person with an apology for something they did on
    purpose. Now the stream raises what it means, so a module that does
    nothing at all still gets it right — which is only true while this holds.
    """
    from agentic_sdk.core.cancellation import WorkflowInterrupted
    from agentic_sdk.llm.openai_compatible import chat_stream

    heard_enough = []

    with pytest.raises(WorkflowInterrupted) as stopped:
        chat_stream(
            _StreamingClient("保固期是十二個月，延長保固可以再加兩年"),
            model="m",
            user="保固多久？",
            should_stop=lambda: bool(heard_enough) or heard_enough.append(1),
        )

    assert stopped.value.payload["produced_characters"] > 0


class _StreamingClient:
    """A client that hands back one character at a time, like a real stream."""

    def __init__(self, answer: str) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._answer = answer

    def _create(self, **_kwargs):
        return (
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=character, tool_calls=None), finish_reason=None)],
                model="m",
                usage=None,
            )
            for character in self._answer
        )


class _CancelsMidStream:
    """A client that stops being wanted while it is still answering."""

    def __init__(self, answer: str, token) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._answer = answer
        self._token = token

    def _create(self, **_kwargs):
        def chunks():
            for index, character in enumerate(self._answer):
                if index == 3:
                    self._token.cancel("interjection")
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=character, tool_calls=None), finish_reason=None)],
                    model="m",
                    usage=None,
                )
        return chunks()


def test_an_interjection_inside_a_module_is_not_reported_as_a_model_error():
    """Being talked over must not come back as something going wrong.

    The module's broad `except Exception` sits around the generation call, and
    an interruption raised inside it is an Exception like any other — so it was
    caught, written out as an action error, and the person who deliberately
    interrupted was shown '[workflow ended with error] cancelled'.
    """
    from agentic_sdk.modules import GenerativeAction, PassThroughPerceive

    token = CancellationToken()
    action = GenerativeAction(api_key="k", base_url="https://example.test/v1", model="m")
    action._client = _CancelsMidStream("保固期是十二個月，延長保固可以再加兩年", token)
    workflow = Workflow(workflow_name="w", perceive=PassThroughPerceive(), action=action)

    result = workflow.run("保固多久？", cancel=token)

    assert result.interrupted is True
    assert result.aborted is False
    assert "error" not in (result.final_message or "")
    assert [entry for entry in result.entries if entry.content.startswith("error:")] == []


def test_the_trace_says_why_the_turn_was_cut_short():
    """The module and the flag were right; the reason was always blank."""
    audio = FakeAudioInput()
    workflow = voice_workflow(audio, SlowAnswer(audio))
    events = []

    audio.transcribe("保固多久？")
    workflow.run(cancel=CancellationToken(), event_callback=events.append)

    aborts = [event for event in events if event.get("phase") == "abort"]
    assert aborts, "追蹤上沒有中止事件"
    assert aborts[-1]["reason"] == "interjection"
    assert aborts[-1]["interrupted"] is True


def test_what_the_reader_saw_is_what_the_turn_records():
    """No audio anywhere near this: a text answer cut off halfway.

    The person read eight characters and the record held nothing at all, so the
    next turn had no idea the agent had said anything. What reached them is
    what the conversation keeps — the rest happened to nobody.
    """
    from agentic_sdk.modules import GenerativeAction, PassThroughPerceive

    token = CancellationToken()
    action = GenerativeAction(api_key="k", base_url="https://example.test/v1", model="m")
    action._client = _CancelsMidStream("保固期是十二個月，延長保固可以再加兩年", token)
    workflow = Workflow(workflow_name="w", perceive=PassThroughPerceive(), action=action)

    # Someone is watching the answer arrive, which is what makes delivery
    # incremental in the first place.
    stream = workflow.stream("保固多久？", cancel=token)
    seen = "".join(stream)
    result = stream.result

    assert result.interrupted is True
    assert seen != "", "使用者什麼都沒看到，那就不是這個情境"
    assert result.interrupt_payload["delivered"] == seen
    assert [turn.content for turn in workflow.memory.turns if turn.role == "assistant"] == [seen]
