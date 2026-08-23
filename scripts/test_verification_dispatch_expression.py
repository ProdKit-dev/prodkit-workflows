#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reusable-release-verification-dispatch.yml"


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    run_block = text.split("        run: |", 1)[1]
    if 'expected_source_contract = "source_sha: $" + "{{ github.sha }}"' not in run_block:
        raise AssertionError("verification dispatcher must construct the github.sha contract at runtime")
    if 'if "source_sha: ${{ github.sha }}" not in text:' in run_block:
        raise AssertionError("github.sha contract must not be embedded as an interpolated Actions expression")
    print("verification dispatch expression contract passed")


if __name__ == "__main__":
    main()
