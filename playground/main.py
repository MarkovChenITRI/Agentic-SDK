from __future__ import annotations

import argparse
import os

import uvicorn
from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware

from playground.app import create_app


_WORKER_SETTINGS = ("WEB_CONCURRENCY", "UVICORN_WORKERS", "GUNICORN_WORKERS")


def require_single_process(environment: "dict[str, str] | None" = None) -> None:
    """Refuse to start where interruption would silently stop working.

    An interjection cancels a workflow by setting a flag the running workflow
    can see, which only holds inside one process. Add workers and the request
    to stop lands in a different one: the agent keeps talking, and nothing
    anywhere reports an error.

    Raising here is the point. A voice agent that has quietly lost the ability
    to be interrupted looks exactly like one that works.
    """
    values = os.environ if environment is None else environment
    for setting in _WORKER_SETTINGS:
        raw = str(values.get(setting) or "").strip()
        if not raw:
            continue
        try:
            workers = int(raw)
        except ValueError:
            continue
        if workers > 1:
            raise RuntimeError(
                f"{setting}={workers} 會讓插話功能靜默失效。中斷訊號必須和它要停止的"
                f"工作流在同一個行程，多個 worker 時訊號會落在別的行程，agent 會繼續"
                f"講而且不會有任何錯誤。請把 {setting} 設為 1，或移除它。"
            )


app = FastAPI(title="Agentic SDK Playground")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/", WSGIMiddleware(create_app()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agentic SDK Playground web app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", os.environ.get("WEBSITES_PORT", "80"))))
    args = parser.parse_args()
    require_single_process()

    uvicorn.run(
        "playground.main:app",
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()