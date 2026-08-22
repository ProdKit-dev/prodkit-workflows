#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = (
    (ROOT / ".github/workflows/reusable-ci-compact.yml", "CI"),
    (ROOT / ".github/workflows/reusable-security-compact.yml", "Security"),
)

for path, label in CASES:
    text = path.read_text(encoding="utf-8")
    required = f"- name: Verify {label} contract\n        if: always() && !cancelled()"
    legacy = f"- name: Verify {label} contract\n        if: always()\n"
    if required not in text:
        raise SystemExit(f"{path.name}: aggregate verifier must skip cancelled workflow runs")
    if legacy in text:
        raise SystemExit(f"{path.name}: legacy always() cancellation-poisoning verifier remains")

print("compact cancellation diagnostics contract passed")
