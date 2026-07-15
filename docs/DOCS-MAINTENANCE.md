# Documentation Maintenance Contract

Last verified: 2026-07-15.

These docs are canonical only if they are maintained when architecture, transport, lifecycle, or safety rules change.

## Update Triggers

Update [INDEX.md](INDEX.md), [ARCHITECTURE.md](ARCHITECTURE.md), [CHATGPT-HANDOFF-BOOTSTRAP.md](CHATGPT-HANDOFF-BOOTSTRAP.md), and [CURRENT-STATE.md](CURRENT-STATE.md) when any of these change:

- primary command/mutation transport;
- fallback connector policy;
- source-of-truth boundaries;
- runner pickup labels, lifecycle labels, or canonical ball-owner enum states;
- branch, PR, review, or merge ownership;
- bridge command schema or dispatch behavior;
- PR bundle schema or review decision schema;
- Doctor/PWA status or mutation capabilities;
- credential, token, or service-account boundaries;
- no-merge, no-deploy, no-sudo, secret-handling, or admin escalation rules;
- deployed vs merged vs planned state for any core component.

Update [OPERATIONAL-WORKFLOW.md](OPERATIONAL-WORKFLOW.md) when task creation, runner continuation, review, approval, or recovery procedures change.

Update router-specific docs such as [CONTRACT.md](CONTRACT.md), [ROUTING.md](ROUTING.md), and [MESSAGE-TYPES.md](MESSAGE-TYPES.md) when router behavior changes.

## Ownership

- Cross-component bootstrap and current-state docs: architecture owner or human operator responsible for the handoff stack.
- `agent-handoff` docs: central message bus/bootstrap owner.
- `agent-handoff-router` docs: router component owner.
- `agent-drive-bridge` docs: bridge component owner.
- `agent-runner` docs: runner component owner.
- `agent-reviewer` docs: reviewer component owner.
- `agent-doctor` and PWA docs: diagnostics/status surface owner.

The component owner updates local component detail first. The cross-component docs should then link that detail and summarize only the architectural contract.

## Stale-Document Warning

Every canonical handoff doc must include a `Last verified` date or a versioned manifest date. Treat docs as stale when:

- `Last verified` predates a known architecture or deployment change;
- current GitHub issue/PR state contradicts the doc;
- a component README contradicts this index;
- Drive/bridge, runner, reviewer, or Doctor behavior has changed without a corresponding doc update.

When stale docs are found, stop relying on the stale claim, discover live state from GitHub and component docs, then update the canonical docs as part of the repair.

## Link and Terminology Checks

Before finishing a docs maintenance change:

- verify local Markdown links resolve;
- verify component repository/path references are current;
- verify `agent:ready` is the runner pickup label;
- verify ball-owner terms reference the canonical `agent-handoff-ball-owner/v1` enum instead of defining a second vocabulary;
- verify primary/fallback wording still says Drive/bridge is primary and the ChatGPT GitHub connector is fallback/rescue only;
- verify bootstrap text contains no secrets, tokens, or machine-specific credentials;
- verify no doc grants ChatGPT, runner, bridge, router, reviewer, Doctor, or PWA permission to merge, deploy, run `sudo`, or handle secrets.
