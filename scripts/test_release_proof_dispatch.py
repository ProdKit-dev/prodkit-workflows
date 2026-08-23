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
    caller = text(".github/workflows/release-proof-dispatch.yml")
    template = text("templates/caller/release-proof-dispatch.yml")
    proof = text("templates/caller/trusted-release-proof.yml")
    bootstrap = text("scripts/bootstrap_consumer.py")
    audit = text("scripts/audit_org.py")

    for needle in (
        "actions: write",
        "contents: read",
        "release-proof-dispatch-${{ inputs.source_sha }}",
        "canonical version",
        "release proof dispatch deferred until exact-main gates complete",
        "required_workflows_json",
        "proof_workflow_file",
        '"/dispatches"',
        '"ref": main_branch',
        "successful exact-source Trusted Release Proof already exists",
        "active exact-source Trusted Release Proof already exists",
        'expected_source_contract = "source_sha: $" + "{{ github.sha }}"',
    ):
        require(reusable, needle, "reusable automatic proof dispatcher")
    reject(reusable, 'if "source_sha: ${{ github.sha }}" not in caller_text:', "dispatcher interpolation safety")
    reject(reusable, "contents: write", "dispatcher mutation boundary")
    for forbidden in ("time.sleep(", "while time.time()", "wait_for_proof"):
        reject(reusable, forbidden, "dispatcher non-blocking contract")

    for body, label in ((caller, "self caller"), (template, "consumer caller template")):
        for needle in (
            "workflow_run:",
            'workflows: ["CI", "Security"]',
            "types: [completed]",
            "branches: [main]",
            "github.event.workflow_run.event == 'push'",
            "github.event.workflow_run.conclusion == 'success'",
            "source_sha: ${{ github.event.workflow_run.head_sha }}",
            'runner_json: \'"ubuntu-latest"\'',
            "required_workflows_json: '[\"CI\",\"Security\"]'",
            "proof_workflow_file: trusted-release-proof.yml",
        ):
            require(body, needle, label)
        reject(body, "contents: write", label)

    require(
        caller,
        "uses: ./.github/workflows/reusable-release-proof-dispatch.yml",
        "self caller local reusable pin",
    )
    require(
        template,
        "reusable-release-proof-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "consumer caller immutable central pin",
    )

    require(proof, "workflow_dispatch:", "Trusted Release Proof dispatch boundary")
    reject(proof, "workflow_run:", "Trusted Release Proof dispatch boundary")
    require(proof, "source_sha: ${{ github.sha }}", "Trusted Release Proof exact source")

    require(bootstrap, 'src / "caller/release-proof-dispatch.yml"', "consumer bootstrap")
    require(audit, '"release-proof-dispatch.yml": "reusable-release-proof-dispatch.yml"', "organization audit")
    require(audit, 'if filename == "release-proof-dispatch.yml":', "organization audit")

    print("automatic release proof dispatch contract passed")


if __name__ == "__main__":
    main()
