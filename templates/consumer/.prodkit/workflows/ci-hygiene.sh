#!/usr/bin/env bash
set -euo pipefail
# Repository-specific structural checks.
python3 scripts/check_repository_hygiene.py
