#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing replacement anchor in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    dispatcher = r'''name: Reusable Release Verification Dispatch

    on:
      workflow_call:
        inputs:
          source_sha:
            description: Exact source SHA published by the parent Release workflow.
            required: true
            type: string
          version:
            description: Canonical SemVer without the v prefix.
            required: true
            type: string
          release_run_id:
            description: Exact parent Release workflow run ID.
            required: true
            type: string
          runner_json:
            description: JSON value accepted by runs-on.
            required: false
            type: string
            default: '"ubuntu-latest"'
          verification_workflow_file:
            description: Dispatch-only verification workflow filename.
            required: false
            type: string
            default: release-verification.yml

    permissions:
      actions: write
      contents: read

    concurrency:
      group: release-verification-dispatch-${{ inputs.source_sha }}
      cancel-in-progress: false

    jobs:
      dispatch:
        name: Dispatch independent verification
        runs-on: ${{ fromJSON(inputs.runner_json) }}
        timeout-minutes: 5
        env:
          SOURCE_SHA: ${{ inputs.source_sha }}
          VERSION: ${{ inputs.version }}
          RELEASE_RUN_ID: ${{ inputs.release_run_id }}
          VERIFICATION_WORKFLOW_FILE: ${{ inputs.verification_workflow_file }}
          GH_TOKEN: ${{ github.token }}
        steps:
          - name: Validate publication handoff and dispatch verification
            shell: bash
            run: |
              set -euo pipefail
              python3 - <<'PY'
              from __future__ import annotations

              import base64
              import json
              import os
              import re
              import urllib.error
              import urllib.parse
              import urllib.request
              from typing import Any

              repo = os.environ["GITHUB_REPOSITORY"]
              token = os.environ["GH_TOKEN"]
              source_sha = os.environ["SOURCE_SHA"]
              version = os.environ["VERSION"]
              release_run_id = os.environ["RELEASE_RUN_ID"]
              verification_file = os.environ["VERIFICATION_WORKFLOW_FILE"]
              root = f"https://api.github.com/repos/{repo}"
              headers = {
                  "Authorization": f"Bearer {token}",
                  "Accept": "application/vnd.github+json",
                  "X-GitHub-Api-Version": "2022-11-28",
                  "User-Agent": "prodkit-workflows-release-verification-dispatch",
              }
              semver = re.compile(
                  r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
                  r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
              )

              class ApiError(RuntimeError):
                  def __init__(self, status: int, body: str) -> None:
                      super().__init__(f"GitHub API {status}: {body}")
                      self.status = status
                      self.body = body

              def api(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
                  raw = None if payload is None else json.dumps(payload).encode()
                  request = urllib.request.Request(
                      root + path,
                      data=raw,
                      method=method,
                      headers={**headers, **({"Content-Type": "application/json"} if raw else {})},
                  )
                  try:
                      with urllib.request.urlopen(request, timeout=120) as response:
                          body = response.read()
                          return None if not body else json.loads(body)
                  except urllib.error.HTTPError as exc:
                      body = exc.read().decode(errors="replace")
                      raise ApiError(exc.code, body) from exc

              if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
                  raise SystemExit("source_sha must be an exact lowercase 40-character commit SHA")
              if not semver.fullmatch(version):
                  raise SystemExit("version must be canonical SemVer")
              if not re.fullmatch(r"[1-9][0-9]*", release_run_id):
                  raise SystemExit("release_run_id must be a positive integer string")
              if not re.fullmatch(r"[A-Za-z0-9._-]+\.ya?ml", verification_file):
                  raise SystemExit("verification_workflow_file must be a workflow filename")

              run = api("GET", f"/actions/runs/{release_run_id}")
              if run.get("path") != ".github/workflows/release.yml":
                  raise SystemExit("release_run_id does not identify the canonical Release workflow")
              if run.get("event") != "workflow_dispatch" or run.get("head_sha") != source_sha:
                  raise SystemExit("release_run_id is not bound to the exact dispatched source")
              if run.get("status") == "completed" and run.get("conclusion") != "success":
                  raise SystemExit("parent Release workflow already completed unsuccessfully")
              if run.get("status") not in {"in_progress", "completed"}:
                  raise SystemExit(f"parent Release workflow is not in a dispatchable state: {run.get('status')}")

              tag = f"v{version}"
              ref = api("GET", f"/git/ref/tags/{urllib.parse.quote(tag, safe='')}")
              obj = ref["object"]
              seen: set[str] = set()
              while obj.get("type") == "tag":
                  sha = str(obj["sha"])
                  if sha in seen:
                      raise SystemExit("tag object cycle detected")
                  seen.add(sha)
                  obj = api("GET", f"/git/tags/{sha}")["object"]
              if obj.get("type") != "commit" or obj.get("sha") != source_sha:
                  raise SystemExit(f"immutable tag {tag} does not resolve to {source_sha}")

              release = api("GET", f"/releases/tags/{urllib.parse.quote(tag, safe='')}")
              if release.get("draft") is not False or str(release.get("target_commitish")) != source_sha:
                  raise SystemExit("published Release is not bound to the exact source")

              quoted = urllib.parse.quote(f".github/workflows/{verification_file}", safe="/")
              caller = api("GET", f"/contents/{quoted}?ref={urllib.parse.quote(source_sha, safe='')}")
              if caller.get("type") != "file" or caller.get("encoding") != "base64":
                  raise SystemExit("verification caller is not a source file")
              text = base64.b64decode(caller["content"]).decode()
              if "workflow_dispatch:" not in text or "workflow_run:" in text:
                  raise SystemExit("verification caller must be workflow_dispatch-only")
              if "source_sha: ${{ github.sha }}" not in text:
                  raise SystemExit("verification caller must derive source_sha from dispatched ref")

              query = urllib.parse.urlencode({"head_sha": source_sha, "event": "workflow_dispatch", "per_page": 100})
              runs = list(api("GET", f"/actions/runs?{query}").get("workflow_runs", []))
              expected_path = f".github/workflows/{verification_file}"
              verification_runs = [
                  item for item in runs
                  if item.get("path") == expected_path
                  and item.get("head_sha") == source_sha
                  and item.get("event") == "workflow_dispatch"
              ]
              successful = [
                  item for item in verification_runs
                  if item.get("status") == "completed" and item.get("conclusion") == "success"
              ]
              if successful:
                  selected = max(successful, key=lambda item: int(item["id"]))
                  print(f"successful exact-source verification already exists: {selected.get('html_url')}")
                  raise SystemExit(0)
              active = [
                  item for item in verification_runs
                  if item.get("status") in {"queued", "in_progress", "pending"}
              ]
              if active:
                  selected = max(active, key=lambda item: int(item["id"]))
                  print(f"active exact-source verification already exists: {selected.get('html_url')}")
                  raise SystemExit(0)

              api(
                  "POST",
                  f"/actions/workflows/{urllib.parse.quote(verification_file, safe='')}/dispatches",
                  {"ref": tag, "inputs": {"release_run_id": release_run_id}},
              )
              print(
                  f"dispatched {verification_file} at immutable {tag} for {source_sha}; "
                  "parent Release exits without waiting"
              )
              PY
    '''
    (ROOT / ".github/workflows/reusable-release-verification-dispatch.yml").write_text(
        textwrap.dedent(dispatcher), encoding="utf-8"
    )

    final_ci = '''name: CI

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: prodkit-control-plane-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    name: ci
    uses: ./.github/workflows/reusable-ci-compact.yml
    with:
      runner_json: '\"ubuntu-latest\"'
      hygiene_enabled: true
      python_enabled: false
      node_enabled: false
      postgres_enabled: false
      container_enabled: false
      custom_enabled: true
      custom_script: .prodkit/workflows/ci-custom.sh
'''
    (ROOT / ".github/workflows/ci.yml").write_text(final_ci, encoding="utf-8")

    release_self = '''name: Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: SemVer without v prefix
        required: true
        type: string
      prerelease:
        description: Mark as prerelease
        required: true
        type: boolean
        default: false

permissions:
  contents: write
  actions: read
  id-token: write
  attestations: write
  artifact-metadata: write

jobs:
  release:
    name: release
    uses: ./.github/workflows/reusable-release.yml
    with:
      version: ${{ inputs.version }}
      target_sha: ${{ github.sha }}
      prerelease: ${{ inputs.prerelease }}
      runner_json: '\"ubuntu-latest\"'
      proof_workflow_file: .github/workflows/trusted-release-proof.yml
      reuse_proof_payload: true
      environment: release

  verification-dispatch:
    name: dispatch verification
    needs: release
    permissions:
      actions: write
      contents: read
    uses: ./.github/workflows/reusable-release-verification-dispatch.yml
    with:
      source_sha: ${{ github.sha }}
      version: ${{ inputs.version }}
      release_run_id: ${{ github.run_id }}
      runner_json: '\"ubuntu-latest\"'
      verification_workflow_file: release-verification.yml
'''
    (ROOT / ".github/workflows/release.yml").write_text(release_self, encoding="utf-8")

    verification_self = '''name: Release Verification

run-name: Release Verification — ${{ github.sha }}

on:
  workflow_dispatch:
    inputs:
      release_run_id:
        description: Exact parent Release run ID; leave blank only for manual re-verification after Release completed
        required: false
        type: string
        default: ""

permissions:
  actions: read
  contents: read

jobs:
  verification:
    name: verification
    uses: ./.github/workflows/reusable-release-verification.yml
    with:
      source_sha: ${{ github.sha }}
      release_run_id: ${{ inputs.release_run_id }}
      runner_json: '\"ubuntu-latest\"'
      manifest_path: .prodkit/release.json
      release_workflow_file: release.yml
'''
    (ROOT / ".github/workflows/release-verification.yml").write_text(verification_self, encoding="utf-8")

    release_template = '''name: Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: SemVer without v prefix
        required: true
        type: string
      prerelease:
        required: true
        type: boolean
        default: false

permissions:
  contents: write
  actions: read
  id-token: write
  attestations: write
  artifact-metadata: write

jobs:
  release:
    name: release
    uses: WORKFLOWS_REPOSITORY/.github/workflows/reusable-release.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA
    with:
      version: ${{ inputs.version }}
      target_sha: ${{ github.sha }}
      prerelease: ${{ inputs.prerelease }}
      runner_json: ${{ vars.PRODKIT_RUNNER_JSON != '' && vars.PRODKIT_RUNNER_JSON || '["self-hosted","Linux","X64"]' }}
      required_workflows_json: '["CI","Security"]'
      proof_workflow_file: .github/workflows/trusted-release-proof.yml
      reuse_proof_payload: true
      python_enabled: true
      python_version: "3.12"
      uv_version: "0.10.0"
      node_enabled: true
      node_version: "24"
      pnpm_version: "11.21.0"
      environment: release

  verification-dispatch:
    name: dispatch verification
    needs: release
    permissions:
      actions: write
      contents: read
    uses: WORKFLOWS_REPOSITORY/.github/workflows/reusable-release-verification-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA
    with:
      source_sha: ${{ github.sha }}
      version: ${{ inputs.version }}
      release_run_id: ${{ github.run_id }}
      runner_json: '\"ubuntu-latest\"'
      verification_workflow_file: release-verification.yml
'''
    (ROOT / "templates/caller/release.yml").write_text(release_template, encoding="utf-8")

    verification_template = '''name: Release Verification

run-name: Release Verification — ${{ github.sha }}

on:
  workflow_dispatch:
    inputs:
      release_run_id:
        description: Exact parent Release run ID; leave blank only for manual re-verification after Release completed
        required: false
        type: string
        default: ""

permissions:
  actions: read
  contents: read

jobs:
  verification:
    name: verification
    uses: WORKFLOWS_REPOSITORY/.github/workflows/reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA
    with:
      source_sha: ${{ github.sha }}
      release_run_id: ${{ inputs.release_run_id }}
      runner_json: ${{ vars.PRODKIT_RUNNER_JSON != '' && vars.PRODKIT_RUNNER_JSON || '["self-hosted","Linux","X64"]' }}
      manifest_path: .prodkit/release.json
      release_workflow_file: release.yml
'''
    (ROOT / "templates/caller/release-verification.yml").write_text(verification_template, encoding="utf-8")

    replace(
        ".github/workflows/reusable-release-verification.yml",
        "      release_workflow_file:\n        required: false\n        type: string\n        default: release.yml\n",
        "      release_workflow_file:\n        required: false\n        type: string\n        default: release.yml\n      release_run_id:\n        description: Optional exact parent Release run ID for automatic verification handoff.\n        required: false\n        type: string\n        default: \"\"\n",
    )
    replace(
        ".github/workflows/reusable-release-verification.yml",
        "      RELEASE_WORKFLOW_FILE: ${{ inputs.release_workflow_file }}\n      GH_TOKEN: ${{ github.token }}\n",
        "      RELEASE_WORKFLOW_FILE: ${{ inputs.release_workflow_file }}\n      RELEASE_RUN_ID: ${{ inputs.release_run_id }}\n      GH_TOKEN: ${{ github.token }}\n",
    )
    old_block = '''          query = urllib.parse.urlencode(
              {"head_sha": source_sha, "event": "workflow_dispatch", "status": "completed", "per_page": 100}
          )
          runs = list(api(f"/actions/runs?{query}").get("workflow_runs", []))
          expected_path = f".github/workflows/{release_workflow_file}"
          successful_release_runs = [
              run
              for run in runs
              if run.get("path") == expected_path
              and run.get("head_sha") == source_sha
              and run.get("event") == "workflow_dispatch"
              and run.get("status") == "completed"
              and run.get("conclusion") == "success"
          ]
          if not successful_release_runs:
              raise SystemExit("missing successful exact-source Release workflow run")
'''
    new_block = '''          expected_path = f".github/workflows/{release_workflow_file}"
          release_run_id = os.environ.get("RELEASE_RUN_ID", "").strip()
          if release_run_id:
              if not re.fullmatch(r"[1-9][0-9]*", release_run_id):
                  raise SystemExit("release_run_id must be a positive integer string")
              parent = api(f"/actions/runs/{release_run_id}")
              if parent.get("path") != expected_path:
                  raise SystemExit("release_run_id does not identify the canonical Release workflow")
              if parent.get("head_sha") != source_sha or parent.get("event") != "workflow_dispatch":
                  raise SystemExit("release_run_id is not bound to the exact dispatched source")
              if parent.get("status") == "completed" and parent.get("conclusion") != "success":
                  raise SystemExit("parent Release workflow completed unsuccessfully")
              if parent.get("status") not in {"in_progress", "completed"}:
                  raise SystemExit(f"parent Release workflow has unexpected status: {parent.get('status')}")
              successful_release_runs = [parent]
          else:
              query = urllib.parse.urlencode(
                  {"head_sha": source_sha, "event": "workflow_dispatch", "status": "completed", "per_page": 100}
              )
              runs = list(api(f"/actions/runs?{query}").get("workflow_runs", []))
              successful_release_runs = [
                  run
                  for run in runs
                  if run.get("path") == expected_path
                  and run.get("head_sha") == source_sha
                  and run.get("event") == "workflow_dispatch"
                  and run.get("status") == "completed"
                  and run.get("conclusion") == "success"
              ]
              if not successful_release_runs:
                  raise SystemExit("missing successful exact-source Release workflow run")
'''
    replace(".github/workflows/reusable-release-verification.yml", old_block, new_block)

    audit_path = ROOT / "scripts/audit_org.py"
    audit = audit_path.read_text(encoding="utf-8")
    old_release_audit = '''            if filename == "release.yml":
                if "target_sha: ${{ github.sha }}" not in text:
                    errors.append("release.yml must publish the dispatched current-main SHA")
                if "proof_workflow_file: .github/workflows/trusted-release-proof.yml" not in text:
                    errors.append("release.yml must delegate Trusted Release Proof authorization centrally")
                if "proof-gate:" in text or "urllib.request" in text:
                    errors.append("release.yml must not duplicate central proof-gate implementation")
                for pattern in direct_release_patterns:
'''
    new_release_audit = '''            if filename == "release.yml":
                if "target_sha: ${{ github.sha }}" not in text:
                    errors.append("release.yml must publish the dispatched current-main SHA")
                if "proof_workflow_file: .github/workflows/trusted-release-proof.yml" not in text:
                    errors.append("release.yml must delegate Trusted Release Proof authorization centrally")
                dispatcher = f"{args.workflows_repository}/.github/workflows/reusable-release-verification-dispatch.yml@{args.required_sha}"
                for fragment in (
                    dispatcher,
                    "verification-dispatch:",
                    "needs: release",
                    "actions: write",
                    "source_sha: ${{ github.sha }}",
                    "release_run_id: ${{ github.run_id }}",
                    "verification_workflow_file: release-verification.yml",
                ):
                    if fragment not in text:
                        errors.append(f"release.yml missing independent verification dispatch contract: {fragment}")
                if "proof-gate:" in text or "urllib.request" in text:
                    errors.append("release.yml must not duplicate central proof-gate implementation")
                for pattern in direct_release_patterns:
'''
    if old_release_audit not in audit:
        raise SystemExit("audit release anchor missing")
    audit = audit.replace(old_release_audit, new_release_audit, 1)
    old_verification_audit = '''            if filename == "release-verification.yml":
                if "workflow_run:" not in text or 'workflows: ["Release"]' not in text:
                    errors.append("release-verification.yml must run after Release completion")
                if "actions: write" in text or "contents: write" in text:
                    errors.append("release-verification.yml must remain read-only")
'''
    new_verification_audit = '''            if filename == "release-verification.yml":
                if workflow_events(text) != {"workflow_dispatch"}:
                    errors.append("release-verification.yml must be workflow_dispatch-only")
                if "source_sha: ${{ github.sha }}" not in text:
                    errors.append("release-verification.yml must derive source from the dispatched immutable ref")
                if "release_run_id: ${{ inputs.release_run_id }}" not in text:
                    errors.append("release-verification.yml must forward the parent Release run identity")
                if "actions: write" in text or "contents: write" in text:
                    errors.append("release-verification.yml must remain read-only")
'''
    if old_verification_audit not in audit:
        raise SystemExit("audit verification anchor missing")
    audit_path.write_text(audit.replace(old_verification_audit, new_verification_audit, 1), encoding="utf-8")

    contracts_path = ROOT / "scripts/test_contracts_current.py"
    contracts = contracts_path.read_text(encoding="utf-8")
    contracts = contracts.replace(
        '            "reusable-release-verification.yml",\n',
        '            "reusable-release-verification.yml",\n            "reusable-release-verification-dispatch.yml",\n',
        1,
    )
    anchor = '''    require(
        ".github/workflows/release-verification.yml",
        "uses: ./.github/workflows/reusable-release-verification.yml",
        "control-plane release verification",
    )
'''
    addition = anchor + '''    require(
        ".github/workflows/release.yml",
        "uses: ./.github/workflows/reusable-release-verification-dispatch.yml",
        "control-plane verification dispatch",
    )
    require(
        "templates/caller/release.yml",
        "reusable-release-verification-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "generated verification dispatch",
    )
    require(
        "templates/caller/release-verification.yml",
        "workflow_dispatch:",
        "generated verification dispatch boundary",
    )
    reject(
        "templates/caller/release-verification.yml",
        "workflow_run:",
        "generated verification must not depend on workflow_run chaining",
    )
    require(
        "templates/caller/release-verification.yml",
        "source_sha: ${{ github.sha }}",
        "generated immutable-ref verification source",
    )
    dispatcher = ".github/workflows/reusable-release-verification-dispatch.yml"
    for fragment in (
        "workflow_call:",
        "actions: write",
        "release_run_id:",
        "verification_workflow_file:",
        "immutable tag",
        "verification caller must be workflow_dispatch-only",
        '"ref": tag',
        '"release_run_id": release_run_id',
        "/dispatches",
        "successful exact-source verification already exists",
        "active exact-source verification already exists",
    ):
        require(dispatcher, fragment, "reusable verification dispatcher")
    reject(dispatcher, "time.sleep(", "verification dispatcher must not wait for child")
'''
    if anchor not in contracts:
        raise SystemExit("test_contracts_current verification anchor missing")
    contracts_path.write_text(contracts.replace(anchor, addition, 1), encoding="utf-8")

    lifecycle_test_path = ROOT / "scripts/test_release_lifecycle.py"
    lifecycle_test = lifecycle_test_path.read_text(encoding="utf-8")
    lifecycle_test = lifecycle_test.replace(
        '    verification = text(".github/workflows/reusable-release-verification.yml")\n',
        '    verification = text(".github/workflows/reusable-release-verification.yml")\n    verification_dispatch = text(".github/workflows/reusable-release-verification-dispatch.yml")\n',
        1,
    )
    old_template_test = '''    for needle in (
        "workflow_run:",
        'workflows: ["Release"]',
        "reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "workflow_run.head_sha",
    ):
        require(verification_template, needle, "release verification caller template")
'''
    new_template_test = '''    for needle in (
        "workflow_dispatch:",
        "reusable-release-verification.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "source_sha: ${{ github.sha }}",
        "release_run_id: ${{ inputs.release_run_id }}",
    ):
        require(verification_template, needle, "release verification caller template")
    reject(verification_template, "workflow_run:", "release verification caller chain-depth safety")

    for needle in (
        "actions: write",
        "release_run_id:",
        "verification_workflow_file:",
        '"ref": tag',
        '"release_run_id": release_run_id',
        "/dispatches",
        "verification caller must be workflow_dispatch-only",
    ):
        require(verification_dispatch, needle, "reusable verification dispatch")
    reject(verification_dispatch, "time.sleep(", "reusable verification dispatch")
    for needle in (
        "verification-dispatch:",
        "needs: release",
        "reusable-release-verification-dispatch.yml@REPLACE_WITH_PRODKIT_WORKFLOWS_SHA",
        "release_run_id: ${{ github.run_id }}",
    ):
        require(release_template, needle, "release verification dispatch handoff")
'''
    if old_template_test not in lifecycle_test:
        raise SystemExit("release lifecycle verification template anchor missing")
    lifecycle_test = lifecycle_test.replace(old_template_test, new_template_test, 1)
    lifecycle_test = lifecycle_test.replace(
        '    for forbidden in ("actions: write", "contents: write", "time.sleep(", "while time.time()"):\n        reject(verification, forbidden, "reusable release verification")\n',
        '    for forbidden in ("actions: write", "contents: write", "time.sleep(", "while time.time()"):\n        reject(verification, forbidden, "reusable release verification")\n    require(verification, "release_run_id:", "reusable release parent-run handoff")\n    require(verification, "parent Release workflow", "reusable release parent-run validation")\n',
        1,
    )
    lifecycle_test = lifecycle_test.replace(
        '    require(lifecycle, "proof-completion boundary", "lifecycle documentation")\n',
        '    require(lifecycle, "proof-completion boundary", "lifecycle documentation")\n    require(lifecycle, "verification-dispatch boundary", "lifecycle documentation")\n',
        1,
    )
    lifecycle_test = lifecycle_test.replace(
        '    require(contracts, "proof-produced", "consumer contracts")\n',
        '    require(contracts, "proof-produced", "consumer contracts")\n    require(contracts, "verification-dispatch boundary", "consumer contracts")\n',
        1,
    )
    lifecycle_test = lifecycle_test.replace(
        '    require(readme, "proof-produced", "README")\n',
        '    require(readme, "proof-produced", "README")\n    require(readme, "verification-dispatch boundary", "README")\n',
        1,
    )
    lifecycle_test_path.write_text(lifecycle_test, encoding="utf-8")

    lifecycle_path = ROOT / "docs/LIFECYCLE.md"
    lifecycle = lifecycle_path.read_text(encoding="utf-8")
    lifecycle = lifecycle.replace(
        '| Verification | `workflow_run` after Release | Independently verify immutable publication | exact tag/source/metadata/assets/checksums |',
        '| Verification | `workflow_dispatch` on immutable release tag | Independently verify immutable publication without chained-workflow suppression | exact tag/source/metadata/assets/checksums |',
    )
    lifecycle = lifecycle.replace(
        '7. `workflow_run` starts independent verification only after Release has completed.',
        '7. Release finishes publication, then a short GitHub-hosted verification-dispatch job validates the immutable tag/source handoff and dispatches `Release Verification` at that immutable tag without waiting for the child. This **verification-dispatch boundary** avoids GitHub’s chained `workflow_run` depth limit.',
    )
    lifecycle = lifecycle.replace(
        'The generated `Release Verification` caller listens for completion of the repository `Release` workflow and invokes `reusable-release-verification.yml` only for successful workflow-dispatch publication runs.\n\nVerification is read-only.',
        'The generated `Release Verification` caller is `workflow_dispatch` only. The parent Release workflow invokes `reusable-release-verification-dispatch.yml` after publication succeeds; the dispatcher validates the exact parent Release run, immutable `vX.Y.Z` tag and published target, then dispatches verification on that tag and exits immediately. The verification caller derives `source_sha` from `${{ github.sha }}` at the immutable tag and forwards only the parent Release run ID for provenance binding.\n\nThis **verification-dispatch boundary** avoids another chained `workflow_run` hop. Verification is read-only.',
    )
    lifecycle = lifecycle.replace(
        'Because verification begins only after Release completes, it cannot hold the runner needed by publication.',
        'Because verification is dispatched only after the reusable publication job succeeds, and the dispatcher itself is short and non-blocking, it cannot hold the runner needed by publication or wait on the verification child.',
    )
    lifecycle_path.write_text(lifecycle, encoding="utf-8")

    contracts_doc = ROOT / "docs/CONTRACTS.md"
    contracts_text = contracts_doc.read_text(encoding="utf-8")
    contracts_text = contracts_text.replace(
        '- `reusable-release-verification.yml`;\n',
        '- `reusable-release-verification.yml`;\n- `reusable-release-verification-dispatch.yml`;\n',
        1,
    )
    old_lifecycle = '''5. **Publication** — Release imports the exact proof-produced payload, seals it with central evidence, and publishes it without rebuilding the repository payload.
6. **Verification** — `Release Verification` independently checks the immutable published transaction.
7. **Cleanup** — after merge/release closure, either explicitly dispatch Branch Cleanup against exact stale branch names or activate the dormant Post-Gate Branch Cleanup caller with a reviewed exact branch list. Both routes end at the same dispatch-only, exact-SHA-bound deletion engine and never move tags/releases.
8. **Metadata repair** — independently reconcile mutable Release name/body while proving immutable source/payload identity is unchanged.
'''
    new_lifecycle = '''5. **Publication** — Release imports the exact proof-produced payload, seals it with central evidence, and publishes it without rebuilding the repository payload.
6. **Verification dispatch** — after publication succeeds, Release calls the bounded verification dispatcher, which validates the exact parent run and immutable tag then triggers `Release Verification` with `workflow_dispatch` on that tag and exits. This **verification-dispatch boundary** avoids chained-`workflow_run` suppression.
7. **Verification** — dispatch-only, read-only `Release Verification` independently checks the immutable published transaction.
8. **Cleanup** — after merge/release closure, either explicitly dispatch Branch Cleanup against exact stale branch names or activate the dormant Post-Gate Branch Cleanup caller with a reviewed exact branch list. Both routes end at the same dispatch-only, exact-SHA-bound deletion engine and never move tags/releases.
9. **Metadata repair** — independently reconcile mutable Release name/body while proving immutable source/payload identity is unchanged.
'''
    if old_lifecycle not in contracts_text:
        raise SystemExit("contracts lifecycle anchor missing")
    contracts_doc.write_text(contracts_text.replace(old_lifecycle, new_lifecycle, 1), encoding="utf-8")

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "## v0.1.3 verification-dispatch boundary" not in readme:
        readme += '''\n## v0.1.3 verification-dispatch boundary\n\nRelease verification no longer depends on a fourth chained `workflow_run`. After publication succeeds, Release calls a short reusable verification dispatcher that validates the exact parent Release run and immutable `vX.Y.Z` source, dispatches read-only `Release Verification` with `workflow_dispatch` on that tag, and exits without waiting. This preserves independent verification while avoiding GitHub workflow-chain depth suppression.\n'''
    readme_path.write_text(readme, encoding="utf-8")

    adoption_path = ROOT / "docs/ADOPTION.md"
    adoption = adoption_path.read_text(encoding="utf-8")
    if "## Verification dispatch" not in adoption:
        adoption += '''\n## Verification dispatch\n\nAfter `Release` publishes successfully, do not manually start the normal verification path. Release automatically dispatches `Release Verification` on the immutable release tag through the central verification-dispatch boundary. Manual `Release Verification` dispatch is recovery-only; select the immutable `vX.Y.Z` tag and leave `release_run_id` empty after the parent Release has completed.\n'''
    adoption_path.write_text(adoption, encoding="utf-8")

    (ROOT / "VERSION").write_text("0.1.3\n", encoding="utf-8")
    changelog_path = ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    if "## [0.1.3] - 2026-08-23" not in changelog:
        insertion = '''## [0.1.3] - 2026-08-23

- Fix automatic post-publication verification so it cannot be suppressed by GitHub's chained `workflow_run` depth limit.
- Add `reusable-release-verification-dispatch.yml`; Release invokes it only after publication succeeds, and it validates the exact parent Release run, immutable tag/source identity, and dispatch-only verification caller before triggering verification.
- Make generated `Release Verification` callers `workflow_dispatch` only, derive the source from `${{ github.sha }}` on the immutable tag, and remain read-only.
- Bind automatic verification to the exact parent Release run ID while preserving source identity without a manually copied SHA and manual recovery after a completed Release.
- Keep verification dispatch non-blocking and GitHub-hosted so it never waits while occupying a trusted product runner.
- Update organization audit, contract tests, lifecycle documentation, generated callers and release notes to enforce the verification-dispatch boundary.
- Keep the immutable `v0.1.2` release unchanged; v0.1.3 is the patch-level lifecycle correction discovered during v0.1.2 closure.

'''
        changelog_path.write_text(
            changelog.replace("## [0.1.2] - 2026-08-23\n", insertion + "## [0.1.2] - 2026-08-23\n", 1),
            encoding="utf-8",
        )

    notes = '''# ProdKit Workflows v0.1.3

`v0.1.3` corrects the post-publication verification trigger topology discovered while closing v0.1.2. GitHub limits chained `workflow_run` depth, so the previous Proof → Promotion → Release → Verification topology could suppress the final verifier even when publication succeeded.

## Outcome

Release verification is explicitly dispatched on the immutable release tag after publication succeeds. The verifier remains a separate, read-only workflow and continues to validate exact source, tag, metadata, assets and checksums.

## Verification-dispatch boundary

Release gains a short `verification-dispatch` job after the reusable publisher. It passes the exact `${{ github.sha }}`, SemVer and `${{ github.run_id }}` to `reusable-release-verification-dispatch.yml`. The dispatcher verifies the parent run identity, immutable `vX.Y.Z` tag and published target, validates that the repository verification caller is `workflow_dispatch` only and source-bound to `${{ github.sha }}`, avoids duplicate active/successful verification runs, then dispatches verification on the immutable tag and exits without waiting.

`Release Verification` accepts no manually copied source SHA. Automatic dispatch forwards only the parent Release run ID. Manual recovery may leave that run ID empty after Release has completed; the verifier then requires an already-completed successful exact-source Release run.

## Compatibility

Consumers pinned to v0.1.2 keep their immutable behavior. Consumers adopting v0.1.3 should repin the complete generated workflow family to the exact v0.1.3 release commit SHA so Release and Release Verification move together.
'''
    (ROOT / "docs/V0.1.3.md").write_text(notes, encoding="utf-8")

    for transient in (
        ".github/workflows/ops-apply-v0.1.3.yml",
        ".prodkit/v0.1.3-staging-trigger",
        "scripts/apply_v013.py",
    ):
        path = ROOT / transient
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    main()
