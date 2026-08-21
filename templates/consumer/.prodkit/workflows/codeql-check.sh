#!/usr/bin/env bash
set -euo pipefail

: "${PRODKIT_CODEQL_OUTPUT_DIR:?PRODKIT_CODEQL_OUTPUT_DIR is required}"
python3 - "$PRODKIT_CODEQL_OUTPUT_DIR" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
files = sorted(root.glob("*.sarif"))
if not files:
    raise SystemExit(f"no SARIF files found under {root}")
findings = []
for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for run in payload.get("runs", []):
        findings.extend(run.get("results", []))
if findings:
    raise SystemExit(f"CodeQL reported {len(findings)} finding(s)")
print("CodeQL policy satisfied: zero findings")
PY
