#!/usr/bin/env bash
set -euo pipefail
: "${RELEASE_VERSION:?}" "${RELEASE_OUTPUT_DIR:?}" "${TARGET_SHA:?}"
mkdir -p "$RELEASE_OUTPUT_DIR"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/prodkit-workflows-contracts-$RELEASE_VERSION"
cp -R contracts rulesets templates docs/CONTRACTS.md docs/ADOPTION.md "$tmp/prodkit-workflows-contracts-$RELEASE_VERSION/"
tar -C "$tmp" -czf "$RELEASE_OUTPUT_DIR/prodkit-workflows-contracts-v${RELEASE_VERSION}.tar.gz" "prodkit-workflows-contracts-$RELEASE_VERSION"
