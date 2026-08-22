#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import audit_org
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


def test_cleanup_trigger_parser() -> None:
    canonical = """name: Branch Cleanup
on:
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
permissions:
  contents: read
"""
    if audit_org.workflow_events(canonical) != {"workflow_dispatch"}:
        raise SystemExit("cleanup trigger parser rejected canonical workflow_dispatch-only caller")

    malicious = (
        '  "pull_request_target":\n',
        "  'schedule':\n",
        "  repository_dispatch:\n",
        "  workflow_run:\n",
    )
    for extra in malicious:
        text = canonical.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n" + extra)
        if audit_org.workflow_events(text) == {"workflow_dispatch"}:
            raise SystemExit(f"cleanup trigger parser ignored additional event: {extra.strip()}")

    ambiguous = """name: Branch Cleanup
on: [workflow_dispatch, push]
permissions:
  contents: write
"""
    if audit_org.workflow_events(ambiguous) == {"workflow_dispatch"}:
        raise SystemExit("cleanup trigger parser accepted ambiguous inline event syntax")


def main() -> None:
    test_contracts.EXPECTED_GITHUB_WORKFLOWS.update(
        {
            "branch-cleanup.yml",
            "post-gate-branch-cleanup.yml",
            "trusted-release-proof.yml",
            "release-promotion.yml",
            "release-verification.yml",
            "reusable-release-promote.yml",
            "reusable-release-verification.yml",
            "reusable-branch-cleanup.yml",
            "reusable-gated-branch-cleanup.yml",
        }
    )
    test_contracts.DEFAULT_CALLERS.update(
        {
            "release-promotion.yml",
            "release-verification.yml",
            "branch-cleanup.yml",
            "post-gate-branch-cleanup.yml",
        }
    )
    test_contracts.EXPECTED_SELF_ADAPTERS.add("release-proof.sh")
    test_contracts.main()
    test_cleanup_trigger_parser()

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
        "Authorize explicit dispatch",
        'EVENT_NAME: ${{ github.event_name }}',
        'if [[ "$EVENT_NAME" != "workflow_dispatch" ]]',
        "authorized only from an explicit workflow_dispatch caller",
        "def read_ref_path(branch: str)",
        "def delete_ref_path(branch: str)",
        "def has_open_pr(branch: str)",
        "def assert_default_unchanged(stage: str)",
        "validated_sha = {}",
        "default branch is never deletable",
        "branch is the head of an open pull request",
        "branch is protected by repository policy",
        "cleanup preflight rejected targets",
        "post-preflight validation",
        "branch became the head of an open pull request during cleanup",
        "branch became protected during cleanup",
        "branch moved after preflight",
        "not_deleted_target_moved",
        'current_sha != validated_sha[branch]',
        'call("DELETE", delete_ref_path(branch))',
        'call("GET", read_ref_path(branch), allow_404=True)',
        "branch deletion did not verify absent",
        "cleanup-evidence.json",
    ):
        require(cleanup, fragment, "reusable branch cleanup")

    gated = ".github/workflows/reusable-gated-branch-cleanup.yml"
    for fragment in (
        "workflow_call:",
        "required_gates_json:",
        "cleanup_workflow_file:",
        "Gated Branch Cleanup Authorization",
        "actions: write",
        'EVENT_NAME: ${{ github.event_name }}',
        'TRIGGER_RUN_ID: ${{ github.event.workflow_run.id }}',
        'TRIGGER_HEAD_SHA: ${{ github.event.workflow_run.head_sha }}',
        'event_name != "workflow_run"',
        'trigger_event != "push"',
        "target cleanup workflow must be workflow_dispatch-only",
        '"head_sha": expected, "event": "push"',
        'run.get("conclusion") != "success"',
        'evidence["state"] = "gate_failed"',
        'evidence["state"] = "deferred"',
        'evidence["state"] = "not_final_gate"',
        'evidence["state"] = "stale_trigger"',
        '"expected_default_sha": expected',
        '/actions/workflows/{workflow_id}/dispatches',
        'evidence["state"] = "dispatched"',
    ):
        require(gated, fragment, "reusable gated branch cleanup")
    reject(gated, "/git/refs/", "gated cleanup must delegate deletion")
    reject(gated, 'method="DELETE"', "gated cleanup must delegate deletion")

    caller = "templates/caller/branch-cleanup.yml"
    for fragment in (
        "workflow_dispatch:",
        "expected_default_sha:",
        "contents: write",
        "pull-requests: read",
        "reusable-branch-cleanup.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "inputs.expected_default_sha != '' && inputs.expected_default_sha || github.sha",
        'runner_json: \'"ubuntu-latest"\'',
        "dry_run: ${{ inputs.dry_run }}",
    ):
        require(caller, fragment, "generated branch cleanup caller")
    reject(caller, "issue_comment:", "generated branch cleanup caller authorization")

    post_gate_caller = "templates/caller/post-gate-branch-cleanup.yml"
    for fragment in (
        "workflow_run:",
        'workflows: ["CI", "Security", "CodeQL"]',
        "types: [completed]",
        "branches: [main]",
        "PRODKIT_GATED_CLEANUP_BRANCHES_JSON != ''",
        "actions: write",
        "reusable-gated-branch-cleanup.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "expected_default_sha: ${{ github.event.workflow_run.head_sha }}",
        "PRODKIT_GATED_CLEANUP_GATES_JSON",
        "cleanup_workflow_file: branch-cleanup.yml",
        "PRODKIT_RUNNER_JSON",
    ):
        require(post_gate_caller, fragment, "generated post-gate cleanup caller")
    if audit_org.workflow_events((ROOT / post_gate_caller).read_text(encoding="utf-8")) != {"workflow_run"}:
        raise SystemExit("generated post-gate cleanup caller must be workflow_run-only")
    reject(post_gate_caller, "contents: write", "post-gate cleanup orchestrator")

    self_caller = ".github/workflows/branch-cleanup.yml"
    for fragment in (
        "workflow_dispatch:",
        "branches_json:",
        "dry_run:",
        "expected_default_sha:",
        "contents: write",
        "pull-requests: read",
        "uses: ./.github/workflows/reusable-branch-cleanup.yml",
        "inputs.expected_default_sha != '' && inputs.expected_default_sha || github.sha",
        'runner_json: \'"ubuntu-latest"\'',
        "dry_run: ${{ inputs.dry_run }}",
    ):
        require(self_caller, fragment, "control-plane branch cleanup caller")
    if audit_org.workflow_events((ROOT / self_caller).read_text(encoding="utf-8")) != {"workflow_dispatch"}:
        raise SystemExit("control-plane branch cleanup caller must be workflow_dispatch-only")
    reject(self_caller, "issue_comment:", "control-plane branch cleanup caller authorization")
    reject(self_caller, "schedule:", "control-plane branch cleanup caller authorization")
    reject(self_caller, "pull_request_target:", "control-plane branch cleanup caller authorization")

    self_post_gate = ".github/workflows/post-gate-branch-cleanup.yml"
    for fragment in (
        "workflow_run:",
        'workflows: ["CI", "Security", "CodeQL"]',
        "PRODKIT_GATED_CLEANUP_BRANCHES_JSON != ''",
        "actions: write",
        "uses: ./.github/workflows/reusable-gated-branch-cleanup.yml",
        "expected_default_sha: ${{ github.event.workflow_run.head_sha }}",
        "cleanup_workflow_file: branch-cleanup.yml",
    ):
        require(self_post_gate, fragment, "control-plane post-gate cleanup caller")
    if audit_org.workflow_events((ROOT / self_post_gate).read_text(encoding="utf-8")) != {"workflow_run"}:
        raise SystemExit("control-plane post-gate cleanup caller must be workflow_run-only")
    reject(self_post_gate, "contents: write", "control-plane post-gate cleanup orchestrator")

    require(
        "scripts/audit_org.py",
        'workflow_events(text) != {"workflow_dispatch"}',
        "branch cleanup trigger audit",
    )
    require(
        "scripts/audit_org.py",
        '"post-gate-branch-cleanup.yml": "reusable-gated-branch-cleanup.yml"',
        "post-gate cleanup organization audit",
    )


if __name__ == "__main__":
    main()
