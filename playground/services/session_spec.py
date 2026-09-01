"""The agent spec for the current Playground session.

Routes reach for the spec, not for the compiled Python text. This module is the
one place that answers "what is the session editing right now", so the Builder
and the Runner cannot disagree about it.
"""

from __future__ import annotations

from typing import Any

from flask import session

from playground.services.workflow_spec import default_spec, validate_runner_presentation


def current_spec() -> dict[str, Any]:
    """Return the session's v2 spec, creating one when the session has none.

    A session that has never been through the Builder gets the default spec, and
    it is stored so every later read in the same session agrees.
    """
    stored = session.get("workflow_spec")
    if isinstance(stored, dict) and stored.get("version") == "2":
        return stored

    python_source = session.get("python_source")
    if python_source:
        spec = _spec_from_legacy_source(python_source)
        if spec is not None:
            session["workflow_spec"] = spec
            return spec

    spec = default_spec()
    session["workflow_spec"] = spec
    return spec


def store_spec(spec: dict[str, Any]) -> None:
    session["workflow_spec"] = spec


def _spec_from_legacy_source(python_source: str) -> dict[str, Any] | None:
    """Recover a spec from a session that only holds compiled Python text.

    Sessions created before the Builder stored a spec still carry the text. The
    recovery reads it once and stores the result, so the text is never read
    again for that session. It goes away with the compiled-source read path.
    """
    from playground.services.source_builder import _config_from_source

    try:
        config = _config_from_source(python_source)
    except Exception:
        return None
    return _config_to_spec(config)


def _config_to_spec(config) -> dict[str, Any]:
    spec = default_spec(workflow_name=config.workflow_name)
    spec["description"] = config.task_goal or ""
    spec["memory"]["kind"] = "in_context"
    spec["perceive"]["module"] = config.perceive_module
    spec["perceive"]["params"] = {
        "input_label": config.perceive_input_label,
        "welcome_message": config.perceive_welcome_message,
        "options": list(config.perceive_options),
        "importance": config.perceive_importance,
        "image_instruction": config.perceive_image_instruction,
    }
    spec["retrieve"]["module"] = config.retrieve_module
    spec["retrieve"]["params"] = {
        "description": config.retrieve_description,
        "items": list(config.retrieve_items),
        "fallback": config.retrieve_fallback,
        "top_k": config.retrieve_top_k,
        "support_files": list(config.semantic_support_files),
        "search_goal": config.semantic_search_goal,
    }
    if config.plan_strategy:
        spec["plan"]["module"] = "NextStepPlan"
        spec["plan"]["params"]["strategy"] = config.plan_strategy
        spec["plan"]["params"]["system_prompt"] = config.plan_system_prompt
    spec["action"]["module"] = config.action_module
    spec["action"]["params"] = {
        "output_format": "interactive" if config.action_module == "ToolCallAction" else "free_text",
        "system_prompt": config.action_prompt,
        "tools": list(config.action_tools),
        "tool_choice": config.action_tool_choice,
        "memory_key": config.direct_answer_memory_key,
        "fallback": config.direct_answer_fallback,
        "prefix": config.direct_answer_prefix,
    }
    if config.reflect_module:
        spec["reflect"]["module"] = config.reflect_module
        spec["reflect"]["params"]["on_failure"] = config.reflect_on_failure
    spec["entry_module"] = config.entry_module
    if config.starter_questions:
        presentation = validate_runner_presentation(session.get("runner_presentation"))
        if not presentation.get("starter_questions"):
            presentation["starter_questions"] = list(config.starter_questions)
            session["runner_presentation"] = presentation
    return spec
