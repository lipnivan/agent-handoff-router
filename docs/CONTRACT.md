# Contract

Messages are Markdown files with YAML frontmatter followed by a Markdown body.

Required fields:
- `schema: agent-handoff-message/v1`
- `type: task_request | context | report | question | artifact`
- `source: chatgpt | drive | codex | sysadmin | router | user`
- `target: handoff-router | chatgpt | codex | sysadmin | agent-runner`
- `status: new | routed | resolved | failed`
- `created_at: ISO8601`

Optional fields:
- `id`
- `project`
- `target_repo`
- `action`
- `labels`
- `priority`
- `related_repo`
- `related_issue`
- `related_pr`
- `attachments`
- `dedupe_key`
- `title`
- `disable_default_ready_label`

The body is the human-readable task, context, report, or question content. Router-generated issue/comment bodies include source metadata so the target repo has a trace back to the message bus.
