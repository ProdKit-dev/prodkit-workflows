#!/usr/bin/env bash
set -euo pipefail
python3 scripts/check_repository.py

# Validate GitHub Actions semantics with the same pinned Actionlint version used
# across the mature ProdKit repositories. Docker is a required capability of the
# default self-hosted runner profile for this control-plane repository.
docker run --rm \
  -v "$PWD:/repo:ro" \
  --workdir /repo \
  rhysd/actionlint:1.7.12 \
  -color
