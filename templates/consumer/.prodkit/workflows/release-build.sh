#!/usr/bin/env bash
set -euo pipefail
: "${RELEASE_VERSION:?}" "${RELEASE_OUTPUT_DIR:?}" "${TARGET_SHA:?}"
mkdir -p "$RELEASE_OUTPUT_DIR"
# Build all registry/GitHub release payloads from the checked-out exact SHA.
# Examples:
# uv build --package your-package --out-dir "$RELEASE_OUTPUT_DIR"
# pnpm --filter @your/package pack --pack-destination "$RELEASE_OUTPUT_DIR"
