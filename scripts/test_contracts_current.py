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
        raise SystemExit("trigger parser rejected canonical workflow_dispatch-only caller")

    for extra in (
        '  "pull_request_target":\n',
        "  'schedule':\n",
        "  repository_dispatch:\n",
        "  workflow_run:\n",
    ):
        candidate = canonical.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n" + extra)
        if audit_org.workflow_events(candidate) == {"workflow_dispatch"}:
            raise SystemExit(f"trigger parser ignored additional event: {extra.strip()}")

    ambiguous = """name: Branch Cleanup
on: [workflow_dispatch, push]
permissions:
  contents: write
"""
    if audit_org.workflow_events(ambiguous) == {"workflow_dispatch"}:
        raise SystemExit("trigger parser accepted ambiguous inline event syntax")


def main() -> None:
    test_contracts.EXPECTED_GITHUB_WORKFLOWS.update(
        {
            "branch-cleanup.yml",
            "post-gate-branch-cleanup.yml",
            "release-proof-dispatch.yml",
            "trusted-release-proof.yml",
            "release-promotion.yml",
            "release-verification.yml",
            "reusable-release-promote.yml",
            "reusable-release-proof-dispatch.yml",
            "reusable-release-proof-promotion-dispatch.yml",
            "reusable-release-verification.yml",
            "reusable-release-verification-dispatch.yml",
            "reusable-branch-cleanup.yml",
            "reusable-gated-branch-cleanup.yml",
        }
    )
    test_contracts.DEFAULT_CALLERS.update(
        {
            "release-proof-dispatch.yml",
            "trusted-release-proof.yml",
            "release-promotion.yml",
            "release-verification.yml",
            "branch-cleanup.yml",
            "post-gate-branch-cleanup.yml",
        }
    )
    test_contracts.EXPECTED_SELF_ADAPTERS.add("release-proof.sh")
    test_contracts.main()
    test_cleanup_trigger_parser()

    for caller in (
        "templates/caller/release-proof-dispatch.yml",
        "templates/caller/trusted-release-proof.yml",
        "templates/caller/release-promotion.yml",
        "templates/caller/release.yml",
        "templates/caller/branch-cleanup.yml",
        "templates/caller/post-gate-branch-cleanup.yml",
    ):
        require(caller, "PRODKIT_RUNNER_JSON", "generated trusted-runner policy")

    require(
        "templates/caller/release-proof-dispatch.yml",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
        "optional hosted proof observer",
    )
    require(
        "templates/caller/release-proof-dispatch.yml",
        "reusable-release-proof-promotion-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "hosted proof observer immutable pin",
    )
    require(
        "templates/caller/trusted-release-proof.yml",
        "needs: proof",
        "serialized proof promotion dependency",
    )
    require(
        "templates/caller/trusted-release-proof.yml",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE != 'true'",
        "serialized proof promotion mode",
    )
    require(
        "templates/caller/trusted-release-proof.yml",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "serialized promotion immutable pin",
    )
    require(
        "templates/caller/release-promotion.yml",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
        "hosted workflow_run promotion gate",
    )

    for caller in (
        ".github/workflows/release-proof-dispatch.yml",
        ".github/workflows/trusted-release-proof.yml",
        ".github/workflows/release-promotion.yml",
        ".github/workflows/release.yml",
        ".github/workflows/branch-cleanup.yml",
        ".github/workflows/post-gate-branch-cleanup.yml",
    ):
        require(caller, "PRODKIT_RUNNER_JSON", "control-plane trusted-runner policy")

    require(
        ".github/workflows/trusted-release-proof.yml",
        "uses: ./.github/workflows/reusable-release-promote.yml",
        "control-plane serialized promotion",
    )
    require(
        ".github/workflows/release.yml",
        "reuse_proof_payload: true",
        "control-plane proof payload reuse",
    )
    require(
        ".github/workflows/release.yml",
        "uses: ./.github/workflows/reusable-release-verification-dispatch.yml",
        "control-plane verification dispatch",
    )

    proof_dispatcher = ".github/workflows/reusable-release-proof-dispatch.yml"
    for fragment in (
        "workflow_call:",
        "actions: write",
        "contents: read",
        "release-proof-dispatch-${{ inputs.source_sha }}",
        "required_workflows_json:",
        "proof_workflow_file:",
        "release proof dispatch deferred until exact-main gates complete",
        "Trusted Release Proof caller must remain workflow_dispatch-only",
        'expected_source_contract = "source_sha: $" + "{{ github.sha }}"',
        "successful exact-source Trusted Release Proof already exists",
        "active exact-source Trusted Release Proof already exists",
        "/dispatches",
    ):
        require(proof_dispatcher, fragment, "reusable proof dispatcher")
    reject(proof_dispatcher, "time.sleep(", "proof dispatcher must not wait for child")
    reject(proof_dispatcher, "contents: write", "proof dispatcher mutation boundary")

    cleanup = ".github/workflows/reusable-branch-cleanup.yml"
    for fragment in (
        "workflow_call:",
        "branches_json:",
        "expected_default_sha:",
        "dry_run:",
        "Branch Cleanup Required",
        "group: branch-cleanup-${{ github.repository }}",
        "cancel-in-progress: false",
        "default branch is never deletable",
        "branch is the head of an open pull request",
        "branch is protected by repository policy",
        "branch moved after preflight",
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
        '"expected_default_sha": expected',
        '"dry_run": False',
        '/actions/workflows/{workflow_id}/dispatches',
    ):
        require(gated, fragment, "reusable gated branch cleanup")
    reject(gated, "/git/refs/", "gated cleanup must delegate deletion")
    reject(gated, 'method="DELETE"', "gated cleanup must delegate deletion")

    for caller in (
        "templates/caller/branch-cleanup.yml",
        ".github/workflows/branch-cleanup.yml",
    ):
        require(caller, "workflow_dispatch:", "branch cleanup authorization")
        require(caller, "contents: write", "branch cleanup mutation authority")
        require(caller, "PRODKIT_RUNNER_JSON", "branch cleanup runner policy")
        reject(caller, "issue_comment:", "branch cleanup authorization")

    for caller in (
        "templates/caller/post-gate-branch-cleanup.yml",
        ".github/workflows/post-gate-branch-cleanup.yml",
    ):
        require(caller, "workflow_run:", "post-gate cleanup trigger")
        require(caller, "PRODKIT_RUNNER_JSON", "post-gate cleanup runner policy")
        reject(caller, "contents: write", "post-gate cleanup must delegate mutation")

    require(
        "scripts/audit_org.py",
        '"release-proof-dispatch.yml": "reusable-release-proof-dispatch.yml"',
        "automatic proof dispatch organization audit",
    )
    require(
        "scripts/audit_org.py",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE",
        "serial/hosted lifecycle organization audit",
    )

    print("current consumer contracts passed")


if __name__ == "__main__":
    main()
