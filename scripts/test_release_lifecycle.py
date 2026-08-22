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
    verification = text(".github/workflows/reusable-release-verification.yml")
    reusable_release = text(".github/workflows/reusable-release.yml")
    compatibility_release = text(".github/workflows/reusable-release-pipeline.yml")
    proof_template = text("templates/caller/trusted-release-proof.yml")
    proof_adapter_template = text("templates/consumer/.prodkit/workflows/release-proof.sh")
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

    # Proof consumes permanent exact-SHA evidence instead of rerunning CI/Security,
    # then produces the repository-owned promotable payload exactly once.
    for needle in (
        "Verify permanent exact-SHA gates",
        "prepare_release_payload:",
        "Build promotable release payload once",
        "release-payload.json",
        "trusted-release-proof-${{ inputs.source_sha }}",
    ):
        require(reusable_proof, needle, "reusable release proof")
    for needle in (
        "prepare_release_payload: true",
        "required_workflows_json: '[\"CI\",\"Security\"]'",
        "actions: read",
        "reusable-release-proof.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "needs: proof",
        "actions: write",
    ):
        require(proof_template, needle, "trusted release proof caller template")
    for forbidden in (
        "ci-python.sh",
        "ci-node.sh",
        "security-python.sh",
        "security-node.sh",
        "security-custom.sh",
        "release-build.sh",
    ):
        reject(proof_adapter_template, forbidden, "release proof adapter template")
    require(
        proof_adapter_template,
        "Do not rerun CI/Security matrices here",
        "release proof adapter template",
    )

    for needle in (
        "workflow_run:",
        'workflows: ["Release"]',
        "reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "workflow_run.head_sha",
    ):
        require(verification_template, needle, "release verification caller template")

    # Release authorization belongs to the central publisher, not copied Python
    # in every consumer caller.
    require(
        release_template,
        "proof_workflow_file: .github/workflows/trusted-release-proof.yml",
        "release caller template",
    )
    require(release_template, "reuse_proof_payload: true", "release caller template")
    reject(release_template, "proof-gate:", "release caller template")
    reject(release_template, "urllib.request", "release caller template")
    require(reusable_release, "proof_workflow_file:", "reusable release proof input")
    require(reusable_release, "reuse_proof_payload:", "reusable release proof-payload input")
    require(
        reusable_release,
        "x.get('path')==proof_file",
        "reusable release proof authorization",
    )
    require(
        reusable_release,
        "missing successful exact-SHA workflow_dispatch proof",
        "reusable release proof authorization",
    )
    for needle in (
        "proof_run_id:",
        "Download proof-produced release payload",
        "release-payload.json",
        "proof payload digest mismatch",
        "Run compatibility release build contract",
    ):
        require(reusable_release, needle, "proof-payload reuse")

    # The reusable publisher owns version-level serialization. A direct caller
    # must not claim the same release-${version} group.
    require(reusable_release, "group: release-${{ inputs.version }}", "reusable release")
    reject(release_template, "group: release-${{ inputs.version }}", "release caller template")

    # Release publication is checkpointed at job boundaries. A late attest or
    # publish failure can use GitHub's "re-run failed jobs" semantics without
    # rebuilding a successful sealed payload.
    for needle in (
        "  prepare:",
        "  build:",
        "  attest:",
        "  publish:",
        "name: Upload sealed release payload",
        "actions/download-artifact@",
        "needs: [prepare, build]",
        "needs: [prepare, build, attest]",
        "Create or resume immutable publication",
        "overwrite: true",
    ):
        require(reusable_release, needle, "resumable release publisher")
    reject(reusable_release, "  release:\n    name: Guarded release", "resumable release publisher")
    require(
        reusable_release,
        "if name in remote: continue",
        "resumable draft asset upload",
    )
    reject(
        reusable_release,
        "for a in rel.get('assets',[]): request('DELETE',a['url'])",
        "resumable draft asset upload",
    )

    # GitHub Artifact Attestations are plan/repository-capability dependent.
    attest_block = reusable_release.split("      attest:\n", 1)[1].split(
        "      environment:\n", 1
    )[0]
    require(attest_block, "default: false", "reusable release attestation input")
    require(
        reusable_release,
        "needs.prepare.outputs.published != 'true' && inputs.attest",
        "reusable release attestation job",
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
        compatibility_release,
        "proof_workflow_file: ${{ inputs.proof_workflow_file }}",
        "compatibility release proof forwarding",
    )
    require(
        compatibility_release,
        "reuse_proof_payload: ${{ inputs.reuse_proof_payload }}",
        "compatibility proof-payload forwarding",
    )
    reject(compatibility_release, "proof-gate:", "compatibility release pipeline")
    reject(compatibility_release, "urllib.request", "compatibility release pipeline")

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
    require(lifecycle, "Re-run failed jobs", "lifecycle documentation")
    require(lifecycle, "proof-produced", "lifecycle documentation")
    require(contracts, "Artifact Attestations are capability-dependent", "consumer contracts")
    require(contracts, "sealed payload", "consumer contracts")
    require(contracts, "proof-produced", "consumer contracts")
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
    require(readme, "Re-run failed jobs", "README")
    require(readme, "proof-produced", "README")

    print("release lifecycle contracts passed")


if __name__ == "__main__":
    main()
