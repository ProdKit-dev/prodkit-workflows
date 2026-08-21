#!/usr/bin/env bash
set -euo pipefail
python3 scripts/test_contracts_current.py
python3 scripts/test_release_metadata_compat.py
python3 scripts/test_release_lifecycle.py
