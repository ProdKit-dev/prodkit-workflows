#!/usr/bin/env bash
set -euo pipefail

bash .prodkit/workflows/ci-hygiene.sh

for python_version in 3.12 3.13 3.14; do
  PRODKIT_PYTHON_VERSION="$python_version" bash .prodkit/workflows/ci-python.sh
done

for node_version in 22 24; do
  PRODKIT_NODE_VERSION="$node_version" bash .prodkit/workflows/ci-node.sh
done

bash .prodkit/workflows/security-python.sh
bash .prodkit/workflows/security-node.sh
bash .prodkit/workflows/security-custom.sh

# Repositories with browser, database, container, packaging, or other release-specific
# acceptance requirements should extend this adapter. The reusable workflow owns
# exact-SHA checkout, current-main verification, source immutability, receipt creation,
# and proof artifact upload.
