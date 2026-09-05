from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "playground"))

from playground.services import model_endpoints
from playground.services.workflow_spec import apply_builder_step, default_spec, spec_to_form_state
from support import build_spec


def bindings(spec) -> list[str]:
    return [requirement["role"] for requirement in model_endpoints.endpoint_state(spec, {})["requirements"]]


def test_choosing_voice_input_asks_only_for_transcription():
    """Using your voice instead of typing needs one service, not two."""
    spec = build_spec(("input_type", "voice"), ("output_format", "direct"))

    assert spec["perceive"]["module"] == "VoiceTextPerceive"
    assert bindings(spec) == ["transcribe"]


def test_choosing_voice_output_asks_only_for_speech():
    """Wanting to listen does not mean wanting to talk."""
    spec = build_spec(("output_format", "voice"))

    assert spec["action"]["module"] == "VoiceAnswerAction"
    assert "tts" in bindings(spec)
    assert "transcribe" not in bindings(spec)


def test_a_full_voice_conversation_asks_for_both():
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))

    assert set(bindings(spec)) >= {"transcribe", "tts"}


def test_neither_half_implies_the_other():
    """Both one-sided combinations are real agents, not misconfigurations."""
    listening_only = build_spec(("input_type", "voice"), ("output_format", "free_text"))
    speaking_only = build_spec(("input_type", "text"), ("output_format", "voice"))

    assert listening_only["action"]["module"] == "GenerativeAction"
    assert speaking_only["perceive"]["module"] == "TextPerceive"


def test_the_builder_reports_the_voice_answers_it_was_given():
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))
    choices = spec_to_form_state(spec)["choices"]

    assert choices["input_type"] == "voice"
    assert choices["output_format"] == "voice"


def test_an_agent_can_be_taken_back_off_voice():
    """Changing your mind must not mean rebuilding the agent."""
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))

    spec = apply_builder_step(spec, "input_type", "text")
    spec = apply_builder_step(spec, "output_format", "free_text")

    assert spec["perceive"]["module"] == "TextPerceive"
    assert spec["action"]["module"] == "GenerativeAction"
    assert "transcribe" not in bindings(spec)
    assert "tts" not in bindings(spec)


def test_listening_and_speaking_are_not_interchangeable():
    """Binding synthesis to the listening step would fail at the first word."""
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))
    options = {
        requirement["role"]: [option["id"] for option in requirement["options"]]
        for requirement in model_endpoints.endpoint_state(spec, {})["requirements"]
    }

    assert options["transcribe"] == ["transcribe"]
    assert options["tts"] == ["tts"]
