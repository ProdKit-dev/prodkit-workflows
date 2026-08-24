#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, fragment: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if fragment not in text:
        raise SystemExit(f"{path} missing {fragment!r}")


def reject(path: str, fragment: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if fragment in text:
        raise SystemExit(f"{path} contains forbidden {fragment!r}")


def main() -> None:
    reusable = ".github/workflows/reusable-release-verification.yml"
    for fragment in (
        "automatic_cleanup:",
        "cleanup_workflow_file:",
        "cleanup_branch_prefixes_json:",
        "actions: write",
        "pull-requests: read",
        "Dispatch verified release branch cleanup",
        'default: \'["release/","hotfix/"]\'',
        'f"/commits/{urllib.parse.quote(source_sha, safe=\'\')}/pulls?per_page=100"',
        'pr.get("merge_commit_sha") == source_sha',
        'head_repo.get("full_name") == repo',
        'any(branch.startswith(prefix) for prefix in prefixes)',
        'comparison.get("status") != "ahead"',
        'merge_base != source_sha',
        'current_branch_sha != expected_head_sha',
        '"branches_json": json.dumps([branch], separators=(",", ":"))',
        '"dry_run": False',
        '"expected_default_sha": current_main',
        "/actions/workflows/",
        "/dispatches",
        "already absent; cleanup is complete",
    ):
        require(reusable, fragment)
    reject(reusable, 'method="DELETE"')
    reject(reusable, 'call("DELETE"')

    for caller in (
        ".github/workflows/release-verification.yml",
        "templates/caller/release-verification.yml",
    ):
        for fragment in (
            "actions: write",
            "pull-requests: read",
            "automatic_cleanup: true",
            "cleanup_workflow_file: branch-cleanup.yml",
            "main_branch: main",
            "cleanup_branch_prefixes_json: '[\"release/\",\"hotfix/\"]'",
        ):
            require(caller, fragment)


if __name__ == "__main__":
    main()
