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


def test_a_voice_agent_can_actually_be_finished():
    """Every voice agent was stuck: bound correctly, still reported unconfigured.

    The API key lookup searched the chat and embedding endpoints only, so a
    speech deployment that was present in the key vault came back missing its
    key. Nothing in the Builder could be done about it — the readiness check
    simply never passed, and the agent could not be run.
    """
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))

    state = model_endpoints.endpoint_state(spec, {"action": "gpt-54", "transcribe": "transcribe", "tts": "tts"})

    assert state["missing_secrets_by_role"]["transcribe"] == []
    assert state["missing_secrets_by_role"]["tts"] == []
    assert state["configured"] is True


def test_every_deployment_a_voice_agent_needs_is_offered_on_the_page():
    """A role missing from the page's table is dropped without a word.

    The Builder asked for a speech deployment, the readiness check counted it,
    and the page rendered no control for it — so there was nothing a person
    could click. Nobody could bind it, and nothing said why.
    """
    from pathlib import Path

    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))
    needed = {
        requirement["role"]
        for requirement in model_endpoints.endpoint_state(spec, {})["requirements"]
    }
    page = Path(__file__).resolve().parents[1] / "playground/static/js/builder/builder-page.js"
    offered = page.read_text(encoding="utf-8")
    table = offered[offered.index("reviewEndpointStepByRole") : offered.index("const dependencyRules")]

    missing = sorted(role for role in needed if f"{role}:" not in table)
    assert missing == [], f"這些角色在畫面上沒有對應的選單：{missing}"


def test_a_voice_agent_says_on_the_page_that_it_is_listening():
    """Without this the page is a text agent with a hidden microphone.

    Two things depend on it being visible: the person can tell whether it is
    hearing them, and the keyboard and the microphone are never both live —
    two inputs racing produce two turns for one question.
    """
    from playground.app import create_app

    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        for step, choice in [("input_type", "voice"), ("output_format", "voice")]:
            client.post("/playground/builder/state", json={"step": step, "choice": choice})
        page = client.get("/playground/run").get_data(as_text=True)

    assert "data-voice-bar" in page
    # Both ways between the modes, each an icon in the place the other one's
    # control sits, so switching moves nothing on the page.
    assert 'data-voice-toggle="voice"' in page
    assert 'data-voice-toggle="text"' in page
    # The voice row stands in for the typing row inside the composer rather
    # than stacking above it.
    composer = page[page.index("data-input-composer") :]
    assert composer.index("runner-message") < composer.index("data-voice-bar")


def test_a_typing_agent_gets_no_voice_bar():
    from playground.app import create_app

    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        client.post("/playground/builder/state", json={"step": "output_format", "choice": "direct"})
        page = client.get("/playground/run").get_data(as_text=True)

    assert "data-voice-bar" not in page


def test_an_agent_that_only_speaks_does_not_ask_for_a_microphone():
    """Wanting to hear the answer is not wanting to be listened to.

    Both halves set the same flag, so choosing only 語音回覆 opened the
    microphone, asked for permission, and disabled the keyboard — turning a
    typing agent that talks back into a full voice conversation.
    """
    from playground.app import create_app

    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        client.post("/playground/builder/state", json={"step": "output_format", "choice": "voice"})
        page = client.get("/playground/run").get_data(as_text=True)

    assert 'data-voice-output="true"' in page
    assert 'data-voice-input="true"' not in page
    # No microphone means no mode to switch into: the composer stays a
    # composer, and the answer simply plays.
    assert "data-voice-bar" not in page
    assert "data-voice-toggle" not in page


def test_an_agent_that_only_listens_says_so_too():
    from playground.app import create_app

    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        client.post("/playground/builder/state", json={"step": "input_type", "choice": "voice"})
        page = client.get("/playground/run").get_data(as_text=True)

    assert 'data-voice-input="true"' in page
    assert 'data-voice-output="true"' not in page


def test_choosing_voice_does_not_answer_the_other_questions():
    """A voice choice must not tick a box the person never filled in.

    The readiness list is the last place the Builder could be honest about an
    unfinished agent, and a question with no answer has to keep saying so no
    matter what the neighbouring questions were set to.
    """
    spec = build_spec(("input_type", "voice"), ("output_format", "voice"))
    state = spec_to_form_state(spec)

    assert state["choices"]["input_type"] == "voice"
    assert state["choices"]["output_format"] == "voice"
    # Never asked, so still unanswered. (memory_type, input_type and
    # retrieve_policy report a default on an untouched spec too, which is
    # older behaviour and not something a voice choice changes.)
    assert state["choices"]["failure_policy"] == ""
