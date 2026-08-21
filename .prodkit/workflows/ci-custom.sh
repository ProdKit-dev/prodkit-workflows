#!/usr/bin/env bash
set -euo pipefail
python3 scripts/test_contracts.py
python3 scripts/test_release_metadata_compat.py
python3 scripts/test_release_lifecycle.py
