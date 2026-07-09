from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import simple_yaml


DEFAULT_CONFIG_PATH = Path("config/config.yaml")
EXAMPLE_CONFIG_PATH = Path("config/config.yaml.example")


@dataclass
class RouterConfig:
    handoff_repo_path: str = "/opt/agent-handoff"
    handoff_repo: str = "lipnivan/agent-handoff"
    state_path: str = "/var/lib/agent-handoff-router/state.json"
    default_ready_label: str = "agent:ready"
    dry_run: bool = False
    pull_before_scan: bool = True
    commit_after_route: bool = True
    scan_roots: list[str] = field(
        default_factory=lambda: [
            "projects/*/inbox/*/open/*.md",
            "projects/*/context/*.md",
        ]
    )

    @property
    def handoff_repo_dir(self) -> Path:
        return Path(self.handoff_repo_path)

    @property
    def state_file(self) -> Path:
        return Path(self.state_path)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path | None = None) -> RouterConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return RouterConfig()
    data = simple_yaml.loads(config_path.read_text(encoding="utf-8")) or {}
    return RouterConfig(**data)


def dump_example_config(destination: str | Path) -> Path:
    dest = Path(destination)
    payload = simple_yaml.dumps(RouterConfig().to_dict())
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(payload, encoding="utf-8")
    return dest
