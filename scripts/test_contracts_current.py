#!/usr/bin/env python3
from __future__ import annotations

import test_contracts


def main() -> None:
    test_contracts.EXPECTED_GITHUB_WORKFLOWS.update(
        {
            "reusable-release-promote.yml",
            "reusable-release-verification.yml",
        }
    )
    test_contracts.DEFAULT_CALLERS.add("release-verification.yml")
    test_contracts.main()


if __name__ == "__main__":
    main()
