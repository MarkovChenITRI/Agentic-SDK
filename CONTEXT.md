# Context

The project's shared vocabulary. Terms are added when a decision actually
resolves one, not up front.

## Agent

An **agent** is a spec plus the deployment settings needed to run it.

The spec says what the agent is: which module fills each of the five workflow
roles, what parameters each module takes, and what limits the run has. It is
stored as JSON and is the single source of truth for the agent's behaviour.

The deployment settings say where it runs: which model endpoints its modules
bind to, and where a semantic-retrieve agent keeps its source files and vector
index. The same spec runs against different deployment settings.

An agent is not a `Workflow`. `Workflow` is the SDK class that executes one;
`build_workflow(spec, endpoint_selections)` is what turns an agent into one.

The distinction is why the execution tier is named for what it does to an
agent — `run_agent` — rather than for the format it reads.

### Not an agent

- The **compiled Python source** is an export of a spec, produced for people to
  read and for AI Hub to store. Nothing reads it back to recover an agent. The
  preview does parse it, but only to split the import block from the workflow
  block for display.
- A **Workflow** is one execution of an agent, holding the run's state.

## Interjection

An **interjection** is a person speaking while the agent is still answering.

It ends the turn, but it is not a failure. The person is steering: they heard
enough, or they heard something wrong, and they said so. A turn that ends this
way is reported as interrupted, and what the person **heard** is kept so the
next turn can carry on from it.

What was heard is not what was produced. Speech lags generation, so an
interrupted answer has a tail that was written and never spoken. That tail is
discarded, because keeping it would let the agent refer back to a sentence
nobody heard.

### Not an interjection

- An **abort** is the workflow stopping itself — a hop limit, a revisit limit,
  a timeout. Nobody asked for it, and it deserves an error on screen.
- A **turn ending normally** is the agent finishing what it had to say.

The distinction matters because the two look identical from inside the run and
must never look identical to the person. Showing someone an error for something
they did on purpose is absurd.

## The two channels of an answer

A voice agent answers on two channels at once, and they carry different things.

The **spoken content** is what the agent says aloud: conversational, the
judgement and the reason. The **displayed content** is what stays on screen:
the precise material a person needs to look at — a model number, a price, a
table, something to click.

They support each other rather than repeat each other. Reading the displayed
content aloud is the failure this distinction exists to name.

An answer may have only displayed content; then there is nothing particular to
say, and the spoken channel falls back to reading it.

## Voice agent

A **voice agent** is an agent whose input, output, or both are speech.

The two directions are independent. An agent may listen but answer in text —
someone using their voice instead of typing. It may read out an answer to
something that was typed — someone who just wants to listen. Neither half
implies the other, because the two directions do not share a connection.

## Pending input

**Pending input** is what a module has already taken in before the workflow
asks it for anything.

Most turns begin with the caller saying what the turn is about. Speech does
not: it arrives when the person feels like talking, not when a turn is
started. A module holding a live session therefore knows what this turn is
about before the workflow does, and offers it rather than waiting to be asked.

It is not a second kind of input. Whatever a module offers becomes the turn's
message in the ordinary way, so the conversation record and what the modules
see never disagree about what was said.

## Listening session

A **listening session** is one person's open microphone: the connection
carrying their audio up and the agent's audio back down.

It is named because the interruption and the answer arrive on different
connections. The person speaks on the listening session; the answer they are
speaking over is a separate request that started earlier. Without a name in
common, nothing on the first can reach the second.

A listening session ends when the page does. Nothing survives it — the next
one hears nothing of the last.

## Heard duration

The **heard duration** is how much of an answer was actually played before the
person interrupted, and only whatever was playing it can report one.

It exists because speech lags generation: the text is finished seconds before
it is spoken, so an interrupted turn has a written part that nobody heard.
The record keeps the heard part and drops the rest.

Unknown is not zero. Something that noticed the interruption without playing
the audio has no heard duration to give, and treating that as nought would
erase an answer the person did hear.
