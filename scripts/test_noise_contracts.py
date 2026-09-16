#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, fragment: str, label: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if fragment not in text:
        raise SystemExit(f"{label} missing {fragment!r}")


def reject(path: str, fragment: str, label: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    if fragment in text:
        raise SystemExit(f"{label} contains forbidden {fragment!r}")


def main() -> None:
    workflow = ".github/workflows/reusable-codeql.yml"
    template = "templates/consumer/.prodkit/workflows/codeql-check.sh"

    for fragment in (
        "language-scoped SARIF policy adapter",
        "must not run repository-global hygiene or unrelated gates",
        "PRODKIT_CODEQL_SCOPE: language-sarif-v1",
        "PRODKIT_CODEQL_LANGUAGE: ${{ matrix.language }}",
        "PRODKIT_CODEQL_OUTPUT_DIR: .artifacts/codeql/${{ matrix.language }}",
        "repository-global hygiene belongs in CI, not CodeQL",
    ):
        require(workflow, fragment, "CodeQL noise-isolation contract")

    for fragment in (
        "PRODKIT_CODEQL_SCOPE",
        "PRODKIT_CODEQL_LANGUAGE",
        "PRODKIT_CODEQL_OUTPUT_DIR",
        '[[ "$PRODKIT_CODEQL_SCOPE" == "language-sarif-v1" ]]',
        "CodeQL policy failed for {language}",
    ):
        require(template, fragment, "generated CodeQL language-policy adapter")

    for forbidden in (
        "check_repository.py",
        "test_contracts.py",
        "ci-hygiene.sh",
        "make check",
    ):
        reject(template, forbidden, "generated CodeQL adapter must remain language-local")

    print("workflow noise-isolation contracts passed")


if __name__ == "__main__":
    main()
