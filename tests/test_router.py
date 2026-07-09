from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from handoff_router.config import RouterConfig
from handoff_router.cli import cmd_scan, cmd_self_check, cmd_status
from handoff_router.router import PreflightCheck, Router


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

LEGACY_MESSAGE = """---
title: Legacy note
source: chatgpt
---

Old body
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

    def test_scan_marks_malformed_v1_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "bad.md"
            path.parent.mkdir(parents=True)
            path.write_text(MALFORMED_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)

            results = router.scan(pull=False)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "invalid")
            self.assertIn("missing required fields", results[0].details["error"])

    def test_scan_default_excludes_legacy_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "legacy.md"
            path.parent.mkdir(parents=True)
            path.write_text(LEGACY_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)

            results = router.scan(pull=False)

            self.assertEqual(results, [])

    def test_scan_include_legacy_shows_legacy_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "legacy.md"
            path.parent.mkdir(parents=True)
            path.write_text(LEGACY_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)

            results = router.scan(pull=False, include_legacy=True)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "legacy")
            self.assertEqual(results[0].action, "ignore")
            self.assertEqual(results[0].path, str(path))

    def test_scan_excludes_routed_message_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)
            router.save_state({"messages": {str(path): {"status": "routed"}}, "dedupe": {}})

            results = router.scan(pull=False)

            self.assertEqual(results, [])

    def test_scan_include_routed_shows_skipped_state_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)
            router.save_state({"messages": {str(path): {"status": "routed"}}, "dedupe": {}})

            results = router.scan(pull=False, include_routed=True)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "skipped")
            self.assertEqual(results[0].action, "state")
            self.assertEqual(results[0].details["matched_on"], "path")

    def test_dedupe_key_state_classifies_message_as_routed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, _, _ = self.make_router(repo)
            router.save_state({"messages": {}, "dedupe": {"task-1": {"status": "routed"}}})

            inventory = router.message_inventory()

            self.assertEqual(inventory["pending_messages"], 0)
            self.assertEqual(inventory["routed_messages"], 1)
            self.assertTrue(inventory["messages"][0]["routed"])
            self.assertEqual(inventory["messages"][0]["matched_on"], "dedupe_key")

    def test_cli_scan_default_excludes_legacy_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_path = repo / "config.yaml"
            legacy_path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "legacy.md"
            legacy_path.parent.mkdir(parents=True)
            legacy_path.write_text(LEGACY_MESSAGE, encoding="utf-8")
            config_path.write_text(
                "\n".join(
                    [
                        f"handoff_repo_path: {repo}",
                        f"state_path: {repo / 'state.json'}",
                        "pull_before_scan: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("sys.stdout.write") as write:
                exit_code = cmd_scan(
                    type(
                        "Args",
                        (),
                        {
                            "config": str(config_path),
                            "route": False,
                            "no_pull": True,
                            "include_legacy": False,
                            "include_routed": False,
                            "once": True,
                        },
                    )()
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(write.call_args_list, [])

    def test_status_counts_pending_vs_routed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_path = repo / "config.yaml"
            pending_path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "pending.md"
            routed_path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "routed.md"
            pending_path.parent.mkdir(parents=True)
            pending_path.write_text(TASK_MESSAGE.replace("title: Demo task", "title: Pending task"), encoding="utf-8")
            routed_path.write_text(TASK_MESSAGE.replace("title: Demo task", "title: Routed task"), encoding="utf-8")
            config_path.write_text(
                "\n".join(
                    [
                        f"handoff_repo_path: {repo}",
                        f"state_path: {repo / 'state.json'}",
                        "pull_before_scan: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "state.json").write_text(
                json.dumps({"messages": {str(routed_path): {"status": "routed"}}, "dedupe": {}}, indent=2) + "\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = cmd_status(type("Args", (), {"config": str(config_path)})())

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("messages: 2", output)
            self.assertIn("pending_messages: 1", output)
            self.assertIn("routed_messages: 1", output)

    def test_route_aborts_before_create_issue_when_state_parent_preflight_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, github, _ = self.make_router(repo)

            with patch.object(Router, "_check_state_parent", return_value=PreflightCheck("error", "permission denied")), patch.object(
                Router, "_check_command", return_value=PreflightCheck("ok")
            ):
                result = router.route_path(path)

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.action, "preflight")
            self.assertEqual(len(github.created), 0)
            self.assertEqual(list(repo.rglob("*.routed.md")), [])
            self.assertFalse(router.config.state_file.exists())

    def test_scan_route_aborts_before_writing_report_when_preflight_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "projects" / "demo" / "inbox" / "chatgpt" / "open" / "task.md"
            path.parent.mkdir(parents=True)
            path.write_text(TASK_MESSAGE, encoding="utf-8")
            router, github, _ = self.make_router(repo)

            with patch.object(Router, "_check_state_parent", return_value=PreflightCheck("error", "permission denied")), patch.object(
                Router, "_check_command", return_value=PreflightCheck("ok")
            ):
                results = router.scan(route=True, pull=False)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "failed")
            self.assertEqual(results[0].action, "preflight")
            self.assertEqual(len(github.created), 0)
            self.assertEqual(list(repo.rglob("*.routed.md")), [])

    def test_self_check_reports_state_parent_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_path = repo / "config.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        f"handoff_repo_path: {repo}",
                        f"state_path: {repo / 'state.json'}",
                        "pull_before_scan: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(Router, "_check_state_parent", return_value=PreflightCheck("error", "permission denied")), patch.object(
                Router, "_check_command", return_value=PreflightCheck("ok")
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = cmd_self_check(type("Args", (), {"config": str(config_path)})())

            self.assertEqual(exit_code, 1)
            self.assertIn("state_parent: error (permission denied)", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
