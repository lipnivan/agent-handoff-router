# Fresh-Chat Handoff Bootstrap

Last verified: 2026-07-15.

Use this document when starting a new ChatGPT chat, Codex runner session, or human handoff with no reliable conversation memory.

## Reading Index

Read in this order:

1. [INDEX.md](INDEX.md) for the canonical entry point and component links.
2. [ARCHITECTURE.md](ARCHITECTURE.md) for source-of-truth and safety boundaries.
3. [CURRENT-STATE.md](CURRENT-STATE.md) for deployed, merged, and planned status.
4. [OPERATIONAL-WORKFLOW.md](OPERATIONAL-WORKFLOW.md) for task, review, continuation, approval, and recovery flow.
5. Component docs only as needed for the action being taken.

Central shared bootstrap:

- GitHub path: `lipnivan/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`
- Local `.39` path: `/opt/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`

## Component Repositories and Canonical Docs

- `lipnivan/agent-handoff`: central message bus, audit trail, bootstrap docs, PR bundle docs, review decision docs.
- `lipnivan/agent-handoff-router`: router docs and this canonical index.
- `lipnivan/agent-drive-bridge`: Drive command transport, typed ingress, command dispatch docs.
- `lipnivan/agent-runner`: issue polling, isolated worktree execution, Codex invocation, draft PR creation.
- `lipnivan/agent-reviewer`: read-only PR bundle collection and allowed review decision execution.
- `lipnivan/agent-doctor`: read-only pipeline diagnostics and ball-owner visualization.

Prefer repository docs over stale chat text. If local paths are available on `.39`, use the checked-out docs there for current deployed behavior. Otherwise inspect GitHub repository docs and current GitHub issue/PR state.

## Rules a New Chat Must Preserve

- Google Drive command documents plus `agent-drive-bridge` are the primary command/mutation transport.
- GitHub is the source of truth for issues, branches, PRs, reviews, labels, and lifecycle state.
- The ChatGPT GitHub connector is a temporary rescue/fallback path while Drive ingress is being built, and remains an emergency fallback for outages or bridge repair. It is not the intended primary mutation path.
- The bridge transports and dispatches canonical commands; it does not become the source of truth.
- Runner claims only `agent:ready`, works in isolated worktrees, and never merges or deploys.
- Architect/ChatGPT reviews; the human owner owns merge, deploy, and admin approval.
- Doctor/PWA is read-only and visualizes current task state and ball ownership.
- Do not run `sudo`, deploy production, merge PRs, handle secrets, or mutate firewall/systemd/router configs without explicit escalation.
- Continue `REQUEST_CHANGES` on the same issue, branch, and PR unless a human owner decides otherwise.
- Review decisions must be anchored to the current PR head SHA.

## Discover Current Queue and PR State

Do not trust stale text, old chat memory, or copied status summaries. Reconstruct current state from source-of-truth systems:

1. Read the current bootstrap/current-state docs and note `last_verified`.
2. Query GitHub issues for configured repos, especially open issues with `agent:ready`.
3. Query open draft PRs and their linked issues, head branches, and head SHAs.
4. Check `agent-handoff` outbox/inbox artifacts for current PR bundles and review decisions.
5. Check bridge, runner, reviewer, and Doctor status only as derived diagnostics.
6. If Drive/bridge ingress is deployed and healthy, use it for new mutations. Use the GitHub connector only for fallback/rescue.

Safe local discovery examples, when credentials and local installs are already present:

```bash
gh issue list --repo <owner/repo> --state open --label agent:ready
gh pr list --repo <owner/repo> --state open --json number,title,isDraft,headRefName,headRefOid,baseRefName,url
./agent-reviewer collect --repo <owner/repo> --pr <number> --project <project>
./agentctl bridge status
./agentrunner status
```

Do not run commands that mutate GitHub, system services, deployment state, secrets, or production configuration unless the current task explicitly authorizes that action.

## Copy/Paste Bootstrap Prompt

```text
You are joining the AI-agent handoff stack with no reliable conversation memory.

Read the canonical docs first:
1. lipnivan/agent-handoff-router/docs/INDEX.md
2. lipnivan/agent-handoff-router/docs/ARCHITECTURE.md
3. lipnivan/agent-handoff-router/docs/CURRENT-STATE.md
4. lipnivan/agent-handoff-router/docs/OPERATIONAL-WORKFLOW.md
5. lipnivan/agent-handoff/docs/CHATGPT-BOOTSTRAP.md

Preserve these rules:
- Google Drive command documents plus agent-drive-bridge are the primary command/mutation transport.
- GitHub is the source of truth for issues, branches, PRs, reviews, labels, and lifecycle state.
- The ChatGPT GitHub connector is fallback/rescue only while Drive ingress is being built or repaired.
- The bridge dispatches canonical commands but does not become source of truth.
- agent-runner claims only agent:ready, uses isolated worktrees, and never merges or deploys.
- ChatGPT reviews; the human owner owns merge, deploy, and admin approval.
- Doctor/PWA is read-only status and ball-owner visualization.
- Never run sudo, deploy prod, merge PRs, handle secrets, or change firewall/systemd/router configs without explicit escalation.

Before taking action, discover current GitHub issue/PR state and current handoff artifacts. Do not trust stale chat text.
```
