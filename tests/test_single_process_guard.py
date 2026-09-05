from __future__ import annotations

import pytest

from playground.main import require_single_process


def test_more_than_one_worker_is_refused():
    """Interruption needs the signal and the workflow in the same memory.

    Across processes the stop request lands somewhere else and the agent keeps
    talking — with no error anywhere. Silent failure is the worst kind, so this
    refuses to start rather than appearing to work.
    """
    with pytest.raises(RuntimeError) as refusal:
        require_single_process({"WEB_CONCURRENCY": "4"})

    assert "插話" in str(refusal.value)


@pytest.mark.parametrize(
    "environment",
    [{}, {"WEB_CONCURRENCY": "1"}, {"WEB_CONCURRENCY": ""}, {"WEB_CONCURRENCY": "not a number"}],
)
def test_one_worker_or_no_opinion_starts_normally(environment):
    require_single_process(environment)


def test_the_refusal_names_the_setting_that_caused_it():
    """Whoever changed it has to be able to find what to change back."""
    with pytest.raises(RuntimeError) as refusal:
        require_single_process({"UVICORN_WORKERS": "2"})

    assert "UVICORN_WORKERS" in str(refusal.value)
