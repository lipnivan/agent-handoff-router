from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


class GitHubError(RuntimeError):
    pass


@dataclass
class GitHubClient:
    gh_binary: str = "gh"
    dry_run: bool = False

    def _run(self, args: list[str], stdin: str | None = None) -> str:
        if self.dry_run:
            return ""
        proc = subprocess.run(
            [self.gh_binary, *args],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise GitHubError(proc.stderr.strip() or proc.stdout.strip() or "gh command failed")
        return proc.stdout.strip()

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, str | int]:
        if self.dry_run:
            return {"number": 0, "url": f"https://github.com/{repo}/issues/dry-run"}
        args = ["issue", "create", "--repo", repo, "--title", title, "--body-file", "-"]
        for label in labels:
            args.extend(["--label", label])
        output = self._run(args, stdin=body)
        url = output.splitlines()[-1].strip()
        number = int(url.rstrip("/").split("/")[-1])
        return {"number": number, "url": url}

    def list_labels(self, repo: str) -> set[str]:
        if self.dry_run:
            return set()
        output = self._run(["label", "list", "--repo", repo, "--limit", "1000", "--json", "name"])
        payload = json.loads(output or "[]")
        return {str(entry["name"]) for entry in payload if "name" in entry}

    def create_label(
        self,
        repo: str,
        name: str,
        color: str = "D4C5F9",
        description: str = "Created by agent-handoff-router",
    ) -> dict[str, str]:
        if self.dry_run:
            return {"name": name}
        self._run(["label", "create", name, "--repo", repo, "--color", color, "--description", description])
        return {"name": name}

    def comment_issue(self, repo: str, issue_number: int, body: str) -> dict[str, str | int]:
        if self.dry_run:
            return {"issue_number": issue_number, "url": f"https://github.com/{repo}/issues/{issue_number}#dry-run"}
        output = self._run(["issue", "comment", str(issue_number), "--repo", repo, "--body-file", "-"], stdin=body)
        return {"issue_number": issue_number, "url": output.splitlines()[-1].strip() if output else ""}

    def search_issue_by_dedupe(self, repo: str, dedupe_key: str) -> list[dict[str, str | int]]:
        if self.dry_run:
            return []
        output = self._run(
            [
                "issue",
                "list",
                "--repo",
                repo,
                "--search",
                f'"dedupe_key: {dedupe_key}" in:body',
                "--state",
                "all",
                "--json",
                "number,title,url",
            ]
        )
        return json.loads(output or "[]")
