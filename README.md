# agent-handoff-router

`agent-handoff-router` is the adapter between the `lipnivan/agent-handoff` message bus and executable work in target GitHub repositories.

It is separate from `agent-runner`:
- `agent-handoff` stays a message bus only.
- `agent-drive-bridge` stays a dumb Drive <-> handoff transport.
- Target repository issues remain the executable task source of truth.
- `agent-runner` continues to execute only from target repo issues labeled `agent:ready`.

This MVP scans a local clone of `lipnivan/agent-handoff`, validates structured Markdown messages, and can translate supported messages into GitHub issues or issue comments using the `gh` CLI. It also records idempotent state and writes routed reports back into the handoff repository when routing is enabled.

## Bootstrap / operating context

Canonical architecture and fresh-chat handoff entry point:
- [docs/INDEX.md](docs/INDEX.md)

For the shared operating context used across the handoff stack, read the central bootstrap doc in `lipnivan/agent-handoff`:
- GitHub: `lipnivan/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`
- Local on `.39`: `/opt/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`

This repository keeps only router-specific implementation and docs. The central bootstrap remains the source of truth for common agent workflow and operating guidance.

## Scope and safety

The router does not store secrets, credentials, raw source copies, large raw logs, or private customer data. For bootstrap, this repository only contains the router implementation. It does not modify `lipnivan/agent-handoff` unless you explicitly run routing commands against a local clone.

The MVP intentionally keeps Git behavior simple:
- scan can `git pull --ff-only` on the local handoff clone
- routing can commit generated report/state updates directly to the handoff repo's current branch
- original message files are not moved or deleted in MVP

## Install paths on `.39`

- Router repo: `/opt/agent-handoff-router`
- Handoff repo clone: `/opt/agent-handoff`
- Default state file: `/var/lib/agent-handoff-router/state.json`

## Commands

```bash
./handoff-router status
./handoff-router scan --once
./handoff-router scan --once --route
./handoff-router route /opt/agent-handoff/projects/example/inbox/chatgpt/open/task.md
./handoff-router messages --json
./handoff-router validate examples/task_request.md
./handoff-router init-config
./handoff-router self-check
```

`scan --once` lists candidates only. `scan --once --route` performs routing for supported messages.

## Configuration

Start from the example:

```bash
./handoff-router init-config
```

Default settings:
- `handoff_repo_path: /opt/agent-handoff`
- `handoff_repo: lipnivan/agent-handoff`
- `state_path: /var/lib/agent-handoff-router/state.json`
- `default_ready_label: agent:ready`
- `auto_create_missing_labels: false`
- `dry_run: false`
- `pull_before_scan: true`
- `commit_after_route: true`

## Supported MVP routing

- `task_request` with `action=create_issue` and `target_repo`
  - creates a GitHub issue in the target repo
  - uses frontmatter title, first heading, or filename as the issue title
  - appends handoff metadata to the issue body
  - treats `agent:ready` as a critical routing label unless explicitly disabled
  - skips missing optional message labels with a warning by default
  - can auto-create missing labels when `auto_create_missing_labels: true`
- `context` with `related_repo` and `related_issue`
  - comments on the related issue
- `report`
  - marks as resolved in router state only
- `question`
  - skipped for ChatGPT/user handling

Unsupported or malformed messages are recorded as failed in router state and are not deleted.

## Systemd

Example unit files are in [systemd/agent-handoff-router.service.example](systemd/agent-handoff-router.service.example) and [systemd/agent-handoff-router.timer.example](systemd/agent-handoff-router.timer.example). They are documentation/examples only. This bootstrap does not enable them.

## Examples and docs

- Message examples: [examples/task_request.md](examples/task_request.md), [examples/context_message.md](examples/context_message.md), [examples/report_message.md](examples/report_message.md), [examples/question_message.md](examples/question_message.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Canonical handoff index: [docs/INDEX.md](docs/INDEX.md)
- Fresh-chat bootstrap: [docs/CHATGPT-HANDOFF-BOOTSTRAP.md](docs/CHATGPT-HANDOFF-BOOTSTRAP.md)
- Current-state manifest: [docs/CURRENT-STATE.md](docs/CURRENT-STATE.md)
- Operational workflow: [docs/OPERATIONAL-WORKFLOW.md](docs/OPERATIONAL-WORKFLOW.md)
- Docs maintenance contract: [docs/DOCS-MAINTENANCE.md](docs/DOCS-MAINTENANCE.md)
- Contract: [docs/CONTRACT.md](docs/CONTRACT.md)
- Message types: [docs/MESSAGE-TYPES.md](docs/MESSAGE-TYPES.md)
- Routing rules: [docs/ROUTING.md](docs/ROUTING.md)
