# Routing

## Discovery

MVP scans:
- `projects/*/inbox/*/open/*.md`
- `projects/*/context/*.md`

## Idempotency

State is stored in `state.json` and keyed by:
- message path
- optional `id`
- optional `dedupe_key`

If the message state already says routed, or the dedupe key already exists, the router skips duplicate execution.

## Task request

When `type=task_request`, `action=create_issue`, and `target_repo` is set:
- title comes from frontmatter `title`, first Markdown heading, or filename
- body is original body plus metadata footer
- labels come from frontmatter plus default ready label unless disabled
- the default ready label is treated as critical and must be applied or routing fails
- missing optional message labels are skipped with a warning unless config enables auto-create
- success writes state and a routed report

## Context

When `type=context`, `related_repo`, and `related_issue` are set:
- router posts a comment to the related issue
- success writes state and a routed report

## Report and question

- `report` is recorded as resolved
- `question` is intentionally skipped for non-router paths

## Failure handling

Malformed or unsupported messages remain in place. Router records failed status and error details in state.
