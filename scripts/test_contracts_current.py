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
        }
    )
    test_contracts.DEFAULT_CALLERS.update(
        {"release-promotion.yml", "release-verification.yml"}
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


if __name__ == "__main__":
    main()
