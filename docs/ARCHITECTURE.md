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

## Canonical Ball-Owner Contract

Schema: `agent-handoff-ball-owner/v1`.
Version: `2026-07-15.1`.

Doctor/PWA, new ChatGPT chats, and human operators must use this enum when deriving current task ownership. Do not create a second state vocabulary in bootstrap, current-state, or component docs.

| State | Meaning | Minimal Evidence |
| --- | --- | --- |
| `codex_queue` | Runner pickup is queued. | Open GitHub issue has `agent:ready` and no stronger evidence that runner has claimed it. |
| `codex_running` | Runner/Codex owns execution. | Runner claim, active runner report, in-progress handoff artifact, or branch/worktree evidence tied to the issue. |
| `architect_review` | Architect/ChatGPT review owns the next decision. | Current PR review bundle or review-request artifact exists for the PR head SHA, or lifecycle label/state explicitly marks review. |
| `codex_followup` | Requested changes are waiting to be continued by runner on the same issue, branch, and PR. | Head-SHA-anchored `REQUEST_CHANGES` decision or equivalent review comment plus continuation/requeue intent. |
| `human_merge` | Human owner owns final review and merge decision. | Head-SHA-anchored approval, ready-for-owner-review state, or equivalent human-review request. |
| `admin_action` | Human/admin approval or privileged action is required before progress can continue. | Explicit escalation for deployment, `sudo`, secrets, production infrastructure, firewall/systemd/router config, merge authority, or other admin-only action. |
| `external_blocker` | Progress is blocked by an unavailable external dependency or outage. | Sanitized outage/blocker report for Drive, bridge, runner, GitHub, connector, credentials, or another dependency outside the current actor's control. |
| `done` | Task lifecycle is complete. | Merged/closed PR or issue, explicit completed state, or human-confirmed completion. |
| `unknown` | Ownership cannot be derived safely. | Evidence is missing, contradictory, stale, or belongs only to a non-authoritative surface. |

Precedence rules:

1. Prefer GitHub issue, PR, review, branch, label, and merge state over Drive, bridge, router, handoff, reviewer, Doctor, or PWA snapshots.
2. Treat explicit `admin_action` and `external_blocker` evidence as stronger than normal queue/review states until the escalation or blocker is resolved.
3. Treat merged/closed completion evidence as `done` unless a newer linked issue or PR shows follow-up work.
4. Treat a valid `REQUEST_CHANGES` decision as `codex_followup` until the same issue/branch/PR is rearmed with `agent:ready` and runner has picked it up.
5. Treat a valid approval or ready-for-owner-review state as `human_merge`; agents still must not merge or deploy.
6. A draft PR by itself does not imply `architect_review`. Use `architect_review` only when there is review-bundle, review-request, or explicit review lifecycle evidence for the current PR head.
7. If current evidence conflicts and no precedence rule resolves it, report `unknown` and collect fresh GitHub and handoff evidence before mutating state.

`agent:ready` is the only runner pickup label. Do not invent `agent:review` as a pickup label. `agent:review` may be used only as a review lifecycle state meaning the ball is with the architect/ChatGPT review path.

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
