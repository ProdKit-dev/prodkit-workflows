#!/usr/bin/env bash
set -euo pipefail
: "${PRODKIT_SECURITY_IMAGE:?}"
docker build --pull -t "$PRODKIT_SECURITY_IMAGE" .
