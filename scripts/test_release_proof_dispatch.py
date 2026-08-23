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
    proof = text("templates/caller/trusted-release-proof.yml")
    promotion = text("templates/caller/release-promotion.yml")
    bootstrap = text("scripts/bootstrap_consumer.py")
    audit = text("scripts/audit_org.py")

    for needle in (
        "actions: write",
        "contents: read",
        "release-proof-dispatch-${{ inputs.source_sha }}",
        "canonical version",
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
    reject(reusable, 'if "source_sha: ${{ github.sha }}" not in caller_text:', "dispatcher interpolation safety")
    reject(reusable, "contents: write", "dispatcher mutation boundary")
    for forbidden in ("time.sleep(", "while time.time()", "wait_for_proof"):
        reject(reusable, forbidden, "dispatcher non-blocking contract")

    # GitHub suppresses workflow_run listeners for workflows dispatched with the
    # repository GITHUB_TOKEN. Keep the proof dispatcher itself non-blocking,
    # then use a GitHub-hosted bounded bridge to observe the exact proof and
    # explicitly workflow_dispatch Release Promotion.
    for needle in (
        "actions: write",
        "contents: read",
        "release-proof-promotion-dispatch-${{ inputs.source_sha }}",
        "proof_timeout_seconds:",
        "poll_seconds:",
        "proof/promotion bridge deferred until exact-main gates complete",
        "timed out waiting for exact-source Trusted Release Proof",
        "exact-source Trusted Release Proof",
        "Release Promotion caller must accept workflow_dispatch exact-source handoff",
        "promotion_workflow_file",
        '"source_sha": source_sha',
        '"proof_run_id": str(selected_proof["id"])',
        "no duplicate dispatch",
        "time.sleep(poll_seconds)",
    ):
        require(bridge, needle, "proof/promotion bridge")
    reject(bridge, "contents: write", "proof/promotion bridge mutation boundary")
    require(bridge, 'default: \'"ubuntu-latest"\'', "proof/promotion bridge hosted default")

    for body, label in ((caller, "self caller"), (template, "consumer caller template")):
        for needle in (
            "workflow_run:",
            'workflows: ["CI", "Security"]',
            "types: [completed]",
            "branches: [main]",
            "github.event.workflow_run.event == 'push'",
            "source_sha: ${{ github.event.workflow_run.head_sha }}",
            'runner_json: \'"ubuntu-latest"\'',
            "required_workflows_json: '[\"CI\",\"Security\"]'",
            "proof_workflow_file: trusted-release-proof.yml",
            "bridge proof to promotion",
            "promotion_workflow_file: release-promotion.yml",
        ):
            require(body, needle, label)
        reject(body, "workflow_run.conclusion == 'success'", label + " must delegate gate outcomes")
        reject(body, "contents: write", label)

    require(
        caller,
        "uses: ./.github/workflows/reusable-release-proof-dispatch.yml",
        "self caller local proof dispatcher",
    )
    require(
        caller,
        "uses: ./.github/workflows/reusable-release-proof-promotion-dispatch.yml",
        "self caller local proof promotion bridge",
    )
    require(
        template,
        "reusable-release-proof-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "consumer caller immutable proof dispatcher pin",
    )
    require(
        template,
        "reusable-release-proof-promotion-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "consumer caller immutable proof promotion bridge pin",
    )

    require(proof, "workflow_dispatch:", "Trusted Release Proof dispatch boundary")
    reject(proof, "workflow_run:", "Trusted Release Proof dispatch boundary")
    require(proof, "source_sha: ${{ github.sha }}", "Trusted Release Proof exact source")

    for needle in (
        "workflow_run:",
        "workflow_dispatch:",
        "source_sha:",
        "proof_run_id:",
        "github.event_name == 'workflow_dispatch'",
        "reusable-release-promote.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
    ):
        require(promotion, needle, "Release Promotion dual-entry caller")

    require(bootstrap, 'src / "caller/release-proof-dispatch.yml"', "consumer bootstrap")
    require(audit, '"release-proof-dispatch.yml": "reusable-release-proof-dispatch.yml"', "organization audit")
    require(audit, 'if filename == "release-proof-dispatch.yml":', "organization audit")
    require(audit, "must let the central dispatcher evaluate gate conclusions", "organization audit")

    print("automatic release proof dispatch contract passed")


if __name__ == "__main__":
    main()
