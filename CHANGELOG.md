# Changelog

Notable changes to this repository. The Playground and the `agentic_sdk`
package ship together from this repo, so both appear here; entries say which.

## Unreleased

### Playground — behaviour changes

**Run limits now come from the agent's spec.** An agent whose spec stores a
smaller hop, revisit or timeout limit stops at that limit. Until now every agent
ran with the SDK defaults (50 hops, 5 revisits per module, 300 seconds),
whatever its spec said, because the limits were never carried to the runtime.
Agents whose spec holds the defaults are unaffected.

**Three more settings now take effect**: the perceive module's importance, the
retrieve module's result limit, and its fallback text. Each was collected by the
Builder and then dropped before the runtime saw it.

**A brand-new draft no longer retrieves.** Before the user answers the retrieve
question, the Builder shows "none" and the agent now behaves that way. It used
to run a keyword retrieve with no entries, which could never match and fed
"No matching entries." into the model's context. Agents stored in AI Hub carry
their own retrieve setting and are unaffected.

**Executing hand-written Python is no longer supported.** The Playground runs an
agent from its spec. Nothing reads the exported Python back.

### Playground — internal

The compiled-source read path is gone: `source_builder.py` shrank from 1677 to
860 lines and `source_parser.py` was removed. The session keeps only the spec,
so a loaded agent can no longer execute a stale configuration.

## v0.1.0

First tagged release.
