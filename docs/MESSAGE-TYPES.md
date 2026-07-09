# Message Types

## `task_request`

Executable request for the router. In MVP, only `action=create_issue` is supported.

## `context`

Additional background to append to an existing target repo issue via comment.

## `report`

Completion or status report. The router records it as resolved and does not create a new task.

## `question`

A question intended for ChatGPT or a user workflow. The router does not convert it into a target repo task in MVP.

## `artifact`

Reserved for future structured attachments or references. MVP treats it as unsupported for execution routing.
