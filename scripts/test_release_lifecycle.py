#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{label} missing {needle!r}")


def reject(haystack: str, needle: str, label: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{label} contains forbidden {needle!r}")


def main() -> None:
    promote = text(".github/workflows/reusable-release-promote.yml")
    reusable_proof = text(".github/workflows/reusable-release-proof.yml")
    proof_bridge = text(".github/workflows/reusable-release-proof-promotion-dispatch.yml")
    verification = text(".github/workflows/reusable-release-verification.yml")
    verification_dispatch = text(".github/workflows/reusable-release-verification-dispatch.yml")
    reusable_release = text(".github/workflows/reusable-release.yml")
    compatibility_release = text(".github/workflows/reusable-release-pipeline.yml")
    proof_template = text("templates/caller/trusted-release-proof.yml")
    dispatch_template = text("templates/caller/release-proof-dispatch.yml")
    promotion_template = text("templates/caller/release-promotion.yml")
    verification_template = text("templates/caller/release-verification.yml")
    release_template = text("templates/caller/release.yml")
    cleanup_template = text("templates/caller/branch-cleanup.yml")
    post_gate_template = text("templates/caller/post-gate-branch-cleanup.yml")
    audit = text("scripts/audit_org.py")
    lifecycle = text("docs/LIFECYCLE.md")
    adoption = text("docs/ADOPTION.md")
    runners = text("docs/RUNNERS.md")

    for needle in (
        "actions: write",
        "source_sha:",
        "manifest_path:",
        "release_workflow_file:",
        "/dispatches",
        "version.sources",
        "no duplicate dispatch",
    ):
        require(promote, needle, "reusable release promotion")
    for forbidden in ("time.sleep(", "while time.time()", "wait_for_release", "wait_run("):
        reject(promote, forbidden, "reusable release promotion")

    for needle in (
        "Verify permanent exact-SHA gates",
        "prepare_release_payload:",
        "Build promotable release payload once",
        "release-payload.json",
        "trusted-release-proof-${{ inputs.source_sha }}",
    ):
        require(reusable_proof, needle, "reusable release proof")

    for needle in (
        "workflow_dispatch:",
        "prepare_release_payload: true",
        "source_sha: ${{ github.sha }}",
        "needs: proof",
        "promote proven release",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE != 'true'",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "PRODKIT_RUNNER_JSON",
    ):
        require(proof_template, needle, "trusted release proof caller template")
    reject(proof_template, "workflow_run:", "trusted release proof dispatch boundary")

    for needle in (
        "reusable-release-proof-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "PRODKIT_RUNNER_JSON",
        "bridge proof to promotion",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
        "reusable-release-proof-promotion-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        'runner_json: \'"ubuntu-latest"\'',
    ):
        require(dispatch_template, needle, "release proof dispatch template")

    for needle in (
        "release-proof-promotion-dispatch-",
        "proof_timeout_seconds:",
        "poll_seconds:",
        "timed out waiting for exact-source Trusted Release Proof",
        "promotion_workflow_file",
        '"proof_run_id": str(selected_proof["id"])',
        "time.sleep(poll_seconds)",
    ):
        require(proof_bridge, needle, "optional hosted proof observer")
    reject(proof_bridge, "contents: write", "hosted proof observer mutation boundary")

    for needle in (
        "workflow_run:",
        'workflows: ["Trusted Release Proof"]',
        "workflow_dispatch:",
        "source_sha:",
        "proof_run_id:",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event_name == 'workflow_dispatch'",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "PRODKIT_RUNNER_JSON",
    ):
        require(promotion_template, needle, "release promotion caller template")
    for forbidden in ("time.sleep(", "while time.time()", "wait_for_release"):
        reject(promotion_template, forbidden, "release promotion caller template")

    for needle in (
        "actions: write",
        "contents: read",
        "pull-requests: read",
        "SHA256SUMS",
        "target_commitish",
        "release_workflow_file",
        "published asset set mismatch",
        "GitHub asset digest mismatch",
        "automatic_cleanup:",
        "cleanup_workflow_file:",
        "cleanup_branch_prefixes_json:",
        "Dispatch verified release branch cleanup",
    ):
        require(verification, needle, "reusable release verification")
    reject(verification, "contents: write", "verification ref mutation boundary")

    for needle in (
        "workflow_dispatch:",
        "reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "source_sha: ${{ github.sha }}",
        "release_run_id: ${{ inputs.release_run_id }}",
        "automatic_cleanup: true",
        "cleanup_workflow_file: branch-cleanup.yml",
    ):
        require(verification_template, needle, "release verification template")
    reject(verification_template, "workflow_run:", "verification chain-depth safety")

    for needle in (
        "actions: write",
        "release_run_id:",
        "verification_workflow_file:",
        '"ref": tag',
        '"release_run_id": release_run_id',
        "/dispatches",
    ):
        require(verification_dispatch, needle, "reusable verification dispatch")
    reject(verification_dispatch, "time.sleep(", "reusable verification dispatch")

    for needle in (
        "target_sha: ${{ github.sha }}",
        "proof_workflow_file: .github/workflows/trusted-release-proof.yml",
        "reuse_proof_payload: true",
        "verification-dispatch:",
        "needs: release",
        "reusable-release-verification-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "release_run_id: ${{ github.run_id }}",
        "PRODKIT_RUNNER_JSON",
    ):
        require(release_template, needle, "release caller template")
    reject(release_template, "proof-gate:", "release caller template")
    reject(release_template, "urllib.request", "release caller template")

    for needle in (
        "proof_workflow_file:",
        "reuse_proof_payload:",
        "missing successful exact-SHA workflow_dispatch proof",
        "Download proof-produced release payload",
        "proof payload digest mismatch",
        "group: release-${{ inputs.version }}",
        "Create or resume immutable publication",
    ):
        require(reusable_release, needle, "reusable release publisher")
    require(reusable_release, "uses: actions/attest@", "optional artifact attestation")
    require(
        reusable_release,
        "needs.prepare.outputs.published != 'true' && inputs.attest",
        "attestation guard",
    )
    require(
        compatibility_release,
        "reuse_proof_payload: ${{ inputs.reuse_proof_payload }}",
        "compatibility proof-payload forwarding",
    )

    for template, label in (
        (cleanup_template, "branch cleanup template"),
        (post_gate_template, "post-gate cleanup template"),
    ):
        require(template, "PRODKIT_RUNNER_JSON", label)
    require(cleanup_template, "contents: write", "branch cleanup mutation authority")
    reject(post_gate_template, "contents: write", "post-gate cleanup delegation")

    for needle in (
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE",
        "trusted-release-proof.yml must be workflow_dispatch-only",
        "release-proof-dispatch.yml must not mutate repository content",
        "release-verification.yml may dispatch cleanup but must not mutate refs directly",
    ):
        require(audit, needle, "organization audit")

    require(lifecycle, "Single-runner non-blocking rule", "lifecycle documentation")
    require(lifecycle, "serialized proof-to-promotion", "lifecycle documentation")
    require(adoption, "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE", "adoption guide")
    require(runners, "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE", "runner guide")

    print("release lifecycle contracts passed")


if __name__ == "__main__":
    main()
