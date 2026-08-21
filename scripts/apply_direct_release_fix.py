#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = "fix/direct-release-proof-and-pnpm"
TOKEN = os.environ["GH_TOKEN"]
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
    "User-Agent": "prodkit-workflows-direct-release-fix",
}


def api(method: str, path: str, payload=None, *, allow_404: bool = False):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        headers=HEADERS,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            return None if not raw else json.loads(raw)
    except urllib.error.HTTPError as exc:
        if allow_404 and exc.code == 404:
            return None
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc


def read(path: str):
    ref = urllib.parse.quote(BRANCH, safe="")
    obj = api("GET", f"/repos/{REPO}/contents/{path}?ref={ref}")
    return obj, base64.b64decode(obj["content"]).decode()


def put(path: str, text: str, message: str):
    ref = urllib.parse.quote(BRANCH, safe="")
    current = api("GET", f"/repos/{REPO}/contents/{path}?ref={ref}", allow_404=True)
    if current and base64.b64decode(current["content"]).decode() == text:
        return current
    payload = {
        "message": message,
        "content": base64.b64encode(text.encode()).decode(),
        "branch": BRANCH,
    }
    if current:
        payload["sha"] = current["sha"]
    return api("PUT", f"/repos/{REPO}/contents/{path}", payload)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    existing = api(
        "GET",
        f"/repos/{REPO}/contents/direct-release-fix-result.json?ref={urllib.parse.quote(BRANCH, safe='')}",
        allow_404=True,
    )
    if existing:
        result = json.loads(base64.b64decode(existing["content"]).decode())
        if result.get("state") == "success":
            print("direct-release fix already staged")
            return

    _, workflow = read(".github/workflows/reusable-release.yml")
    workflow = replace_once(
        workflow,
        """      - name: Provision release pnpm\n        if: steps.preflight.outputs.published != 'true' && inputs.node_enabled\n        shell: bash\n        run: npm install --global \"pnpm@${{ inputs.pnpm_version }}\"\n""",
        """      - name: Provision release pnpm\n        if: steps.preflight.outputs.published != 'true' && inputs.node_enabled\n        shell: bash\n        run: |\n          set -euo pipefail\n          corepack enable\n          corepack prepare \"pnpm@${{ inputs.pnpm_version }}\" --activate\n          test \"$(pnpm --version)\" = \"${{ inputs.pnpm_version }}\"\n""",
        "reusable release pnpm provisioning",
    )
    staged = put(
        "staged-reusable-release.yml",
        workflow,
        "chore: stage idempotent reusable release workflow",
    )
    staged_sha = staged["sha"] if "sha" in staged else staged["content"]["sha"]

    _, template = read("templates/caller/release.yml")
    for old, new, label in (
        (
            "      PROOF_WORKFLOW: Trusted Release Proof\n",
            "      PROOF_WORKFLOW_FILE: .github/workflows/trusted-release-proof.yml\n",
            "proof workflow env",
        ),
        (
            '          workflow = os.environ["PROOF_WORKFLOW"]\n',
            '          workflow_file = os.environ["PROOF_WORKFLOW_FILE"]\n',
            "proof workflow variable",
        ),
        (
            '              if run.get("name") == workflow\n',
            '              if run.get("path") == workflow_file\n',
            "proof workflow identity",
        ),
        (
            '                  f"missing successful workflow_dispatch {workflow!r} proof for exact SHA {sha}"\n',
            '                  f"missing successful workflow_dispatch proof from {workflow_file!r} for exact SHA {sha}"\n',
            "proof error message",
        ),
    ):
        template = replace_once(template, old, new, label)
    put("templates/caller/release.yml", template, "fix(release): identify proof by workflow file")

    _, audit = read("scripts/audit_org.py")
    audit = replace_once(
        audit,
        '                if "PROOF_WORKFLOW: Trusted Release Proof" not in text:\n                    errors.append("release.yml must gate on Trusted Release Proof")\n',
        '                if "PROOF_WORKFLOW_FILE: .github/workflows/trusted-release-proof.yml" not in text:\n                    errors.append("release.yml must gate on the Trusted Release Proof workflow file")\n',
        "organization audit proof identity",
    )
    put("scripts/audit_org.py", audit, "fix(audit): require proof workflow-file identity")

    _, tests = read("scripts/test_contracts.py")
    tests = replace_once(
        tests,
        '        if "PROOF_WORKFLOW: Trusted Release Proof" not in release:\n            raise SystemExit("bootstrap Release caller must gate on Trusted Release Proof")\n',
        '        if "PROOF_WORKFLOW_FILE: .github/workflows/trusted-release-proof.yml" not in release:\n            raise SystemExit("bootstrap Release caller must gate on Trusted Release Proof by workflow file")\n        if \'run.get("path") == workflow_file\' not in release:\n            raise SystemExit("bootstrap Release proof lookup must use workflow file identity")\n',
        "bootstrap proof identity test",
    )
    tests = replace_once(
        tests,
        '            "consumer release payload must not use hidden asset names",\n        ),\n        name="Reusable Release",\n    )\n',
        '            "consumer release payload must not use hidden asset names",\n            "corepack prepare",\n            "test \\\"$(pnpm --version)\\\"",\n        ),\n        name="Reusable Release",\n    )\n    if \'npm install --global "pnpm@\' in release:\n        raise SystemExit("Reusable Release must not use global npm pnpm installation on persistent runners")\n',
        "reusable release pnpm regression test",
    )
    tests = replace_once(
        tests,
        '            "PROOF_WORKFLOW: Trusted Release Proof",\n',
        '            "PROOF_WORKFLOW_FILE: .github/workflows/trusted-release-proof.yml",\n',
        "audit contract proof identity test",
    )
    put("scripts/test_contracts.py", tests, "test(release): lock proof identity and Corepack contracts")

    _, docs = read("docs/CONTRACTS.md")
    docs = replace_once(
        docs,
        "The caller performs the explicit exact-SHA `Trusted Release Proof` lookup before delegating to the publisher. The publisher independently requires successful exact-SHA `push` runs for `CI` and `Security`.\n",
        "The caller performs the explicit exact-SHA `Trusted Release Proof` lookup by authoritative workflow-file identity before delegating to the publisher; dynamic `run-name` text is never an authorization identity. The publisher independently requires successful exact-SHA `push` runs for `CI` and `Security`. Release and proof pnpm provisioning both use Corepack so persistent self-hosted runners are idempotent and do not accumulate conflicting global pnpm shims.\n",
        "publication contract documentation",
    )
    put("docs/CONTRACTS.md", docs, "docs(release): define proof identity and pnpm idempotence")

    result = {
        "state": "success",
        "branch": BRANCH,
        "staged_workflow_blob_sha": staged_sha,
        "fixes": [
            "proof workflow-file identity",
            "idempotent Corepack release pnpm",
            "audit and contract regression coverage",
        ],
    }
    put(
        "direct-release-fix-result.json",
        json.dumps(result, indent=2) + "\n",
        "chore: record direct release fix result",
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
