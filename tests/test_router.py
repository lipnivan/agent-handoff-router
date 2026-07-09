from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from handoff_router.config import RouterConfig
from handoff_router.router import Router


TASK_MESSAGE = """---
schema: agent-handoff-message/v1
type: task_request
source: chatgpt
target: handoff-router
status: new
created_at: 2026-07-09T00:00:00Z
project: demo
target_repo: lipnivan/demo
action: create_issue
labels:
  - bug
dedupe_key: task-1
title: Demo task
---

Body text
"""

CONTEXT_MESSAGE = """---
schema: agent-handoff-message/v1
type: context
source: sysadmin
target: handoff-router
status: new
created_at: 2026-07-09T00:00:00Z
project: demo
related_repo: lipnivan/demo
related_issue: 17
title: Context note
---

Extra context
"""

MALFORMED_MESSAGE = """---
schema: agent-handoff-message/v1
type: task_request
source: chatgpt
target: handoff-router
status: new
---

Bad
"""


class FakeGitHub:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str, list[str]]] = []
        self.commented: list[tuple[str, int, str]] = []

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, str | int]:
        self.created.append((repo, title, body, labels))
        return {"number": 11, "url": f"https://github.com/{repo}/issues/11"}

    def comment_issue(self, repo: str, issue_number: int, body: str) -> dict[str, str | int]:
        self.commented.append((repo, issue_number, body))
        return {"issue_number": issue_number, "url": f"https://github.com/{repo}/issues/{issue_number}#issuecomment-1"}


class FakeGitOps:
    def __init__(self) -> None:
        self.pulled = False
        self.commits: list[tuple[Path, list[Path], str]] = []

    def pull(self, repo_path: Path) -> str:
        self.pulled = True
        return ""

    def commit_paths(self, repo_path: Path, paths: list[Path], message: str) -> str:
        self.commits.append((repo_path, paths, message))
        return ""


class RouterTests(unittest.TestCase):
    def make_router(self, repo: Path) -> tuple[Router, FakeGitHub, FakeGitOps]:
        github = FakeGitHub()
        git = FakeGitOps()
        config = RouterConfig(
            handoff_repo_path=str(repo),
            state_path=str(repo / "var" / "state.json"),
            pull_before_scan=False,
            commit_after_route=False,
        )
        return Router(config, github_client=github, git_ops=git), github, git

    def test_task_request_creates_issue_and_records_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, github, _ = self.make_router(repo)

            result = router.route_path(path)

            self.assertEqual(result.status, "routed")
            self.assertEqual(len(github.created), 1)
            state = router.load_state()
            self.assertEqual(state["messages"][str(path)]["issue"]["number"], 11)
            self.assertIn("task-1", state["dedupe"])

    def test_context_comments_related_issue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "context" / "context.md"
            path.parent.mkdir(parents=True)
            path.write_text(CONTEXT_MESSAGE, encoding="utf-8")
            router, github, _ = self.make_router(repo)

            result = router.route_path(path)

            self.assertEqual(result.status, "routed")
            self.assertEqual(github.commented[0][1], 17)

    def test_already_routed_dedupe_skips_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, github, _ = self.make_router(repo)
            state = {"messages": {}, "dedupe": {"task-1": {"status": "routed"}}}
            router.save_state(state)

            result = router.route_path(path)

            self.assertEqual(result.status, "skipped")
            self.assertEqual(len(github.created), 0)

    def test_malformed_message_records_failed_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "bad.md"
            path.parent.mkdir(parents=True)
            path.write_text(MALFORMED_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)

            result = router.route_path(path)

            self.assertEqual(result.status, "failed")
            state = router.load_state()
            self.assertEqual(state["messages"][str(path)]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
