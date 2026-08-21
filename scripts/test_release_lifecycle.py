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
    proof_template = text("templates/caller/trusted-release-proof.yml")
    verification_template = text("templates/caller/release-verification.yml")
    release_template = text("templates/caller/release.yml")
    bootstrap = text("scripts/bootstrap_consumer.py")
    audit = text("scripts/audit_org.py")
    lifecycle = text("docs/LIFECYCLE.md")

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

    print("release lifecycle contracts passed")


if __name__ == "__main__":
    main()
