# Current-State Manifest

Version: 2026-07-15.1  
Last verified: 2026-07-15  
Verifier: Codex runner for `lipnivan/agent-handoff-router` issue #8  
Scope: Documentation state reconstructed from this repository plus local component docs on `.39`.

## Structured Manifest

```yaml
schema: agent-handoff-current-state/v1
version: 2026-07-15.1
last_verified: 2026-07-15
source_of_truth:
  lifecycle: GitHub issues, branches, PRs, reviews, labels
  code: component repositories
  audit: lipnivan/agent-handoff messages and artifacts
  transport: Google Drive command documents plus agent-drive-bridge
primary_transport:
  name: Google Drive command documents plus agent-drive-bridge
  status: merged for bridge command handling in documented worktree; intended primary for mutations
fallback_transport:
  name: ChatGPT GitHub connector
  status: temporary rescue/fallback while Drive ingress is being built; emergency fallback for outages or bridge repair
runner_pickup_label: agent:ready
human_owned_actions:
  - merge
  - deploy
  - admin approval
  - secrets
  - production infrastructure changes
global_forbidden_for_agents:
  - merge_prs
  - deploy_prod
  - sudo
  - handle_secrets
  - mutate_firewall_systemd_router_configs_without_escalation
```

## Deployed or Locally Documented Behavior

- `agent-handoff-router` scans `agent-handoff` messages, validates frontmatter, creates GitHub issues or comments, applies `agent:ready` as the default critical runner label, and records idempotent state.
- The router-to-runner smoke was completed on 2026-07-09: a handoff message created an issue in `lipnivan/agent-handoff-router`, `agent-runner` picked it up, Codex produced a draft PR, and Ivan merged it.
- `agent-runner` scans configured repositories for `agent:ready`, runs Codex in isolated worktrees, and opens draft PRs.
- `agent-reviewer` can collect read-only PR bundles with `gh` and writes them into `agent-handoff`.
- `agent-doctor` exists as a compact diagnostics tool, with current docs noting a limitation that the imported script is still cwd/repo-local rather than fully system-wide.

## Merged or Documented in Component Worktrees

- `agent-drive-bridge` documents Google Drive via `rclone` as default transport, GitHub as source of truth, Gmail disabled, and ChatGPT GitHub connector as fallback-only.
- `agent-drive-bridge` documents command handling for `create_task`, `comment_issue`, `comment_pr`, `review_pr`, `request_status`, `continue_task`, and `summarize_latest`.
- `agent-drive-bridge` documents typed local ingress that serializes authenticated JSON requests into canonical Drive command documents.
- `agent-drive-bridge` documents guarded `continue_task` behavior on the same issue and PR with head-SHA checks and `agent:ready` rearming.
- `agent-drive-bridge` documents formal PR review commands with reviewer-token isolation and optional head-SHA validation.
- `agent-handoff` documents PR review bundles and review decisions as canonical review artifacts.

## Planned or Not Yet Fully Canonicalized Here

- Drive ingress is the intended primary ChatGPT mutation path once deployed and healthy everywhere. Until then, the ChatGPT GitHub connector remains fallback/rescue only.
- Doctor/PWA should visualize current task and ball ownership from source-of-truth state without becoming a mutation path.
- Component docs should continue moving implementation detail into their own repositories, with this repo serving as the cross-component canonical index.
- Recovery runbooks should be expanded as real outage repairs occur.

## Known Limitations

- This manifest was verified from local docs and current worktree content, not by mutating live services.
- External GitHub URLs were not network-validated during this documentation task.
- Local component paths may differ outside `.39`.
- Historical labels such as `agent:review` may appear in older state, but runner pickup is `agent:ready`.
- The bridge and reviewer command capabilities must be rechecked against their current repository docs before relying on a specific command in production.

## Next Milestones

- Confirm Drive ingress deployment status in the canonical `agent-drive-bridge` repository docs.
- Add or link a system-wide Doctor/PWA ball-owner view once implemented.
- Keep PR review bundle and review decision examples aligned with the latest bridge/reviewer command formats.
- Add a small link-check or docs consistency check for canonical documentation updates.

## Component Links

- Router architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Router workflow: [OPERATIONAL-WORKFLOW.md](OPERATIONAL-WORKFLOW.md)
- Fresh-chat bootstrap: [CHATGPT-HANDOFF-BOOTSTRAP.md](CHATGPT-HANDOFF-BOOTSTRAP.md)
- Router contract: [CONTRACT.md](CONTRACT.md)
- Router routing rules: [ROUTING.md](ROUTING.md)
- Router message types: [MESSAGE-TYPES.md](MESSAGE-TYPES.md)
- Central bootstrap: `lipnivan/agent-handoff/docs/CHATGPT-BOOTSTRAP.md`
- Central PR bundle docs: `lipnivan/agent-handoff/docs/PR-REVIEW-BUNDLES.md`
- Central review decision docs: `lipnivan/agent-handoff/docs/REVIEW-DECISIONS.md`
