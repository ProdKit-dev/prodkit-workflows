#!/usr/bin/env bash
set -euo pipefail

: "${PRODKIT_CODEQL_SCOPE:?PRODKIT_CODEQL_SCOPE is required}"
: "${PRODKIT_CODEQL_LANGUAGE:?PRODKIT_CODEQL_LANGUAGE is required}"
: "${PRODKIT_CODEQL_OUTPUT_DIR:?PRODKIT_CODEQL_OUTPUT_DIR is required}"
[[ "$PRODKIT_CODEQL_SCOPE" == "language-sarif-v1" ]] || {
  echo "unsupported CodeQL policy scope: $PRODKIT_CODEQL_SCOPE" >&2
  exit 2
}

python3 - "$PRODKIT_CODEQL_LANGUAGE" "$PRODKIT_CODEQL_OUTPUT_DIR" <<'PY'
import json
import pathlib
import sys

language = sys.argv[1]
root = pathlib.Path(sys.argv[2])
files = sorted(root.glob("*.sarif"))
if not files:
    raise SystemExit(f"CodeQL policy failed for {language}: no SARIF files found under {root}")
findings = []
for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "2.1.0" or not isinstance(payload.get("runs"), list):
        raise SystemExit(f"CodeQL policy failed for {language}: invalid SARIF contract in {path}")
    for run in payload["runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("results", []), list):
            raise SystemExit(f"CodeQL policy failed for {language}: invalid SARIF run in {path}")
        findings.extend(run.get("results", []))
if findings:
    raise SystemExit(f"CodeQL policy failed for {language}: {len(findings)} finding(s)")
print(f"CodeQL policy satisfied for {language}: zero findings")
PY
