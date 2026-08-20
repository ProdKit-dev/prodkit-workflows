#!/usr/bin/env bash
set -euo pipefail
uv export --frozen --no-dev --no-hashes --format requirements-txt > /tmp/prodkit-security-requirements.txt
uvx pip-audit==2.10.0 -r /tmp/prodkit-security-requirements.txt
