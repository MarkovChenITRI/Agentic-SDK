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
