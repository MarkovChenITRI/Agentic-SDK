from __future__ import annotations

import threading
from typing import Any


class CancellationToken:
    """A request to stop a workflow that is already running.

    Held by whoever starts the run and by whoever might want it to stop — a
    person speaking over the answer, a client closing the tab, a supervisor
    that decided the turn is no longer wanted. Setting it from another thread
    is the point, so the flag is an Event rather than a plain bool.

    The reason travels with it because stopping is not one thing: a person
    interrupting wants the workflow to pick up what they said, while a closed
    connection wants it to go away. The payload carries whatever the canceller
    knows at the moment it decides — for speech that is usually nothing yet,
    since the useful signal arrives before the words do.
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason: str = ""
        self._payload: dict[str, Any] = {}

    def cancel(self, reason: str = "cancelled", **payload: Any) -> None:
        self._reason = reason
        self._payload = dict(payload)
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def payload(self) -> dict[str, Any]:
        return dict(self._payload)

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise WorkflowInterrupted(self._reason or "cancelled", self.payload)

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)


class WorkflowInterrupted(Exception):
    """A run stopped because someone asked it to, not because it failed.

    Kept apart from WorkflowAborted so the two do not get reported the same
    way. A hop limit or a timeout is the workflow protecting itself and the
    person watching should see an error; being talked over is the person
    steering, and showing them an error for it would be absurd.
    """

    def __init__(self, reason: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.payload = dict(payload or {})
