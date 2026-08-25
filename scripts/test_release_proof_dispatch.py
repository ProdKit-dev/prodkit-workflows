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
    reusable = text(".github/workflows/reusable-release-proof-dispatch.yml")
    bridge = text(".github/workflows/reusable-release-proof-promotion-dispatch.yml")
    caller = text(".github/workflows/release-proof-dispatch.yml")
    template = text("templates/caller/release-proof-dispatch.yml")
    self_proof = text(".github/workflows/trusted-release-proof.yml")
    proof = text("templates/caller/trusted-release-proof.yml")
    promotion = text("templates/caller/release-promotion.yml")
    audit = text("scripts/audit_org.py")

    for needle in (
        "actions: write",
        "contents: read",
        "release-proof-dispatch-${{ inputs.source_sha }}",
        "release proof dispatch deferred until exact-main gates complete",
        "exact-main release gates completed unsuccessfully",
        "required_workflows_json",
        "proof_workflow_file",
        "/dispatches",
        '"ref": main_branch',
        "successful exact-source Trusted Release Proof already exists",
        "active exact-source Trusted Release Proof already exists",
        'expected_source_contract = "source_sha: $" + "{{ github.sha }}"',
    ):
        require(reusable, needle, "reusable automatic proof dispatcher")
    reject(reusable, "contents: write", "dispatcher mutation boundary")
    for forbidden in ("time.sleep(", "while time.time()", "wait_for_proof"):
        reject(reusable, forbidden, "dispatcher non-blocking contract")

    for needle in (
        "release-proof-promotion-dispatch-${{ inputs.source_sha }}",
        "proof_timeout_seconds:",
        "poll_seconds:",
        "timed out waiting for exact-source Trusted Release Proof",
        "promotion_workflow_file",
        '"proof_run_id": str(selected_proof["id"])',
        "time.sleep(poll_seconds)",
    ):
        require(bridge, needle, "optional hosted proof/promotion bridge")
    reject(bridge, "contents: write", "proof/promotion bridge mutation boundary")

    for body, label in ((caller, "self caller"), (template, "consumer caller template")):
        for needle in (
            "workflow_run:",
            'workflows: ["CI", "Security"]',
            "types: [completed]",
            "branches: [main]",
            "github.event.workflow_run.event == 'push'",
            "source_sha: ${{ github.event.workflow_run.head_sha }}",
            "required_workflows_json: '[\"CI\",\"Security\"]'",
            "proof_workflow_file: trusted-release-proof.yml",
            "bridge proof to promotion",
            "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
            'runner_json: \'"ubuntu-latest"\'',
            "promotion_workflow_file: release-promotion.yml",
        ):
            require(body, needle, label)
        reject(body, "workflow_run.conclusion == 'success'", label + " gate delegation")
        reject(body, "contents: write", label)
    require(template, "PRODKIT_RUNNER_JSON", "consumer trusted-runner dispatcher")

    for body, label in ((self_proof, "self proof"), (proof, "consumer proof template")):
        for needle in (
            "workflow_dispatch:",
            "source_sha: ${{ github.sha }}",
            "needs: proof",
            "promote proven release",
            "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE != 'true'",
            "actions: write",
            "reusable-release-promote.yml",
            "release_workflow_file: release.yml",
        ):
            require(body, needle, label)
        reject(body, "workflow_run:", label + " dispatch boundary")
    require(self_proof, 'runner_json: \'"ubuntu-latest"\'', "self proof hosted policy")
    require(proof, "PRODKIT_RUNNER_JSON", "consumer proof trusted-runner policy")

    for needle in (
        "workflow_run:",
        "workflow_dispatch:",
        "source_sha:",
        "proof_run_id:",
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event_name == 'workflow_dispatch'",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "PRODKIT_RUNNER_JSON",
    ):
        require(promotion, needle, "Release Promotion dual-entry consumer caller")

    for needle in (
        '"release-proof-dispatch.yml": "reusable-release-proof-dispatch.yml"',
        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE",
        "trusted-release-proof.yml must be workflow_dispatch-only",
        "release-promotion.yml must not poll or wait for Release",
    ):
        require(audit, needle, "organization audit")

    print("automatic release proof dispatch contract passed")


if __name__ == "__main__":
    main()
