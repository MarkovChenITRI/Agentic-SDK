from __future__ import annotations

from agentic_sdk.core import WorkflowState


ON_FAILURE_TO_NEXT: dict[str, str | None] = {"retry_plan": "plan", "end": None}


def next_after_failure(on_failure: str, state: WorkflowState) -> str | None:
    """Send the workflow back to plan once, then stop.

    "Retry" means try again, not try until the hop limit stops you. A second
    failure means re-planning did not change the outcome, so looping again only
    spends model calls to reach the same verdict and then abort.

    Both reflect modules share this because both are reached by the same
    Builder answer: "再查一次再回答" installs one or the other depending on how
    the agent retrieves, and the promise it makes is the same either way.
    """
    if on_failure != "retry_plan" or state.visit_counts.get("reflect", 0) > 1:
        return None
    return "plan"
