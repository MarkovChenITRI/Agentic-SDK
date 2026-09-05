from __future__ import annotations

import json
from unittest.mock import patch

from agentic_sdk import Workflow
from agentic_sdk.audio import FakeAudioOutput
from agentic_sdk.modules import PassThroughPerceive, PassThroughRetrieve, VoiceAnswerAction

from support import FoundryOpenAILikeClient


SPOKEN = "這款比較適合久站，兩千三百八，門市有現貨。"
DISPLAYED = "科技鞋墊 多功能型 / SKU 7037730 / NT$2,380 / 現貨 4 雙"


def voice_action(speech: FakeAudioOutput, action_text: str) -> VoiceAnswerAction:
    action = VoiceAnswerAction(
        api_key="k", base_url="https://example.test/v1", model="m", speech=speech
    )
    action._client = FoundryOpenAILikeClient(action_text=action_text)
    return action


def two_channel_reply() -> str:
    return json.dumps({"spoken": SPOKEN, "displayed": DISPLAYED}, ensure_ascii=False)


def _state_with_cancel(token):
    """A state the way the workflow hands one to a module mid-run."""
    from agentic_sdk.core import WorkflowState

    state = WorkflowState(workflow_name="voice", user_message="保固多久？")
    state.cancel = token
    return state


def run_with(action) -> object:
    workflow = Workflow(
        workflow_name="voice",
        perceive=PassThroughPerceive(),
        retrieve=PassThroughRetrieve(),
        action=action,
    )
    return workflow.run("有什麼鞋墊？")


def test_the_screen_and_the_voice_carry_different_things():
    """Reading the displayed content aloud is the failure this exists to avoid."""
    speech = FakeAudioOutput()

    result = run_with(voice_action(speech, two_channel_reply()))

    assert result.final_message == DISPLAYED
    assert speech.spoken == [SPOKEN]


def test_an_answer_with_nothing_particular_to_say_is_read_out():
    """No spoken channel is a plain answer, not a broken one."""
    speech = FakeAudioOutput()

    result = run_with(voice_action(speech, "保固十二個月。"))

    assert result.final_message == "保固十二個月。"
    assert speech.spoken == ["保固十二個月。"]


def test_speaking_starts_before_the_whole_answer_is_written():
    """Waiting for the displayed half would put a pause in front of every reply.

    Driven from the reply cut off part way through: the spoken field is
    complete, the JSON around it is not. Anything that waited for the whole
    answer to parse would say nothing at all here.
    """
    speech = FakeAudioOutput()
    truncated = '{"spoken": "' + SPOKEN + '", "displayed": "科技鞋墊'

    run_with(voice_action(speech, truncated))

    assert speech.spoken == [SPOKEN]


def test_interrupting_stops_the_synthesis_too():
    """Finishing a sentence nobody will hear costs money and says nothing."""
    from agentic_sdk.core.cancellation import CancellationToken

    speech = FakeAudioOutput()
    action = voice_action(speech, two_channel_reply())
    token = CancellationToken()

    class InterruptDuringPlayback:
        """Stands in for a person talking over the first moment of the reply."""

        def speak(self, text):
            speech.spoken.append(text)
            token.cancel("interjection")
            yield b"first"
            speech.abandoned.append(text)

    action._speech = InterruptDuringPlayback()
    workflow = Workflow(
        workflow_name="voice",
        perceive=PassThroughPerceive(),
        retrieve=PassThroughRetrieve(),
        action=action,
    )

    workflow.run("有什麼鞋墊？", cancel=token)

    assert speech.spoken == [SPOKEN]
    assert speech.abandoned == [], "synthesis kept going after the interruption"


def test_nothing_heard_is_reported_when_playback_never_started():
    """Interrupted before a sound came out: there is nothing to carry forward."""
    from agentic_sdk.core.cancellation import CancellationToken

    speech = FakeAudioOutput()
    action = voice_action(speech, two_channel_reply())
    token = CancellationToken()
    token.cancel("interjection")

    workflow = Workflow(
        workflow_name="voice",
        perceive=PassThroughPerceive(),
        retrieve=PassThroughRetrieve(),
        action=action,
    )
    result = workflow.run("有什麼鞋墊？", cancel=token)

    assert result.interrupt_payload.get("heard", "") == ""


def test_only_what_was_played_is_reported_as_heard():
    """The producer of the heard text, not a hand-fed value.

    Speech lags generation, so an answer cut off mid-playback has a tail that
    was written and never spoken. Reporting the whole thing would let the next
    turn refer back to a sentence nobody heard.
    """
    from agentic_sdk.core.cancellation import CancellationToken

    token = CancellationToken()
    action = voice_action(FakeAudioOutput(), "")
    state = _state_with_cancel(token)

    token.cancel("interjection", heard_seconds=2.0)
    action._speak("保固期是十二個月，延長保固可以再加兩年，另外配件另計", state)

    assert state.spoken_so_far == "保固期是十二個月"


def test_an_answer_nobody_interrupted_is_reported_whole():
    from agentic_sdk.core.cancellation import CancellationToken

    token = CancellationToken()
    action = voice_action(FakeAudioOutput(), "")
    state = _state_with_cancel(token)

    action._speak("保固十二個月", state)

    assert state.spoken_so_far == "保固十二個月"
