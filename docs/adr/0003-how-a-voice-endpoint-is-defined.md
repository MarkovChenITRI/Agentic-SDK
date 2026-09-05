# 3. How a voice endpoint is defined

Date: 2026-09-05

## Status

Accepted

## Context

Every module in this SDK that needs a model takes three settings — `api_key`,
`base_url`, `model` — and builds an OpenAI client from them. The documentation
says so plainly: any OpenAI-compatible endpoint, Azure AI Foundry or Ollama or
anything else.

The two voice modules did not follow that. They hand-rolled the transport: a
websocket client that assembled `intent=transcription` and an
`api-version=2025-04-01-preview` into its own URL, and an HTTP client that
posted with an `api-key` header. Both were named after Azure, and both were
what a module built for itself when no transport was passed. One vendor's
product details were sitting inside a library that claims to be vendor-neutral,
and supporting a second vendor would have meant editing the module.

They were also unnecessary. The `openai` package this project already depends
on covers all three surfaces — `audio.speech` with streaming,
`audio.transcriptions`, and `beta.realtime`, whose `connect` takes
`extra_query` and `extra_headers`. Everything the hand-rolled clients were
doing, including Azure's non-standard query parameters, goes through it.

## Decision

**The transports the SDK ships talk to OpenAI and to nothing else.** They take
no client and no vendor parameters: there is nothing to point somewhere else,
and so nothing that reads as an integration with a provider this project does
not test against and cannot promise to keep working.

**An endpoint reached differently is a subclass, written where it is chosen.**
Only opening the connection varies; the session settings, the audio frames and
the events are the same standard protocol wherever the connection came from. So
one method is overridden — `_open` for listening, `_open_stream` for speaking —
and everything else is inherited. The subclass is the caller's, and reads as
theirs.

**Resources that are not uniform are injected as objects; modules carry no list
of sources.** A chat endpoint is uniform — every OpenAI-compatible endpoint is
the same interface, so three settings describe it and a module may build the
client itself. Audio sources are not: live transcription is a long-lived
websocket, batch transcription uploads a file, synthesis streams a response, and
each has its own handshake and lifetime. Describing that family with one
endpoint's shape is how the extension path gets closed.

So the audio transport becomes a **required** constructor argument.
`require_speech_endpoint` and the endpoint settings it guarded are removed, and
with them the vendor list that lived inside the modules.

## Consequences

A custom audio source is not a special case; it is the only case. The
implementations the SDK ships are simply the ones it happens to include, and a
module cannot tell them apart from anything a caller writes.

An earlier draft of this decision let a caller hand over their own client
instead. It was wrong twice over. The arguments were not uniform — one client
needed a query parameter another rejected, so the caller had to know which
vendor they held — and the documentation had to name a vendor to show it, which
reads as support. Passing a client looks smaller than a subclass and is not.

The Playground now carries its own two subclasses, because choosing that
provider was its decision and not the SDK's. Its Builder bindings stand for the
same reason.

The Playground's stored endpoint settings do not change. The key vault holds
the endpoints that Playground offers, in whatever shape they arrive, and they
are not required to be OpenAI-shaped — that is the Playground's configuration,
not the SDK's. Turning a stored setting into a client belongs to the layer that
stored it, and stays there.

Every voice example changes with it: constructing a transport is one line more
than passing three settings, and it is the line that keeps the door open.
