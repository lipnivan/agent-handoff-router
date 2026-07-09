# Architecture

`agent-handoff-router` reads structured messages from a local clone of `lipnivan/agent-handoff` and translates them into actions in target GitHub repositories.

Flow:
1. `agent-drive-bridge` or a human writes a structured message into `agent-handoff`.
2. `agent-handoff-router` scans the local clone.
3. Router validates frontmatter and applies routing rules.
4. Router uses `gh` CLI to create issues or comments in the target repository.
5. Router records idempotent state and optionally writes a routed report back to the handoff repo.
6. `agent-runner` later consumes labeled target repo issues as executable tasks.

Smoke test note: the `agent-handoff-router` -> `agent-runner` E2E pipeline was smoke-tested on 2026-07-09.

Boundaries:
- `agent-handoff` is transport and audit trail, not execution state.
- Target repository issues are the task source of truth.
- Router should not store secrets or large copied artifacts.
