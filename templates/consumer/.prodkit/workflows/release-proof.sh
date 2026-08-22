#!/usr/bin/env bash
set -euo pipefail

: "${SOURCE_SHA:?SOURCE_SHA is required}"
: "${PRODKIT_PROOF_OUTPUT_DIR:?PRODKIT_PROOF_OUTPUT_DIR is required}"

# Permanent exact-SHA CI and Security are verified by the reusable proof workflow.
# Do not rerun CI/Security matrices here. This adapter is only for acceptance that
# is genuinely specific to promotion/release and is not already represented by
# permanent CI/Security evidence.
#
# Examples a repository may add here:
# - production-container runtime smoke tests;
# - release-only browser/extension acceptance;
# - migration acceptance not already present in permanent CI;
# - release-policy checks that depend on the exact version candidate.
#
# The reusable proof workflow executes the repository-owned release-build adapter
# once after this script and stores the promotable payload in the proof artifact.
# The Release workflow consumes that exact payload instead of rebuilding it.

mkdir -p "$PRODKIT_PROOF_OUTPUT_DIR"
printf 'release-specific acceptance adapter completed for %s\n' "$SOURCE_SHA" \
  > "$PRODKIT_PROOF_OUTPUT_DIR/release-specific-acceptance.txt"
