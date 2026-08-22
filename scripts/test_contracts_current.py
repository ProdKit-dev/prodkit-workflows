#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import test_contracts


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, fragment: str, label: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if fragment not in content:
        raise SystemExit(f"{label} missing {fragment!r}")


def main() -> None:
    test_contracts.EXPECTED_GITHUB_WORKFLOWS.update(
        {
            "trusted-release-proof.yml",
            "release-verification.yml",
            "reusable-release-promote.yml",
            "reusable-release-verification.yml",
        }
    )
    test_contracts.DEFAULT_CALLERS.add("release-verification.yml")
    test_contracts.EXPECTED_SELF_ADAPTERS.add("release-proof.sh")
    test_contracts.main()

    require(
        "templates/caller/trusted-release-proof.yml",
        'node_version: "24"',
        "generated proof payload runtime",
    )
    require(
        ".github/workflows/trusted-release-proof.yml",
        "uses: ./.github/workflows/reusable-release-proof.yml",
        "control-plane trusted proof",
    )
    require(
        ".github/workflows/trusted-release-proof.yml",
        "uses: ./.github/workflows/reusable-release-promote.yml",
        "control-plane proof promotion",
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
