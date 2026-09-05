"""An answer that is said aloud and shown on screen, carrying different things.

Reading the screen out loud is the failure this module exists to avoid. The
spoken channel is conversational — the judgement and the reason — while the
screen holds what a person needs to look at: a model number, a price, a table.
They support each other rather than repeat each other.

Speaking begins as soon as the spoken half is written, not when the whole
answer is. Waiting would put a pause in front of every reply, and the pause is
what makes an agent feel like a form rather than a conversation.
"""

from __future__ import annotations

import json
from typing import Any

from agentic_sdk.audio.speech_rate import heard_portion
from agentic_sdk.audio.transport import AudioOutputTransport, require_speech_endpoint
from agentic_sdk.core import ContextEntry, ContextEntryType, ModuleOutput, WorkflowState
from agentic_sdk.core.cancellation import WorkflowInterrupted
from agentic_sdk.llm import chat_stream_json
from agentic_sdk.modules.action.generative import (
    GenerativeAction,
    _build_messages,
    _format_openai_error,
)


TWO_CHANNEL_CONTRACT = (
    "回覆必須是 JSON，包含 spoken 與 displayed 兩個欄位。"
    "spoken 是要說出口的話：口語、精簡，講重點與判斷理由，不要唸出編號、價格表或條列。"
    "displayed 是要顯示在畫面上的內容：精確、可掃視，放型號、數字、條列或表格。"
    "兩者互相補充，不要讓 spoken 只是把 displayed 唸一遍。"
)


class VoiceAnswerAction(GenerativeAction):
    """Generate the reply, show one half of it and say the other."""

    def __init__(
        self,
        *,
        speech: AudioOutputTransport | None = None,
        speech_api_key: str | None = None,
        speech_base_url: str | None = None,
        speech_model: str | None = None,
        voice: str = "alloy",
        **generative: Any,
    ) -> None:
        """Answer on the given speech endpoint, or through a transport of your own.

        The generation settings are the same three as every other module, and
        the speech settings mirror them, because this module talks to two
        services and a caller configuring it needs to see which is which.
        """
        system_prompt = generative.pop("system_prompt", None)
        super().__init__(
            system_prompt=_with_two_channel_contract(system_prompt), **generative
        )
        if speech is None:
            require_speech_endpoint(
                speech_api_key=speech_api_key,
                speech_base_url=speech_base_url,
                speech_model=speech_model,
            )
            from agentic_sdk.audio.azure_speech import AzureSpeechOutput

            speech = AzureSpeechOutput(
                api_key=speech_api_key,
                base_url=speech_base_url,
                model=speech_model,
                voice=voice,
            )
        self._speech = speech

    def __call__(self, state: WorkflowState) -> ModuleOutput:
        said: list[str] = []

        def say(field: str, value: Any) -> None:
            # Reached from inside the stream, the moment the field closes —
            # which is the whole point of asking for it as a structured field
            # rather than parsing the finished answer.
            if field == "spoken" and not said:
                spoken = str(value or "").strip()
                if spoken:
                    said.append(spoken)
                    self._speak(spoken, state)

        try:
            response = chat_stream_json(
                self._client,
                model=self._model,
                messages=_build_messages(state, self._system_prompt),
                temperature=self._temperature,
                should_stop=state.should_stop,
                structured_fields=("spoken",),
                on_field=say,
                on_delta=lambda content: state.emit_token_delta(
                    self.name, content, metadata={"model": self._model, "structured": True}
                ),
            )
        except Exception as exc:
            detail = _format_openai_error(exc)
            state.last_action_error = {"type": type(exc).__name__, "message": detail}
            return ModuleOutput(
                next_module=None,
                payload={"_llm_usage": None},
                context_updates=[
                    ContextEntry(
                        type=ContextEntryType.ACTION_RESULT,
                        content=f"error:{type(exc).__name__}",
                        metadata={"ok": False, "error": detail},
                    )
                ],
            )

        spoken, displayed = _split_channels(response.content)
        state.last_action_error = None
        state.last_action_result = {"content": displayed, "model": response.model or self._model}
        if not said and spoken:
            # The field never closed cleanly — say it now rather than not at all.
            self._speak(spoken, state)
        return ModuleOutput(
            next_module=None,
            payload={
                "latest_final_message": displayed,
                "_llm_usage": {
                    "model": response.model or self._model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            },
            context_updates=[
                ContextEntry(
                    type=ContextEntryType.ACTION_RESULT,
                    content=displayed,
                    metadata={"ok": True, "spoken": spoken, "source": "voice_answer_action"},
                )
            ],
        )

    def _speak(self, text: str, state: WorkflowState) -> None:
        """Play the words out, and stop the moment the person talks over them.

        What is reported afterwards is the part that was actually played, not
        the part that was written. They differ whenever someone interrupts,
        and keeping the difference is what stops the next turn referring back
        to a sentence nobody heard.
        """
        interrupted = False
        for _piece in self._speech.speak(text):
            if state.should_stop():
                interrupted = True
                break
        if not interrupted:
            state.report_spoken_progress(text)
            return
        heard_seconds = (state.cancel.payload if state.cancel else {}).get("heard_seconds")
        state.report_spoken_progress(heard_portion(text, heard_seconds))


def _with_two_channel_contract(system_prompt: str | None) -> str:
    if not system_prompt:
        return TWO_CHANNEL_CONTRACT
    return f"{system_prompt}\n\n{TWO_CHANNEL_CONTRACT}"


def _split_channels(content: str) -> tuple[str, str]:
    """Pull the two channels out of the reply, tolerating one that has neither.

    An answer with nothing particular to say is a plain answer, not a broken
    one: it goes on the screen and is read out as it stands.
    """
    text = str(content or "").strip()
    try:
        parsed = json.loads(text)
    except ValueError:
        return text, text
    if not isinstance(parsed, dict):
        return text, text
    displayed = str(parsed.get("displayed") or "").strip()
    spoken = str(parsed.get("spoken") or "").strip()
    if not displayed and not spoken:
        return text, text
    return spoken or displayed, displayed or spoken
