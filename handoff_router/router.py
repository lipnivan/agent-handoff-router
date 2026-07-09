from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RouterConfig
from .git_ops import GitError, GitOps
from .github import GitHubClient
from .messages import Message, MessageError, discover_messages, parse_message
from .utils import now_utc_iso, read_json_file, sanitize_filename, write_json_file


@dataclass
class RouteResult:
    status: str
    action: str
    path: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action": self.action,
            "path": self.path,
            "details": self.details,
        }


class Router:
    def __init__(
        self,
        config: RouterConfig,
        github_client: GitHubClient | None = None,
        git_ops: GitOps | None = None,
    ) -> None:
        self.config = config
        self.github = github_client or GitHubClient(dry_run=config.dry_run)
        self.git = git_ops or GitOps(dry_run=config.dry_run)

    def load_state(self) -> dict[str, Any]:
        return read_json_file(self.config.state_file, {"messages": {}, "dedupe": {}})

    def save_state(self, state: dict[str, Any]) -> None:
        write_json_file(self.config.state_file, state)

    def candidate_messages(self) -> tuple[list[Message], list[dict[str, Any]]]:
        return discover_messages(self.config)

    def scan(self, route: bool = False, pull: bool | None = None) -> list[RouteResult]:
        results: list[RouteResult] = []
        if pull is None:
            pull = self.config.pull_before_scan
        if pull and self.config.handoff_repo_dir.exists():
            try:
                self.git.pull(self.config.handoff_repo_dir)
            except GitError as exc:
                results.append(
                    RouteResult(
                        status="warning",
                        action="pull",
                        path=str(self.config.handoff_repo_dir),
                        details={"error": str(exc)},
                    )
                )
        messages, errors = self.candidate_messages()
        results.extend(
            [
            RouteResult(status="invalid", action="parse", path=entry["path"], details={"error": entry["error"]})
            for entry in errors
            ]
        )
        for message in messages:
            if route:
                results.append(self.route_message(message))
            else:
                results.append(
                    RouteResult(
                        status="candidate",
                        action="scan",
                        path=str(message.path),
                        details=message.to_summary(),
                    )
                )
        return results

    def route_path(self, path: str | Path) -> RouteResult:
        try:
            return self.route_message(parse_message(path))
        except MessageError as exc:
            state = self.load_state()
            key = str(Path(path))
            state["messages"][key] = {"status": "failed", "error": str(exc), "updated_at": now_utc_iso()}
            self.save_state(state)
            return RouteResult(status="failed", action="validate", path=key, details={"error": str(exc)})

    def route_message(self, message: Message) -> RouteResult:
        state = self.load_state()
        message_key = str(message.path)
        if message.status in {"routed", "resolved"}:
            return RouteResult(status="skipped", action="status", path=message_key, details={"reason": message.status})
        if state["messages"].get(message_key, {}).get("status") == "routed":
            return RouteResult(status="skipped", action="state", path=message_key, details={"reason": "already routed"})
        dedupe_key = message.frontmatter.get("dedupe_key")
        if dedupe_key and dedupe_key in state["dedupe"]:
            return RouteResult(
                status="skipped",
                action="dedupe",
                path=message_key,
                details={"reason": "dedupe_key already routed", "dedupe_key": dedupe_key},
            )

        if message.message_type == "task_request":
            return self._route_task_request(message, state)
        if message.message_type == "context":
            return self._route_context(message, state)
        if message.message_type == "report":
            return self._record_terminal(message, state, "resolved", "report")
        if message.message_type == "question":
            return RouteResult(status="skipped", action="question", path=message_key, details={"reason": "left for chatgpt/user"})
        return self._record_terminal(message, state, "failed", "unsupported", error="unsupported message type for MVP")

    def _route_task_request(self, message: Message, state: dict[str, Any]) -> RouteResult:
        repo = message.frontmatter.get("target_repo")
        action = message.frontmatter.get("action")
        if not repo or action != "create_issue":
            return self._record_terminal(message, state, "failed", "task_request", error="task_request requires action=create_issue and target_repo")

        labels = [str(label) for label in message.frontmatter.get("labels", [])]
        if not message.frontmatter.get("disable_default_ready_label", False):
            labels = labels + [self.config.default_ready_label]
        labels = sorted(dict.fromkeys(labels))

        title = message.effective_title()
        body = self._build_issue_body(message)
        issue = self.github.create_issue(str(repo), title, body, labels)
        record = {
            "status": "routed",
            "type": "task_request",
            "issue": issue,
            "repo": repo,
            "updated_at": now_utc_iso(),
        }
        self._record_state(state, message, record)
        report_path = self._write_routed_report(message, issue=issue)
        self.save_state(state)
        self._commit_outputs_if_needed([self.config.state_file, report_path])
        return RouteResult(status="routed", action="create_issue", path=str(message.path), details={"issue": issue, "report_path": str(report_path)})

    def _route_context(self, message: Message, state: dict[str, Any]) -> RouteResult:
        repo = message.frontmatter.get("related_repo")
        issue_number = message.frontmatter.get("related_issue")
        if not repo or not issue_number:
            return self._record_terminal(message, state, "failed", "context", error="context requires related_repo and related_issue")
        body = self._build_context_comment(message)
        comment = self.github.comment_issue(str(repo), int(issue_number), body)
        record = {
            "status": "routed",
            "type": "context",
            "comment": comment,
            "repo": repo,
            "issue_number": int(issue_number),
            "updated_at": now_utc_iso(),
        }
        self._record_state(state, message, record)
        report_path = self._write_routed_report(message, comment=comment)
        self.save_state(state)
        self._commit_outputs_if_needed([self.config.state_file, report_path])
        return RouteResult(status="routed", action="comment_issue", path=str(message.path), details={"comment": comment, "report_path": str(report_path)})

    def _record_terminal(
        self,
        message: Message,
        state: dict[str, Any],
        status: str,
        action: str,
        error: str | None = None,
    ) -> RouteResult:
        details = {"updated_at": now_utc_iso()}
        if error:
            details["error"] = error
        state["messages"][str(message.path)] = {"status": status, "action": action, **details}
        self.save_state(state)
        return RouteResult(status=status, action=action, path=str(message.path), details=details)

    def _record_state(self, state: dict[str, Any], message: Message, record: dict[str, Any]) -> None:
        message_key = str(message.path)
        state["messages"][message_key] = record
        message_id = message.frontmatter.get("id")
        if message_id:
            state["messages"][f"id:{message_id}"] = record
        dedupe_key = message.frontmatter.get("dedupe_key")
        if dedupe_key:
            state["dedupe"][str(dedupe_key)] = record

    def _build_issue_body(self, message: Message) -> str:
        metadata = {
            "message_path": str(message.path),
            "project": message.project(),
            "source": message.source,
            "type": message.message_type,
            "created_at": message.frontmatter["created_at"],
            "dedupe_key": message.frontmatter.get("dedupe_key", ""),
        }
        meta_lines = "\n".join(f"- {key}: {value}" for key, value in metadata.items() if value)
        return f"{message.body.rstrip()}\n\n---\nHandoff metadata:\n{meta_lines}\n"

    def _build_context_comment(self, message: Message) -> str:
        return f"{message.body.rstrip()}\n\n---\nSource message: `{message.path}`\n"

    def _write_routed_report(self, message: Message, issue: dict[str, Any] | None = None, comment: dict[str, Any] | None = None) -> Path:
        source_dir = message.source if message.source in {"chatgpt", "codex"} else "codex"
        report_dir = self.config.handoff_repo_dir / "projects" / message.project() / "inbox" / source_dir / "resolved"
        filename = sanitize_filename(message.effective_title()) + ".routed.md"
        report_path = report_dir / filename
        action = "commented" if comment else "created_issue"
        payload = [
            "---",
            "schema: agent-handoff-message/v1",
            "type: report",
            "source: router",
            f"target: {message.frontmatter.get('source', 'chatgpt')}",
            "status: resolved",
            f"created_at: {now_utc_iso()}",
            f"project: {message.project()}",
            f"title: Routed {message.effective_title()}",
            "---",
            "",
            f"Original message: `{message.path}`",
            f"Action: `{action}`",
        ]
        if issue:
            payload.append(f"Issue: {issue.get('url')}")
        if comment:
            payload.append(f"Comment target: issue #{comment.get('issue_number')}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(payload) + "\n", encoding="utf-8")
        return report_path

    def _commit_outputs_if_needed(self, paths: list[Path]) -> None:
        if not self.config.commit_after_route:
            return
        repo_dir = self.config.handoff_repo_dir
        if not repo_dir.exists():
            return
        repo_paths = [path for path in paths if repo_dir in path.parents or path == repo_dir]
        if repo_paths:
            self.git.commit_paths(repo_dir, repo_paths, "router: record routed message")
