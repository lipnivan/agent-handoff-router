---
schema: agent-handoff-message/v1
type: task_request
source: chatgpt
target: handoff-router
status: new
created_at: 2026-07-09T00:00:00Z
project: sample-project
target_repo: lipnivan/sample-project
action: create_issue
labels:
  - bug
priority: high
dedupe_key: sample-project-task-001
title: Fix failing sync job
---

# Fix failing sync job

The nightly sync started returning partial results after the last deployment. Investigate logs in the target repo and restore the expected success path.
