from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass
class GitOps:
    git_binary: str = "git"
    dry_run: bool = False

    def _run(self, repo_path: Path, args: list[str]) -> str:
        if self.dry_run:
            return ""
        proc = subprocess.run(
            [self.git_binary, "-C", str(repo_path), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise GitError(proc.stderr.strip() or proc.stdout.strip() or "git command failed")
        return proc.stdout.strip()

    def pull(self, repo_path: Path) -> str:
        return self._run(repo_path, ["pull", "--ff-only"])

    def commit_paths(self, repo_path: Path, paths: list[Path], message: str) -> str:
        if self.dry_run:
            return ""
        rel_paths = [str(path.relative_to(repo_path)) for path in paths]
        self._run(repo_path, ["add", *rel_paths])
        return self._run(repo_path, ["commit", "-m", message])
