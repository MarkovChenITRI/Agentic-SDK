from __future__ import annotations

from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput, WorkflowState


_ON_FAILURE_TO_NEXT: dict[str, str | None] = {"retry_plan": "plan", "end": None}


class EvidenceCheckReflect:
    name = "reflect"

    def __init__(self, on_failure: str = "retry_plan") -> None:
        if on_failure not in _ON_FAILURE_TO_NEXT:
            raise ValueError(f"unsupported on_failure={on_failure!r}")
        self._on_failure = on_failure

    def __call__(self, state: WorkflowState) -> ModuleOutput:
        err = state.last_action_error
        evidence_error = _evidence_error(state)
        verdict = "fail" if err or evidence_error else "pass"
        if err:
            reason = str(err.get("message", "unknown action error"))
        elif evidence_error:
            reason = evidence_error
        else:
            reason = "action_result ok"
        next_module = _next_after_failure(self._on_failure, state) if verdict == "fail" else None
        return ModuleOutput(
            next_module=next_module,
            payload={"reflect_verdict": verdict},
            context_updates=[
                ContextEntry(
                    type=ContextEntryType.REFLECTION,
                    content=f"verdict={verdict} reason={reason}",
                    metadata={"verdict": verdict, "reason": reason, "strategy": "evidence_check"},
                )
            ],
        )


def _next_after_failure(on_failure: str, state: WorkflowState) -> str | None:
    """Send the workflow back to plan once, then stop.

    "Retry" means try again, not try until the hop limit stops you. A second
    failure means re-planning did not change the outcome, so looping again only
    spends model calls to reach the same verdict and then abort.
    """
    if on_failure != "retry_plan" or state.visit_counts.get("reflect", 0) > 1:
        return None
    return "plan"


def _evidence_error(state: WorkflowState) -> str | None:
    """Report an error when the workflow looked something up and found nothing.

    A retrieve module that does not look anything up reports no count at all,
    and gets no verdict: it has no claim to make about evidence.
    """
    retrieved = state.latest_of(ContextEntryType.RETRIEVED)
    if retrieved is None or "hit_count" not in retrieved.metadata:
        return None
    if int(retrieved.metadata.get("hit_count") or 0) == 0:
        return "no retrieved evidence"
    return None
