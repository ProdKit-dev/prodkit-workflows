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
    verification = text(".github/workflows/reusable-release-verification.yml")
    reusable_release = text(".github/workflows/reusable-release.yml")
    compatibility_release = text(".github/workflows/reusable-release-pipeline.yml")
    proof_template = text("templates/caller/trusted-release-proof.yml")
    verification_template = text("templates/caller/release-verification.yml")
    release_template = text("templates/caller/release.yml")
    bootstrap = text("scripts/bootstrap_consumer.py")
    audit = text("scripts/audit_org.py")
    lifecycle = text("docs/LIFECYCLE.md")
    contracts = text("docs/CONTRACTS.md")
    security_model = text("docs/SECURITY-MODEL.md")
    readme = text("README.md")

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
        "actions: read",
        "contents: read",
        "SHA256SUMS",
        "target_commitish",
        "release_workflow_file",
        "published asset set mismatch",
        "GitHub asset digest mismatch",
    ):
        require(verification, needle, "reusable release verification")
    for forbidden in ("actions: write", "contents: write", "time.sleep(", "while time.time()"):
        reject(verification, forbidden, "reusable release verification")

    for needle in (
        "reusable-release-proof.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "needs: proof",
        "actions: write",
    ):
        require(proof_template, needle, "trusted release proof caller template")

    for needle in (
        "workflow_run:",
        'workflows: ["Release"]',
        "reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "workflow_run.head_sha",
    ):
        require(verification_template, needle, "release verification caller template")

    require(
        release_template,
        "PROOF_WORKFLOW_FILE: .github/workflows/trusted-release-proof.yml",
        "release caller template",
    )
    require(release_template, 'run.get("path") == workflow_file', "release caller template")
    reject(release_template, "PROOF_WORKFLOW: Trusted Release Proof", "release caller template")

    # The reusable publisher owns version-level serialization. A direct caller
    # must not claim the same release-${version} group or it can hold the group
    # while waiting for the called workflow, preventing the called publisher
    # from ever materializing.
    require(reusable_release, "group: release-${{ inputs.version }}", "reusable release")
    reject(release_template, "group: release-${{ inputs.version }}", "release caller template")

    # GitHub Artifact Attestations are plan/repository-capability dependent.
    # Both the current publisher and retained compatibility controller must
    # remain opt-in. Explicit opt-in stays release-fatal.
    attest_block = reusable_release.split("      attest:\n", 1)[1].split(
        "      environment:\n", 1
    )[0]
    require(attest_block, "default: false", "reusable release attestation input")
    require(
        reusable_release,
        "if: steps.preflight.outputs.published != 'true' && inputs.attest",
        "reusable release attestation step",
    )
    require(reusable_release, "uses: actions/attest@", "reusable release attestation step")

    compatibility_attest_block = compatibility_release.split("      attest:\n", 1)[1].split(
        "      environment:\n", 1
    )[0]
    require(
        compatibility_attest_block,
        "default: false",
        "compatibility release attestation input",
    )
    require(
        compatibility_release,
        "attest: ${{ inputs.attest }}",
        "compatibility release attestation forwarding",
    )

    require(
        bootstrap,
        'src / "caller/release-verification.yml"',
        "consumer bootstrap",
    )
    require(
        audit,
        '"release-verification.yml": "reusable-release-verification.yml"',
        "organization audit",
    )
    require(audit, "must not wait for Release on the trusted runner", "organization audit")

    require(lifecycle, "Single-runner non-blocking rule", "lifecycle documentation")
    require(
        lifecycle,
        "must never dispatch another workflow that also needs the runner and then poll",
        "lifecycle documentation",
    )
    require(lifecycle, "Artifact Attestations are optional", "lifecycle documentation")
    require(contracts, "Artifact Attestations are capability-dependent", "consumer contracts")
    require(
        security_model,
        "Artifact Attestations are an optional additional trust signal",
        "security model",
    )
    require(
        readme,
        "Artifact Attestations are an optional additional provenance layer",
        "README",
    )

    print("release lifecycle contracts passed")


if __name__ == "__main__":
    main()
