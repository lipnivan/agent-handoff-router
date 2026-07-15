# Current-State Manifest

Version: 2026-07-15.3
Last verified: 2026-07-15
Verifier: Codex runner for `lipnivan/agent-handoff-router` issue #8, with evidence listed in the structured manifest below
Scope: Documentation state reconstructed from this repository, local component docs on `.39`, and read-only GitHub PR metadata where noted. Deployment state was not changed or exhaustively verified by this documentation task.

## Structured Manifest

```yaml
schema: agent-handoff-current-state/v1
version: 2026-07-15.3
last_verified: 2026-07-15
verification:
  verifier: Codex runner for lipnivan/agent-handoff-router issue #8
  github_metadata_checked:
    - repo: lipi-codex/agent-drive-bridge
      pr: 10
      state: MERGED
      merged_at: 2026-07-15T09:45:18Z
      head_sha: af6e5adf2d3c872001c5e8765b33353ad3e7e851
      merge_commit: 7d5e537ac5f6c2a96c740ab6331fb8c3de8b075e
      url: https://github.com/lipi-codex/agent-drive-bridge/pull/10
    - repo: lipnivan/agent-runner
      pr: 10
      state: MERGED
      merged_at: 2026-07-15T00:15:54Z
      head_sha: c1c551ad3045885e905673f4ee277cecf50d515c
      url: https://github.com/lipnivan/agent-runner/pull/10
    - repo: lipnivan/agent-runner
      pr: 12
      state: MERGED
      merged_at: 2026-07-15T10:25:03Z
      head_sha: f312cd9c93d75321e2e043d3dc1b2d4507bf0fab
      merge_commit: bb741aaddb1ffed75babcf4ede1067b8585a9603
      url: https://github.com/lipnivan/agent-runner/pull/12
    - repo: lipnivan/agent-doctor
      pr: 6
      state: MERGED
      merged_at: 2026-07-14T23:49:27Z
      head_sha: 81f18a82b2484a87239e2afc9e787439d26f0b73
      url: https://github.com/lipnivan/agent-doctor/pull/6
  deployment_checked: false
source_of_truth:
  lifecycle: GitHub issues, branches, PRs, reviews, labels
  code: component repositories
  audit: lipnivan/agent-handoff messages and artifacts
  transport: Google Drive command documents plus agent-drive-bridge
primary_transport:
  name: Google Drive command documents plus agent-drive-bridge
  status: primary command/mutation transport; typed ingress is merged in the bridge repository, but deployment remains unknown until separately verified
fallback_transport:
  name: ChatGPT GitHub connector
  status: temporary rescue/fallback while Drive ingress is being built; emergency fallback for outages or bridge repair
runner_pickup_label: agent:ready
review_lifecycle_label: agent:review
ball_owner_contract:
  schema: agent-handoff-ball-owner/v1
  version: 2026-07-15.1
  canonical_doc: docs/ARCHITECTURE.md#canonical-ball-owner-contract
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

## Component State

```yaml
components:
  agent-handoff:
    repo: lipnivan/agent-handoff
    role: central message bus, audit trail, bootstrap docs, PR bundle docs, review decision docs
    repository_state: current docs available in local /opt/agent-handoff checkout for this task
    deployment_state: unknown
    evidence:
      - /opt/agent-handoff/docs/CHATGPT-BOOTSTRAP.md read during this task
    last_verified: 2026-07-15
  agent-handoff-router:
    repo: lipnivan/agent-handoff-router
    role: routes handoff messages into GitHub issues/comments
    repository_state: this worktree contains the canonical docs update for issue #8
    deployment_state: unknown
    evidence:
      - local worktree /opt/agent-worktrees/agent-handoff-router/issue-8
    last_verified: 2026-07-15
  agent-drive-bridge:
    repo: lipi-codex/agent-drive-bridge
    role: Drive command transport, command validation, and dispatch
    repository_state: typed ingress PR #10 is merged
    deployment_state: unknown
    evidence:
      - GitHub PR #10 read-only metadata: MERGED at 2026-07-15T09:45:18Z, head af6e5adf2d3c872001c5e8765b33353ad3e7e851, merge commit 7d5e537ac5f6c2a96c740ab6331fb8c3de8b075e
      - local worktree remote confirms lipi-codex/agent-drive-bridge
    last_verified: 2026-07-15
  agent-runner:
    repo: lipnivan/agent-runner
    role: claims agent:ready issues, runs Codex in isolated worktrees, opens/updates draft PRs
    repository_state: PR #10 for sequential drain is merged; PR #12 for duplicate Done/Review-needed push fixes is merged
    deployment_state: unknown; production checkout/systemd timer deployment on .39 not confirmed by this docs task
    evidence:
      - GitHub PR #10 read-only metadata: MERGED at 2026-07-15T00:15:54Z, head c1c551ad3045885e905673f4ee277cecf50d515c
      - GitHub PR #12 read-only metadata: MERGED at 2026-07-15T10:25:03Z, head f312cd9c93d75321e2e043d3dc1b2d4507bf0fab, merge commit bb741aaddb1ffed75babcf4ede1067b8585a9603
      - /opt/agent-runner local checkout exists on main, but local checkout state alone is not deployment proof
    last_verified: 2026-07-15
  agent-reviewer:
    repo: lipnivan/agent-reviewer
    role: collects read-only PR bundles and executes allowed review actions
    repository_state: local repository reference verified
    deployment_state: unknown
    evidence:
      - /opt/agent-reviewer remote points to lipnivan/agent-reviewer
    last_verified: 2026-07-15
  agent-doctor:
    repo: lipnivan/agent-doctor
    role: read-only diagnostics and ball-owner/status visualization
    repository_state: PR #6 is merged
    deployment_state: unknown; installed /opt/agent-doctor or live behavior update not confirmed by this docs task
    evidence:
      - GitHub PR #6 read-only metadata: MERGED at 2026-07-14T23:49:27Z, head 81f18a82b2484a87239e2afc9e787439d26f0b73
      - /opt/agent-doctor local checkout exists, but local checkout state alone is not deployment proof
    last_verified: 2026-07-15
```

## Deployed Behavior Confirmed Here

This docs task did not deploy, restart, or mutate production services, and did not conclusively verify live deployment state for the components above. Treat deployment fields marked `unknown` as requiring a separate authorized service/deployment check.

## Locally Documented Behavior

- `agent-handoff-router` scans `agent-handoff` messages, validates frontmatter, creates GitHub issues or comments, applies `agent:ready` as the default critical runner label, and records idempotent state.
- The router-to-runner smoke was completed on 2026-07-09: a handoff message created an issue in `lipnivan/agent-handoff-router`, `agent-runner` picked it up, Codex produced a draft PR, and Ivan merged it.
- `agent-runner` scans configured repositories for `agent:ready`, runs Codex in isolated worktrees, and opens draft PRs.
- `agent-reviewer` can collect read-only PR bundles with `gh` and writes them into `agent-handoff`.
- `agent-doctor` exists as a compact diagnostics tool, with current docs noting a limitation that the imported script is still cwd/repo-local rather than fully system-wide.

## Merged, Open, or Documented in Component Repositories

- `lipi-codex/agent-drive-bridge` documents Google Drive via `rclone` as default transport, GitHub as source of truth, Gmail disabled, and ChatGPT GitHub connector as fallback-only in the typed-ingress worktree inspected for this task.
- `lipi-codex/agent-drive-bridge` PR #10 for typed ChatGPT ingress is merged; deployment is unknown according to this manifest.
- The inspected `agent-drive-bridge` worktree documents command handling for `create_task`, `comment_issue`, `comment_pr`, `review_pr`, `request_status`, `continue_task`, and `summarize_latest`.
- The inspected `agent-drive-bridge` worktree documents typed local ingress that serializes authenticated JSON requests into canonical Drive command documents.
- The inspected `agent-drive-bridge` worktree documents guarded `continue_task` behavior on the same issue and PR with head-SHA checks and `agent:ready` rearming.
- The inspected `agent-drive-bridge` worktree documents formal PR review commands with reviewer-token isolation and optional head-SHA validation.
- `lipnivan/agent-runner` PR #10 for sequential drain is merged, and PR #12 for duplicate Done/Review-needed push fixes is merged, but production checkout/systemd timer deployment on `.39` is not confirmed here.
- `lipnivan/agent-doctor` PR #6 is merged, but installed `/opt/agent-doctor` or live behavior update is not confirmed here.
- `agent-handoff` documents PR review bundles and review decisions as canonical review artifacts.

## Planned or Not Yet Fully Canonicalized Here

- Drive ingress is the intended primary ChatGPT mutation path once deployed and healthy everywhere. Until then, the ChatGPT GitHub connector remains fallback/rescue only.
- Doctor/PWA should visualize current task and ball ownership from source-of-truth state without becoming a mutation path.
- Component docs should continue moving implementation detail into their own repositories, with this repo serving as the cross-component canonical index.
- Recovery runbooks should be expanded as real outage repairs occur.

## Known Limitations

- This manifest was verified from local docs and current worktree content, not by mutating live services.
- The GitHub PR metadata listed in `verification.github_metadata_checked` was read with `gh`; other external URLs were not exhaustively network-validated.
- Local component paths may differ outside `.39`.
- Ball-owner state must use the canonical `agent-handoff-ball-owner/v1` enum in [ARCHITECTURE.md](ARCHITECTURE.md#canonical-ball-owner-contract). `agent:review` is an active review lifecycle state, not a runner pickup label. Runner pickup is only `agent:ready`; after `REQUEST_CHANGES`, continuation should reapply `agent:ready` on the same issue/branch/PR.
- The bridge and reviewer command capabilities must be rechecked against their current repository docs before relying on a specific command in production.

## Next Milestones

- Confirm Drive ingress deployment status in the canonical `lipi-codex/agent-drive-bridge` repository docs and installed service state.
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
