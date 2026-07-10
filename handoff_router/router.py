from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RouterConfig
from .git_ops import GitError, GitOps
from .github import GitHubClient, GitHubError
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


@dataclass
class MessageState:
    routed: bool
    action: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = {"routed": self.routed}
        if self.routed:
            payload["state_action"] = self.action
            payload.update(self.details)
        return payload


@dataclass
class PreflightCheck:
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        payload = {"status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class PreflightReport:
    state_parent: PreflightCheck
    state_file: PreflightCheck
    handoff_repo: PreflightCheck
    handoff_repo_writable: PreflightCheck
    gh: PreflightCheck
    git: PreflightCheck

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {
            "state_parent": self.state_parent.to_dict(),
            "state_file": self.state_file.to_dict(),
            "handoff_repo": self.handoff_repo.to_dict(),
            "handoff_repo_writable": self.handoff_repo_writable.to_dict(),
            "gh": self.gh.to_dict(),
            "git": self.git.to_dict(),
        }

    def routing_ok(self) -> bool:
        required = [
            self.state_parent.status == "ok",
            self.state_file.status in {"ok", "missing"},
            self.handoff_repo.status == "ok",
            self.handoff_repo_writable.status == "ok",
            self.gh.status == "ok",
            self.git.status == "ok",
        ]
        return all(required)

    def summary(self) -> str:
        failures: list[str] = []
        for name, check in self.to_dict().items():
            status = check["status"]
            if status not in {"ok", "missing"}:
                detail = check.get("detail", "")
                failures.append(f"{name}={status}{': ' + detail if detail else ''}")
        return "; ".join(failures) if failures else "ok"


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

    def candidate_messages(self) -> tuple[list[Message], list[dict[str, Any]], list[dict[str, Any]]]:
        return discover_messages(self.config)

    def message_inventory(self) -> dict[str, Any]:
        messages, errors, legacy = self.candidate_messages()
        state = self.load_state()
        summaries: list[dict[str, Any]] = []
        pending_messages = 0
        routed_messages = 0
        for message in messages:
            classification = self.classify_message(message, state)
            summaries.append({**message.to_summary(), **classification.to_dict()})
            if classification.routed:
                routed_messages += 1
            else:
                pending_messages += 1
        return {
            "messages": summaries,
            "pending_messages": pending_messages,
            "routed_messages": routed_messages,
            "legacy_ignored": len(legacy),
            "parse_errors": len(errors),
            "errors": errors,
            "legacy": legacy,
        }

    def preflight_report(self) -> PreflightReport:
        state_parent = self._check_state_parent()
        state_file = self._check_state_file(state_parent)
        handoff_repo = self._check_handoff_repo()
        handoff_repo_writable = self._check_handoff_repo_writable(handoff_repo)
        gh = self._check_command("gh")
        git = self._check_command("git")
        return PreflightReport(
            state_parent=state_parent,
            state_file=state_file,
            handoff_repo=handoff_repo,
            handoff_repo_writable=handoff_repo_writable,
            gh=gh,
            git=git,
        )

    def scan(
        self,
        route: bool = False,
        pull: bool | None = None,
        include_legacy: bool = False,
        include_routed: bool = False,
    ) -> list[RouteResult]:
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
        if route:
            preflight = self.preflight_report()
            if not preflight.routing_ok():
                return [self._preflight_failure_result(preflight, action="scan")]
        messages, errors, legacy = self.candidate_messages()
        state = self.load_state()
        results.extend(
            [
                RouteResult(status="invalid", action="parse", path=entry["path"], details={"error": entry["error"]})
                for entry in errors
            ]
        )
        if include_legacy:
            results.extend(
                [
                    RouteResult(status="legacy", action="ignore", path=entry["path"], details={"kind": entry["kind"]})
                    for entry in legacy
                ]
            )
        for message in messages:
            if route:
                results.append(self.route_message(message, skip_preflight=True))
                continue
            classification = self.classify_message(message, state)
            if classification.routed:
                if include_routed:
                    results.append(
                        RouteResult(
                            status="skipped",
                            action=classification.action,
                            path=str(message.path),
                            details={**message.to_summary(), **classification.to_dict()},
                        )
                    )
                continue
            results.append(
                RouteResult(
                    status="candidate",
                    action="scan",
                    path=str(message.path),
                    details={**message.to_summary(), **classification.to_dict()},
                )
            )
        return results

    def route_path(self, path: str | Path, *, skip_preflight: bool = False) -> RouteResult:
        if not skip_preflight:
            preflight = self.preflight_report()
            if not preflight.routing_ok():
                return self._preflight_failure_result(preflight, action="route", path=str(Path(path)))
        try:
            return self.route_message(parse_message(path), skip_preflight=True)
        except MessageError as exc:
            state = self.load_state()
            key = str(Path(path))
            state["messages"][key] = {"status": "failed", "error": str(exc), "updated_at": now_utc_iso()}
            self.save_state(state)
            return RouteResult(status="failed", action="validate", path=key, details={"error": str(exc)})

    def route_message(self, message: Message, *, skip_preflight: bool = False) -> RouteResult:
        if not skip_preflight:
            preflight = self.preflight_report()
            if not preflight.routing_ok():
                return self._preflight_failure_result(preflight, action="route", path=str(message.path))
        state = self.load_state()
        message_key = str(message.path)
        classification = self.classify_message(message, state)
        if classification.routed:
            return RouteResult(status="skipped", action=classification.action, path=message_key, details=classification.details)

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

        optional_labels = [str(label) for label in message.frontmatter.get("labels", [])]
        critical_labels: list[str] = []
        if not message.frontmatter.get("disable_default_ready_label", False):
            critical_labels.append(self.config.default_ready_label)

        try:
            labels, label_warnings = self._prepare_issue_labels(
                str(repo),
                optional_labels=optional_labels,
                critical_labels=critical_labels,
            )
        except GitHubError as exc:
            return self._record_terminal(message, state, "failed", "create_issue", error=str(exc))

        title = message.effective_title()
        body = self._build_issue_body(message)
        issue = self.github.create_issue(str(repo), title, body, labels)
        record = {
            "status": "routed",
            "type": "task_request",
            "issue": issue,
            "repo": repo,
            "labels": labels,
            "updated_at": now_utc_iso(),
        }
        if label_warnings:
            record["warnings"] = label_warnings
        self._record_state(state, message, record)
        report_path = self._write_routed_report(message, issue=issue)
        self.save_state(state)
        self._commit_outputs_if_needed([self.config.state_file, report_path])
        details: dict[str, Any] = {
            "issue": issue,
            "labels": labels,
            "report_path": str(report_path),
        }
        if label_warnings:
            details["warnings"] = label_warnings
        return RouteResult(status="routed", action="create_issue", path=str(message.path), details=details)

    def _prepare_issue_labels(
        self,
        repo: str,
        *,
        optional_labels: list[str],
        critical_labels: list[str],
    ) -> tuple[list[str], list[str]]:
        labels = sorted(dict.fromkeys([*optional_labels, *critical_labels]))
        if self.config.dry_run or not labels:
            return labels, []

        existing_labels = self.github.list_labels(repo)
        applied: list[str] = []
        warnings: list[str] = []
        missing_optional: list[str] = []

        for label in sorted(dict.fromkeys(optional_labels)):
            if label in existing_labels:
                applied.append(label)
            else:
                missing_optional.append(label)

        for label in sorted(dict.fromkeys(critical_labels)):
            if label in existing_labels:
                applied.append(label)
                continue
            if self.config.auto_create_missing_labels:
                self.github.create_label(repo, label)
                existing_labels.add(label)
                applied.append(label)
                continue
            raise GitHubError(f"critical label missing in {repo}: {label}")

        if missing_optional:
            if self.config.auto_create_missing_labels:
                for label in missing_optional:
                    if label in existing_labels:
                        applied.append(label)
                        continue
                    self.github.create_label(repo, label)
                    existing_labels.add(label)
                    applied.append(label)
            else:
                skipped = ", ".join(missing_optional)
                warnings.append(f"skipped missing optional labels in {repo}: {skipped}")

        return sorted(dict.fromkeys(applied)), warnings

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

    def classify_message(self, message: Message, state: dict[str, Any] | None = None) -> MessageState:
        active_state = state if state is not None else self.load_state()
        if message.status in {"routed", "resolved"}:
            return MessageState(True, "status", {"reason": message.status, "matched_on": "status"})

        message_key = str(message.path)
        if self._record_is_routed(active_state["messages"].get(message_key)):
            return MessageState(True, "state", {"reason": "already routed", "matched_on": "path"})

        message_id = message.frontmatter.get("id")
        if message_id and self._record_is_routed(active_state["messages"].get(f"id:{message_id}")):
            return MessageState(True, "state", {"reason": "already routed", "matched_on": "id", "id": str(message_id)})

        dedupe_key = message.frontmatter.get("dedupe_key")
        if dedupe_key and self._record_is_routed(active_state["dedupe"].get(str(dedupe_key))):
            return MessageState(
                True,
                "dedupe",
                {"reason": "dedupe_key already routed", "matched_on": "dedupe_key", "dedupe_key": str(dedupe_key)},
            )

        return MessageState(False, "pending", {})

    def _record_is_routed(self, record: Any) -> bool:
        return isinstance(record, dict) and record.get("status") == "routed"

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

    def _preflight_failure_result(
        self,
        report: PreflightReport,
        action: str,
        path: str | None = None,
    ) -> RouteResult:
        return RouteResult(
            status="failed",
            action="preflight",
            path=path or str(self.config.state_file),
            details={"error": f"preflight failed: {report.summary()}", "checks": report.to_dict(), "command": action},
        )

    def _check_command(self, binary: str) -> PreflightCheck:
        return PreflightCheck("ok") if shutil.which(binary) else PreflightCheck("error", f"{binary} not found")

    def _check_state_parent(self) -> PreflightCheck:
        parent = self.config.state_file.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return PreflightCheck("error", str(exc))
        return self._probe_directory_writable(parent)

    def _check_state_file(self, state_parent: PreflightCheck) -> PreflightCheck:
        state_file = self.config.state_file
        if state_parent.status != "ok":
            return PreflightCheck("error", "state parent not writable")
        if not state_file.exists():
            return PreflightCheck("missing")
        try:
            with state_file.open("r+", encoding="utf-8") as handle:
                payload = handle.read()
        except OSError as exc:
            return PreflightCheck("error", str(exc))
        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:
            return PreflightCheck("invalid_json", str(exc))
        return PreflightCheck("ok")

    def _check_handoff_repo(self) -> PreflightCheck:
        repo_dir = self.config.handoff_repo_dir
        if not repo_dir.exists():
            return PreflightCheck("error", "path does not exist")
        if not repo_dir.is_dir():
            return PreflightCheck("error", "path is not a directory")
        return PreflightCheck("ok")

    def _check_handoff_repo_writable(self, handoff_repo: PreflightCheck) -> PreflightCheck:
        if handoff_repo.status != "ok":
            return PreflightCheck("error", "handoff repo unavailable")
        return self._probe_directory_writable(self.config.handoff_repo_dir)

    def _probe_directory_writable(self, directory: Path) -> PreflightCheck:
        probe_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".router-write-check-", delete=False) as handle:
                probe_path = handle.name
            Path(probe_path).unlink()
        except OSError as exc:
            if probe_path:
                try:
                    Path(probe_path).unlink(missing_ok=True)
                except OSError:
                    pass
            return PreflightCheck("error", str(exc))
        return PreflightCheck("ok")
