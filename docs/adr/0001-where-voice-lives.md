# 1. Where voice lives in the workflow

Date: 2026-09-05

## Status

Accepted

## Context

A voice agent has to do three things the SDK had never done: listen while it is
talking, stop mid-sentence when someone talks over it, and answer on two
channels at once.

The obvious place to put all of it is the perceive module. It already owns the
live audio session — the transcription websocket stays open across turns — and
it is the module that knows when someone started speaking. Putting the spoken
output there too would mean one module owning the microphone and the speaker,
which reads as tidy.

A spike measured what the current architecture can already do
(`spikes/realtime-interjection/`). Three findings shaped this decision:

- A module is an object the workflow keeps, so it outlives a turn and can hold
  a session open. The cancellation token is one object per run, so the token a
  module receives during its own turn is the same one that will stop a later
  module. A perceive module can therefore interrupt an action module without
  any change to the one-call-one-return contract.
- `state.apply` runs after a module returns, so an interrupted module leaves no
  half-written state. Resuming after an interjection is clean by construction.
- Transcription and speech are **not the same connection**. Transcription is a
  long-lived websocket; speech is a per-answer streaming request. Nothing is
  shared between them.

## Decision

**Cancellation belongs to the SDK; audio belongs to the Playground.** The core
learns only that a run can be stopped and by whom. Nothing in the module
standard knows a microphone exists.

**Input belongs to perceive; output belongs to action.** `VoiceTextPerceive`
turns speech into text and raises the interjection. `VoiceAnswerAction`
produces the answer and speaks it.

**The spoken channel is an optional field on an answer**, not a required one.
An action that does not produce one is read aloud verbatim.

## Consequences

Speaking is an action, and the roles say so. `ToolCallAction` already sends its
output somewhere other than the screen; speech is the same shape.

The tidiness that argued for perceive owning both turned out to be imaginary,
because the two directions never shared a connection. What it would have cost
is real: perceive would have had to subscribe to action's output, which is the
wrong direction for a dependency and needs a fan-out the core does not have.

Concurrency survives the split. An action can stream its spoken content to
speech synthesis as soon as that field completes, while it is still producing
the displayed content, so the person hears the beginning before the answer is
finished. This needed no asynchronous execution model.

The interruption fires on voice activity, not on words. Speech is detected
about 600 ms after someone opens their mouth; the transcript takes about four
seconds. Waiting for the words would not be interrupting.

What survives the interruption is what the person **heard**, not what the model
produced. Those differ: speech lags generation, so the tail was written but
never spoken. Keeping it would let the next turn refer back to a sentence
nobody heard. This follows the same reasoning OpenAI's realtime API encodes in
`conversation.item.truncate`, which deletes the transcript of the unplayed
portion for exactly this reason.

One thing did have to change in the core, and it is worth naming because the
rest of this decision is about keeping voice out of it. `Workflow.run` refused
to start without a message, which a voice agent can never supply up front —
the words arrive when the person speaks, not when the turn begins. A module
may now offer what it has already taken in. The hook says nothing about audio
and any module may implement it; what it admits is that the caller is not
always the one who knows what a turn is about.

The Playground must run in one process. The interjection and the workflow it
stops have to share memory, and adding worker processes would break that
silently — so the startup refuses to run with more than one.
