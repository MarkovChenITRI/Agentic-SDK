"""Choosing voice in the Builder has to produce an agent that actually speaks.

The Builder writes the choice into the spec and the readiness check accepts it;
whether the runtime honours it is a separate question, and the answer used to
be no. This is the seam where the two meet.
"""

from __future__ import annotations

from agentic_sdk.config.workflow_config import ModuleSpec, build_module
from agentic_sdk.modules.action.voice_answer import VoiceAnswerAction
from agentic_sdk.modules.perceive.voice_text import VoiceTextPerceive
from playground.services.runner_service import _action_from_config, _perceive_from_config
from playground.services.source_builder import BuilderSourceConfig


def voice_config(**overrides) -> BuilderSourceConfig:
    return BuilderSourceConfig(
        workflow_name="voice",
        perceive_module="VoiceTextPerceive",
        action_module="VoiceAnswerAction",
        **overrides,
    )


def test_the_spec_can_name_the_speaking_action():
    """Half a registration is what ticket 01 exists to catch."""
    module = build_module(
        ModuleSpec(
            kind="voice_answer",
            params={
                "api_key": "k",
                "base_url": "https://models.test/openai/v1",
                "model": "gpt-5.4",
                "speech_api_key": "k",
                "speech_base_url": "https://speech.test",
                "speech_model": "tts",
            },
        )
    )

    assert isinstance(module, VoiceAnswerAction)


def test_a_voice_agent_answers_on_two_channels():
    action = _action_from_config(voice_config(), {"action": "gpt-54"}, {"action"})

    assert isinstance(action, VoiceAnswerAction)


def test_a_voice_agent_listens_on_the_session_that_is_listening():
    """The audio is already arriving somewhere. The workflow uses that one."""
    from agentic_sdk.audio import FakeAudioInput
    from playground.services.voice_session import registry

    listening = registry.listen("wired-session", FakeAudioInput())

    perceive = _perceive_from_config(voice_config(), {}, {"perceive"}, voice_session_id="wired-session")

    assert perceive is listening


def test_a_voice_agent_still_works_for_someone_typing():
    """No microphone open is not a broken agent — it is someone using the keyboard."""
    perceive = _perceive_from_config(voice_config(), {}, {"perceive"}, voice_session_id="")

    assert not isinstance(perceive, VoiceTextPerceive)
    assert perceive is not None
