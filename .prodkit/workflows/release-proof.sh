#!/usr/bin/env bash
set -euo pipefail

version="$(tr -d '\r\n' < VERSION)"
python3 scripts/validate_release_manifest.py "$version" --root .

test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
