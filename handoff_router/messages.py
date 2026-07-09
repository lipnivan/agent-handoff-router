from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import RouterConfig
from . import simple_yaml

REQUIRED_FIELDS = {"schema", "type", "source", "target", "status", "created_at"}
ALLOWED_TYPES = {"task_request", "context", "report", "question", "artifact"}
ALLOWED_SOURCES = {"chatgpt", "drive", "codex", "sysadmin", "router", "user"}
ALLOWED_TARGETS = {"handoff-router", "chatgpt", "codex", "sysadmin", "agent-runner"}
ALLOWED_STATUS = {"new", "routed", "resolved", "failed"}


class MessageError(ValueError):
    pass


@dataclass
class MessageInspection:
    path: Path
    kind: str
    frontmatter: dict[str, Any] | None = None
    body: str = ""
    error: str | None = None


@dataclass
class Message:
    path: Path
    frontmatter: dict[str, Any]
    body: str

    @property
    def schema(self) -> str:
        return str(self.frontmatter["schema"])

    @property
    def message_type(self) -> str:
        return str(self.frontmatter["type"])

    @property
    def status(self) -> str:
        return str(self.frontmatter["status"])

    @property
    def source(self) -> str:
        return str(self.frontmatter["source"])

    @property
    def title(self) -> str | None:
        value = self.frontmatter.get("title")
        return str(value) if value else None

    def first_heading(self) -> str | None:
        for line in self.body.splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip() or None
        return None

    def effective_title(self) -> str:
        return self.title or self.first_heading() or self.path.stem

    def project(self) -> str:
        project = self.frontmatter.get("project")
        if project:
            return str(project)
        parts = self.path.parts
        if "projects" in parts:
            idx = parts.index("projects")
            if len(parts) > idx + 1:
                return parts[idx + 1]
        return "unknown"

    def to_summary(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "project": self.project(),
            "type": self.message_type,
            "status": self.status,
            "source": self.source,
            "target": self.frontmatter.get("target"),
            "title": self.effective_title(),
        }


def _parse_iso8601(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MessageError(f"invalid created_at: {value}") from exc


def _load_frontmatter(path: str | Path) -> tuple[dict[str, Any], str]:
    message_path = Path(path)
    text = message_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise MessageError("message must start with YAML frontmatter")
    try:
        _, fm_text, body = text.split("---\n", 2)
    except ValueError as exc:
        raise MessageError("message frontmatter is not terminated") from exc
    frontmatter = simple_yaml.loads(fm_text) or {}
    if not isinstance(frontmatter, dict):
        raise MessageError("frontmatter must be a mapping")
    return frontmatter, body.lstrip("\n")


def inspect_message(path: str | Path) -> MessageInspection:
    message_path = Path(path)
    text = message_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return MessageInspection(path=message_path, kind="ignored")
    try:
        frontmatter, body = _load_frontmatter(message_path)
    except MessageError as exc:
        return MessageInspection(path=message_path, kind="invalid", error=str(exc))
    schema = frontmatter.get("schema")
    if schema is None:
        return MessageInspection(path=message_path, kind="legacy", frontmatter=frontmatter, body=body)
    if schema != "agent-handoff-message/v1":
        return MessageInspection(path=message_path, kind="unsupported_schema", frontmatter=frontmatter, body=body)
    try:
        validate_frontmatter(frontmatter)
    except MessageError as exc:
        return MessageInspection(path=message_path, kind="invalid", frontmatter=frontmatter, body=body, error=str(exc))
    return MessageInspection(path=message_path, kind="valid", frontmatter=frontmatter, body=body)


def parse_message(path: str | Path) -> Message:
    inspection = inspect_message(path)
    if inspection.kind == "ignored":
        raise MessageError("message must start with YAML frontmatter")
    if inspection.kind in {"legacy", "unsupported_schema"}:
        raise MessageError("message does not declare supported schema")
    if inspection.kind != "valid" or inspection.frontmatter is None:
        raise MessageError(inspection.error or "invalid message")
    return Message(path=inspection.path, frontmatter=inspection.frontmatter, body=inspection.body)


def validate_frontmatter(frontmatter: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(frontmatter))
    if missing:
        raise MessageError(f"missing required fields: {', '.join(missing)}")
    if frontmatter["schema"] != "agent-handoff-message/v1":
        raise MessageError("unsupported schema")
    if frontmatter["type"] not in ALLOWED_TYPES:
        raise MessageError(f"unsupported type: {frontmatter['type']}")
    if frontmatter["source"] not in ALLOWED_SOURCES:
        raise MessageError(f"unsupported source: {frontmatter['source']}")
    if frontmatter["target"] not in ALLOWED_TARGETS:
        raise MessageError(f"unsupported target: {frontmatter['target']}")
    if frontmatter["status"] not in ALLOWED_STATUS:
        raise MessageError(f"unsupported status: {frontmatter['status']}")
    _parse_iso8601(str(frontmatter["created_at"]))


def discover_message_paths(config: RouterConfig) -> list[Path]:
    repo_dir = config.handoff_repo_dir
    candidates: set[Path] = set()
    for pattern in config.scan_roots:
        candidates.update(repo_dir.glob(pattern))
    return sorted(path for path in candidates if path.is_file() and path.suffix == ".md")


def discover_messages(config: RouterConfig) -> tuple[list[Message], list[dict[str, Any]], list[dict[str, Any]]]:
    messages: list[Message] = []
    errors: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    for path in discover_message_paths(config):
        inspection = inspect_message(path)
        if inspection.kind == "ignored":
            continue
        if inspection.kind == "valid" and inspection.frontmatter is not None:
            messages.append(Message(path=inspection.path, frontmatter=inspection.frontmatter, body=inspection.body))
            continue
        if inspection.kind in {"legacy", "unsupported_schema"}:
            legacy.append({"path": str(path), "kind": inspection.kind})
            continue
        errors.append({"path": str(path), "error": inspection.error or "invalid message"})
    return messages, errors, legacy
