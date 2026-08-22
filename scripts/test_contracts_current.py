#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import test_contracts


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, fragment: str, label: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if fragment not in content:
        raise SystemExit(f"{label} missing {fragment!r}")


def reject(path: str, fragment: str, label: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if fragment in content:
        raise SystemExit(f"{label} contains forbidden {fragment!r}")


def main() -> None:
    test_contracts.EXPECTED_GITHUB_WORKFLOWS.update(
        {
            "trusted-release-proof.yml",
            "release-promotion.yml",
            "release-verification.yml",
            "reusable-release-promote.yml",
            "reusable-release-verification.yml",
            "reusable-branch-cleanup.yml",
        }
    )
    test_contracts.DEFAULT_CALLERS.update(
        {"release-promotion.yml", "release-verification.yml", "branch-cleanup.yml"}
    )
    test_contracts.EXPECTED_SELF_ADAPTERS.add("release-proof.sh")
    test_contracts.main()

    require(
        "templates/caller/trusted-release-proof.yml",
        'node_version: "24"',
        "generated proof payload runtime",
    )
    reject(
        "templates/caller/trusted-release-proof.yml",
        "reusable-release-promote.yml@",
        "generated proof completion boundary",
    )
    require(
        "templates/caller/release-promotion.yml",
        'workflows: ["Trusted Release Proof"]',
        "generated proof-completion promotion",
    )
    require(
        "templates/caller/release-promotion.yml",
        "workflow_run.conclusion == 'success'",
        "generated successful-proof promotion",
    )
    require(
        "templates/caller/release-promotion.yml",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "generated release promotion",
    )
    require(
        ".github/workflows/trusted-release-proof.yml",
        "uses: ./.github/workflows/reusable-release-proof.yml",
        "control-plane trusted proof",
    )
    reject(
        ".github/workflows/trusted-release-proof.yml",
        "uses: ./.github/workflows/reusable-release-promote.yml",
        "control-plane proof completion boundary",
    )
    require(
        ".github/workflows/release-promotion.yml",
        'workflows: ["Trusted Release Proof"]',
        "control-plane proof-completion promotion",
    )
    require(
        ".github/workflows/release-promotion.yml",
        "uses: ./.github/workflows/reusable-release-promote.yml",
        "control-plane release promotion",
    )
    require(
        ".github/workflows/release.yml",
        "reuse_proof_payload: true",
        "control-plane release payload reuse",
    )
    require(
        ".github/workflows/release-verification.yml",
        "uses: ./.github/workflows/reusable-release-verification.yml",
        "control-plane release verification",
    )

    cleanup = ".github/workflows/reusable-branch-cleanup.yml"
    for fragment in (
        "workflow_call:",
        "branches_json:",
        "expected_default_sha:",
        "dry_run:",
        'default: \'"ubuntu-latest"\'',
        "Branch Cleanup Required",
        "group: branch-cleanup-${{ github.repository }}",
        "cancel-in-progress: false",
        "def read_ref_path(branch: str)",
        "def delete_ref_path(branch: str)",
        "def has_open_pr(branch: str)",
        "default branch is never deletable",
        "branch is the head of an open pull request",
        "branch is protected by repository policy",
        "cleanup preflight rejected targets",
        "default branch moved after cleanup preflight",
        "branch became the head of an open pull request during cleanup",
        'call("DELETE", delete_ref_path(branch))',
        'call("GET", read_ref_path(branch), allow_404=True)',
        "branch deletion did not verify absent",
        "cleanup-evidence.json",
    ):
        require(cleanup, fragment, "reusable branch cleanup")

    caller = "templates/caller/branch-cleanup.yml"
    for fragment in (
        "workflow_dispatch:",
        "contents: write",
        "pull-requests: read",
        "reusable-branch-cleanup.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "expected_default_sha: ${{ github.sha }}",
        'runner_json: \'"ubuntu-latest"\'',
        "dry_run: ${{ inputs.dry_run }}",
    ):
        require(caller, fragment, "generated branch cleanup caller")
    reject(caller, "issue_comment:", "generated branch cleanup caller authorization")
    require(
        "scripts/audit_org.py",
        'workflow_events(text) != {"workflow_dispatch"}',
        "branch cleanup trigger audit",
    )


if __name__ == "__main__":
    main()
