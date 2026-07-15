# Architecture

Last verified: 2026-07-15.

This is the canonical architecture overview for the AI-agent handoff stack. It is intentionally concise: component-specific implementation detail belongs in the component repositories linked from [INDEX.md](INDEX.md).

## Components and Responsibilities

- Google Drive command documents plus `agent-drive-bridge` are the primary command/mutation transport. ChatGPT or a human writes canonical command documents; the bridge validates and dispatches supported commands.
- `agent-handoff` is the message bus, audit trail, and bootstrap anchor. It is not a product source-code repository and does not own task lifecycle state.
- `agent-handoff-router` reads structured handoff messages and creates or comments on GitHub issues using `gh`. It records idempotent routing state and report artifacts.
- GitHub is the source of truth for issues, branches, PRs, reviews, labels, and lifecycle state.
- `agent-runner` claims only GitHub issues labeled `agent:ready`, works in isolated worktrees, invokes Codex, and opens or updates draft PRs.
- `agent-reviewer` or a collector on `.39` gathers read-only PR bundles with `gh`, writes bundles into `agent-handoff`, and may execute only review actions authorized by a head-SHA-anchored review decision.
- ChatGPT reviews PR bundles and writes decisions. ChatGPT does not merge, deploy, or administer infrastructure.
- The human owner reviews final state and owns merge, deploy, and admin approval.
- `agent-doctor` and any PWA viewer are read-only status surfaces that visualize current task state and ball ownership.

## Primary and Fallback Paths

Primary command/mutation path:

```text
ChatGPT or human
  -> Google Drive command document
  -> agent-drive-bridge
  -> GitHub issue/comment/review command
  -> GitHub lifecycle state
```

Bridge-to-router path for handoff messages:

```text
ChatGPT or Drive
  -> agent-drive-bridge
  -> agent-handoff message
  -> agent-handoff-router
  -> target GitHub issue/comment
```

Execution and review path:

```text
GitHub issue labeled agent:ready
  -> agent-runner
  -> isolated worktree + Codex
  -> draft PR
  -> agent-reviewer PR bundle
  -> ChatGPT review decision
  -> allowed review action
  -> human merge decision
```

The ChatGPT GitHub connector is a temporary rescue/fallback path while Drive ingress is being built, and remains an emergency fallback for outages or bridge repair. It is not the intended primary mutation path. When the bridge ingress is available, new chats must prefer Drive/bridge commands for mutation and use the connector only after explicitly identifying the primary path as unavailable or unsafe.

## Source-of-Truth Boundaries

- GitHub owns issues, branches, PRs, reviews, labels, assignees, and merge state.
- Each component repository owns its code and component-specific docs.
- `agent-handoff` owns message artifacts, review bundles, reports, and bootstrap docs.
- Google Drive command documents are transport inputs and mirrored reading surfaces; they do not replace GitHub or component repositories.
- The bridge transports and dispatches canonical commands. It must not become the source of truth for task state, PR state, reviews, or product code.
- Router state is idempotency and diagnostics only; it is not lifecycle truth.
- Doctor/PWA state is read-only derived state and must not be treated as authoritative mutation state.

## Lifecycle and Ball Owner

Use GitHub state plus handoff artifacts to determine the current ball owner:

- New command: ball is with bridge/router until a GitHub issue or comment is created.
- `agent:ready`: ball is with `agent-runner`; this is the only runner pickup label.
- Claimed/running: ball is with `agent-runner` and Codex in an isolated worktree.
- Draft PR opened: ball is with review collection.
- PR bundle published: ball is with ChatGPT for review.
- `REQUEST_CHANGES`: ball returns to runner on the same issue, branch, and PR after the continuation is posted and `agent:ready` is applied.
- `APPROVE`: ball moves to human owner for final review and merge.
- Admin action needed: ball is with human/admin approver until explicit approval is granted.
- Blocked or outage: ball is with the component owner of the unavailable dependency.

Do not invent `agent:review` as the runner pickup label. `agent:review` is a review lifecycle state meaning the ball is with the architect/ChatGPT review path; runner pickup remains only `agent:ready`. After `REQUEST_CHANGES`, continuation should keep the same issue, branch, and PR, then reapply `agent:ready` for runner pickup.

## Trust and Credential Boundaries

- Bridge credentials may dispatch validated GitHub commands and use Drive transport, but must not expose tokens or become a general admin shell.
- Runner credentials may create branches and draft PRs for configured repositories. Runner must not merge, deploy, run `sudo`, or handle secrets.
- Reviewer credentials may collect PR data and execute explicitly allowed review actions. Formal review commands must be anchored to the current PR head SHA.
- ChatGPT may produce command documents and review decisions, but does not directly own credentials or final approval.
- Human owner credentials are required for merge, deployment, infrastructure changes, secrets, and admin approval.
- Doctor/PWA credentials, if any, must be read-only.

## Global No-Go Rules

- Do not merge PRs.
- Do not deploy production.
- Do not run `sudo`.
- Do not handle secrets, tokens, or private customer data.
- Do not modify firewall, systemd, router, or production service configuration without explicit human/admin escalation.
- Do not mutate historical audit artifacts unless a documented repair procedure explicitly requires it.
