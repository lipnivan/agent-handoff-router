from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from handoff_router.config import RouterConfig
from handoff_router.messages import MessageError, discover_message_paths, parse_message


VALID_MESSAGE = """---
schema: agent-handoff-message/v1
type: task_request
source: chatgpt
target: handoff-router
status: new
created_at: 2026-07-09T00:00:00Z
project: demo
target_repo: lipnivan/demo
action: create_issue
---

# Demo title

Hello
"""


class MessageTests(unittest.TestCase):
    def test_parse_valid_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "message.md"
            path.write_text(VALID_MESSAGE, encoding="utf-8")
            message = parse_message(path)
            self.assertEqual(message.message_type, "task_request")
            self.assertEqual(message.effective_title(), "Demo title")

    def test_reject_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "message.md"
            path.write_text("---\nschema: agent-handoff-message/v1\n---\n", encoding="utf-8")
            with self.assertRaises(MessageError):
                parse_message(path)

    def test_scan_finds_open_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(VALID_MESSAGE, encoding="utf-8")
            config = RouterConfig(handoff_repo_path=str(repo), state_path=str(repo / "state.json"))
            results = discover_message_paths(config)
            self.assertEqual(results, [path])


if __name__ == "__main__":
    unittest.main()
