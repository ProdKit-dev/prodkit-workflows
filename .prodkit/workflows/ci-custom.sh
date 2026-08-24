#!/usr/bin/env bash
set -euo pipefail
python3 scripts/test_contracts_current.py
python3 scripts/test_release_metadata_compat.py
python3 scripts/test_release_lifecycle.py
python3 scripts/test_cancelled_diagnostics.py
python3 scripts/test_verification_dispatch_expression.py
python3 scripts/test_release_proof_dispatch.py
python3 scripts/test_release_verification_cleanup.py
