# Operational Workflow

Last verified: 2026-07-15.

This workflow describes how work moves through the handoff stack. See [ARCHITECTURE.md](ARCHITECTURE.md) for component boundaries and [CURRENT-STATE.md](CURRENT-STATE.md) for repository, deployment, and planned status.

## Create a Task

1. Prefer a Google Drive command document processed by `agent-drive-bridge`.
2. Use the canonical command format for the active bridge version.
3. Target a GitHub repository and include the task body, labels, and enough context to execute without conversation memory.
4. Ensure the resulting GitHub issue has `agent:ready` if runner pickup is intended.
5. Treat GitHub issue creation as the durable task state. Drive and handoff artifacts are transport and audit records.

If Drive ingress is unavailable, use the documented fallback path only long enough to create or repair the canonical GitHub state. The ChatGPT GitHub connector is fallback/rescue, not primary mutation transport.

## Runner Claim and Execution

1. `agent-runner` scans configured repositories for issues labeled `agent:ready`.
2. Runner claims only `agent:ready`; do not use `agent:review` for pickup.
3. Runner works in an isolated worktree under its configured worktree root.
4. Runner invokes Codex with the generated prompt and safety rules.
5. Runner may push a branch and open or update a draft PR.
6. Runner must not merge, deploy, run `sudo`, handle secrets, or change production infrastructure.

## Draft PR and Review Bundle

1. Draft PR state lives in GitHub.
2. `agent-reviewer` or a collector on `.39` gathers a read-only PR bundle using `gh`.
3. The bundle must include repo, issue, PR number, base/head refs, head SHA, draft state, changed files, diff or bounded diff, and freshness status.
4. The bundle is written to `agent-handoff` for ChatGPT review intake.
5. ChatGPT reviews the bundle and writes a review decision anchored to the observed PR head SHA.

Review bundle details are canonical in `lipnivan/agent-handoff/docs/PR-REVIEW-BUNDLES.md`.

## REQUEST_CHANGES Continuation

1. ChatGPT writes a `request_changes` decision with concrete blocking findings and the reviewed head SHA.
2. The bridge or reviewer posts the continuation to the existing GitHub issue or PR.
3. Continuation must stay on the same issue, branch, and PR unless a human explicitly chooses otherwise.
4. Re-arm runner pickup by applying `agent:ready`.
5. Remove lifecycle labels that are no longer current only after `agent:ready` succeeds and current PR head checks still match.
6. Runner resumes on the same task and updates the same draft PR.

Head-SHA guards matter: if the PR head changed since review, collect a new bundle before treating a previous decision as actionable.

## APPROVE and Human Merge

1. ChatGPT writes an `approved` decision only for the reviewed head SHA.
2. Reviewer automation may mark ready for review, comment approval, assign owner, request owner review, or add labels if those actions are authorized.
3. ChatGPT, bridge, router, reviewer, and runner must not merge.
4. Human owner performs final review and merge decision in GitHub.
5. Deployment, if any, is a separate human-owned/admin-approved action.

## Admin-Action Escalation

Stop and report an escalation request when work requires:

- `sudo`;
- production deployment;
- secrets or token handling;
- firewall, systemd, router, or production service config changes;
- destructive filesystem or Git operations;
- merge or release authority;
- mutation outside the allowed component scope.

The escalation report should name the required action, why it is needed, the component affected, and the safe state where automation stopped.

## Recovery Paths

Drive unavailable:

- Do not pretend Drive succeeded. Record the outage.
- Use GitHub state to discover active issues and PRs.
- Use the ChatGPT GitHub connector only as temporary rescue/fallback for urgent mutation or bridge repair.
- Backfill canonical Drive or handoff artifacts after recovery when needed for audit continuity.

Bridge unavailable:

- Check bridge status and latest sanitized diagnostics.
- Avoid direct mutation unless it is required to unblock repair.
- Use connector fallback only for emergency issue/comment/review actions.
- Restore Drive/bridge as primary after repair.

Runner unavailable:

- Leave GitHub issue and PR state intact.
- Confirm whether `agent:ready` is present and whether a runner claim is stale.
- Do not create a competing branch or PR unless a human decides to abandon the existing runner attempt.
- Repair runner or requeue with `agent:ready` after the stale state is understood.

GitHub connector unavailable:

- No architectural problem if Drive/bridge and `.39` services are healthy.
- Continue through Drive/bridge primary transport.
- If both connector and primary path are unavailable, stop and request human/admin intervention.

GitHub unavailable:

- Do not treat Drive, bridge, router, or Doctor/PWA output as source of truth.
- Queue no-op or failed diagnostics only.
- Resume by reconciling against GitHub after availability returns.
