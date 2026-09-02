"""The agent spec for the current Playground session.

Routes reach for the spec, not for the compiled Python text. This module is the
one place that answers "what is the session editing right now", so the Builder
and the Runner cannot disagree about it.
"""

from __future__ import annotations

from typing import Any

from flask import session

from playground.services.workflow_spec import default_spec


def current_spec() -> dict[str, Any]:
    """Return the session's v2 spec, creating one when the session has none.

    A session that has never been through the Builder gets the default spec, and
    it is stored so every later read in the same session agrees. Nothing is
    recovered from compiled text: AI Hub holds a spec for every agent.
    """
    stored = session.get("workflow_spec")
    if isinstance(stored, dict) and stored.get("version") == "2":
        return stored

    spec = default_spec()
    session["workflow_spec"] = spec
    return spec


def has_spec() -> bool:
    """Report whether this session is already editing an agent.

    Distinct from :func:`current_spec`, which answers "give me a spec" and
    creates one when the session has none. Use this wherever the absence of a
    draft is itself the answer, such as a route that redirects to the Builder.
    """
    return isinstance(session.get("workflow_spec"), dict)


def store_spec(spec: dict[str, Any]) -> None:
    """Replace the session's draft with this spec."""
    session["workflow_spec"] = spec


def clear_spec() -> None:
    """Drop the session's draft, leaving it with none."""
    session.pop("workflow_spec", None)


def reset_spec() -> dict[str, Any]:
    """Start a fresh draft, replacing whatever the session held.

    Callers that used to seed the session with default compiled text seed the
    spec instead, so the spec stays the session's one source of truth.
    """
    spec = default_spec()
    session["workflow_spec"] = spec
    return spec
