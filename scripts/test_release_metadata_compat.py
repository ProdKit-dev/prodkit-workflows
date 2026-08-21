#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
metadata = (root / ".github/workflows/reusable-release-metadata.yml").read_text()
release = (root / ".github/workflows/reusable-release.yml").read_text()

required = (
    'LEGACY_TRANSPORT_ALIASES = {".gitignore": "default.gitignore"}',
    "resolved_assets = {}",
    "consumed_remote_names = {\"SHA256SUMS\"}",
    "legacy transport-normalized release asset",
    "asset = resolved_assets[name]",
)
for fragment in required:
    if fragment not in metadata:
        raise SystemExit(f"release metadata compatibility contract missing: {fragment}")

if "consumer release payload must not use hidden asset names" not in release:
    raise SystemExit("legacy verification compatibility must not weaken hidden-asset publication guard")

# The compatibility exception must remain singular and explicit rather than
# becoming a general hidden-name rewriting mechanism.
if metadata.count("LEGACY_TRANSPORT_ALIASES") != 2:
    raise SystemExit("legacy transport alias must remain a single narrowly scoped mapping")

print("legacy hidden release-asset verification contract satisfied")
