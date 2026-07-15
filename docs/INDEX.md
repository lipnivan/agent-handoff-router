# AI-Agent Handoff Canonical Index

Last verified: 2026-07-15.

This is the single canonical entry point for reconstructing the current AI-agent handoff architecture in a fresh ChatGPT chat, Codex runner, or human operator session.

## Read First

1. [ARCHITECTURE.md](ARCHITECTURE.md) - component responsibilities, source-of-truth boundaries, lifecycle states, trust boundaries, and safety rules.
2. [OPERATIONAL-WORKFLOW.md](OPERATIONAL-WORKFLOW.md) - task creation, runner execution, review, continuation, approval, escalation, and recovery.
3. [CHATGPT-HANDOFF-BOOTSTRAP.md](CHATGPT-HANDOFF-BOOTSTRAP.md) - ordered reading list, exact new-chat rules, live-state discovery, and copy/paste bootstrap prompt.
4. [CURRENT-STATE.md](CURRENT-STATE.md) - versioned manifest of repository, deployment, planned, and limited behavior.
5. [DOCS-MAINTENANCE.md](DOCS-MAINTENANCE.md) - update triggers, ownership, stale-doc warning, and validation checklist.

## Non-Negotiable Architecture Rules

- Google Drive command documents plus `agent-drive-bridge` are the primary command/mutation transport.
- GitHub is the source of truth for issues, branches, PRs, reviews, labels, and lifecycle state.
- The ChatGPT GitHub connector is a temporary rescue/fallback path while Drive ingress is being built, and remains an emergency fallback for outages or bridge repair. It is not the intended primary mutation path.
- The bridge transports and dispatches canonical commands; it does not become the source of truth.
- Runner claims only `agent:ready`, works in isolated worktrees, and never merges or deploys.
- Architect/ChatGPT reviews; the human owner owns merge, deploy, and admin approval.
- Doctor/PWA is read-only and visualizes current task state and ball ownership.
- Never run `sudo`, deploy production, merge PRs, handle secrets, or mutate firewall/systemd/router configs without explicit escalation.

## Component Docs

Central shared docs:

- `lipnivan/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`
- `lipnivan/agent-handoff/docs/PR-REVIEW-BUNDLES.md`
- `lipnivan/agent-handoff/docs/REVIEW-DECISIONS.md`
- `lipnivan/agent-handoff/docs/SERVICES.md`
- `lipnivan/agent-handoff/docs/DRIVE-DOCS-MIRROR.md`

Router docs in this repository:

- [CONTRACT.md](CONTRACT.md)
- [ROUTING.md](ROUTING.md)
- [MESSAGE-TYPES.md](MESSAGE-TYPES.md)

Component repositories:

- `lipnivan/agent-handoff`
- `lipnivan/agent-handoff-router`
- `lipi-codex/agent-drive-bridge`
- `lipnivan/agent-runner`
- `lipnivan/agent-reviewer`
- `lipnivan/agent-doctor`

## State Discovery Rule

Do not trust old chat text. Discover current state from GitHub issues, branches, PRs, reviews, labels, and current component docs. Treat Drive, handoff messages, bridge snapshots, router state, reviewer bundles, Doctor, and PWA as transport, audit, or derived status unless the specific state belongs to that component.

Use Drive/bridge as the primary mutation path once ingress is deployed and healthy. Use the ChatGPT GitHub connector only as fallback/rescue for outages, bridge repair, or cases where the primary path is unavailable and a human accepts the fallback.
