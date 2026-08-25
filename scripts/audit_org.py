#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


def api(url: str, token: str) -> tuple[Any, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prodkit-workflows-audit",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response), response.headers
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, {}
        raise


def file_text(repo: str, path: str, token: str) -> str | None:
    obj, _ = api(f"https://api.github.com/repos/{repo}/contents/{path}", token)
    if not obj:
        return None
    return base64.b64decode(obj["content"]).decode()


def workflow_events(text: str) -> set[str] | None:
    """Return top-level workflow events, or None for an ambiguous on: mapping."""
    lines = text.splitlines()
    start = None
    on_key = re.compile(r'^\s*(?:on|"on"|\'on\'):\s*(?:#.*)?$')
    for index, line in enumerate(lines):
        if on_key.fullmatch(line) and not line[: len(line) - len(line.lstrip())]:
            start = index
            break
    if start is None:
        return None

    key_pattern = re.compile(
        r'^  (?:(?:"([A-Za-z0-9_-]+)")|(?:\'([A-Za-z0-9_-]+)\')|'
        r'([A-Za-z0-9_-]+)):\s*(?:.*)?$'
    )
    events: set[str] = set()
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break
        if indent > 2:
            continue
        if indent != 2:
            return None
        match = key_pattern.fullmatch(line)
        if not match:
            return None
        events.add(next(group for group in match.groups() if group is not None))
    return events


def require_fragments(
    text: str,
    fragments: tuple[str, ...],
    errors: list[str],
    label: str,
) -> None:
    for fragment in fragments:
        if fragment not in text:
            errors.append(f"{label} missing required contract fragment: {fragment}")


def central_ref(workflows_repository: str, target: str, required_sha: str) -> str:
    return f"{workflows_repository}/.github/workflows/{target}@{required_sha}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True)
    parser.add_argument("--workflows-repository", required=True)
    parser.add_argument("--required-sha", required=True)
    parser.add_argument("--repository-prefix", default="")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    if not re.fullmatch(r"[0-9a-f]{40}", args.required_sha):
        raise SystemExit("required SHA must be 40 lowercase hex chars")

    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        data, _ = api(
            f"https://api.github.com/orgs/{args.org}/repos?per_page=100&page={page}&type=all",
            token,
        )
        if not data:
            break
        repositories.extend(data)
        if len(data) < 100:
            break
        page += 1

    required = {
        "ci.yml": "reusable-ci-compact.yml",
        "security.yml": "reusable-security-compact.yml",
        "branch-cleanup.yml": "reusable-branch-cleanup.yml",
        "post-gate-branch-cleanup.yml": "reusable-gated-branch-cleanup.yml",
        "release-proof-dispatch.yml": "reusable-release-proof-dispatch.yml",
        "trusted-release-proof.yml": "reusable-release-proof.yml",
        "release-promotion.yml": "reusable-release-promote.yml",
        "release.yml": "reusable-release.yml",
        "release-verification.yml": "reusable-release-verification.yml",
        "release-metadata.yml": "reusable-release-metadata-current.yml",
    }
    direct_release_patterns = (
        r"softprops/action-gh-release",
        r"gh\s+release\s+create",
        r"/releases(?:/|\b)",
        r"git\s+tag\s+",
        r"npm\s+publish",
        r"uv\s+publish",
    )
    trusted_runner_fragment = "PRODKIT_RUNNER_JSON"
    hosted_control_plane_flag = "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE"

    findings: list[dict[str, Any]] = []
    repositories_checked = 0
    for repository in sorted(repositories, key=lambda value: value["name"]):
        name = repository["name"]
        if repository.get("archived"):
            continue
        if args.repository_prefix and not name.startswith(args.repository_prefix):
            continue
        if repository["full_name"] == args.workflows_repository:
            continue

        repositories_checked += 1
        repo = repository["full_name"]
        errors: list[str] = []
        for filename, target in required.items():
            text = file_text(repo, f".github/workflows/{filename}", token)
            if text is None:
                errors.append(f"missing .github/workflows/{filename}")
                continue

            expected = central_ref(args.workflows_repository, target, args.required_sha)
            if expected not in text:
                errors.append(f"{filename} not pinned to required central SHA/contract")

            floating = re.findall(
                re.escape(args.workflows_repository)
                + r"/.github/workflows/[^@\s]+@([^\s]+)",
                text,
            )
            if any(not re.fullmatch(r"[0-9a-f]{40}", ref) for ref in floating):
                errors.append(f"{filename} contains floating central reference")
            if "reusable-runner-policy.yml@" in text or "PRODKIT_RUNNER_MODE" in text:
                errors.append(f"{filename} uses retired runner-controller orchestration")

            if filename == "branch-cleanup.yml":
                require_fragments(
                    text,
                    (
                        "workflow_dispatch:",
                        "branches_json:",
                        "dry_run:",
                        "expected_default_sha:",
                        "contents: write",
                        "pull-requests: read",
                        "inputs.expected_default_sha != '' && inputs.expected_default_sha || github.sha",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )
                if workflow_events(text) != {"workflow_dispatch"}:
                    errors.append("branch-cleanup.yml must be workflow_dispatch-only")

            if filename == "post-gate-branch-cleanup.yml":
                require_fragments(
                    text,
                    (
                        "workflow_run:",
                        'workflows: ["CI", "Security", "CodeQL"]',
                        "types: [completed]",
                        "branches: [main]",
                        "github.event.workflow_run.event == 'push'",
                        "PRODKIT_GATED_CLEANUP_BRANCHES_JSON != ''",
                        "actions: write",
                        "expected_default_sha: ${{ github.event.workflow_run.head_sha }}",
                        "PRODKIT_GATED_CLEANUP_GATES_JSON",
                        "cleanup_workflow_file: branch-cleanup.yml",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )
                if workflow_events(text) != {"workflow_run"}:
                    errors.append("post-gate-branch-cleanup.yml must be workflow_run-only")
                if "contents: write" in text:
                    errors.append(
                        "post-gate-branch-cleanup.yml must delegate deletion to Branch Cleanup"
                    )

            if filename == "release-proof-dispatch.yml":
                require_fragments(
                    text,
                    (
                        "workflow_run:",
                        "types: [completed]",
                        "branches: [main]",
                        "github.event.workflow_run.event == 'push'",
                        "actions: write",
                        "source_sha: ${{ github.event.workflow_run.head_sha }}",
                        "required_workflows_json:",
                        "proof_workflow_file: trusted-release-proof.yml",
                        trusted_runner_fragment,
                        hosted_control_plane_flag,
                    ),
                    errors,
                    filename,
                )
                bridge = central_ref(
                    args.workflows_repository,
                    "reusable-release-proof-promotion-dispatch.yml",
                    args.required_sha,
                )
                require_fragments(
                    text,
                    (bridge, "promotion_workflow_file: release-promotion.yml"),
                    errors,
                    filename,
                )
                if workflow_events(text) != {"workflow_run"}:
                    errors.append("release-proof-dispatch.yml must be workflow_run-only")
                if "workflow_run.conclusion == 'success'" in text:
                    errors.append(
                        "release-proof-dispatch.yml must let the central dispatcher evaluate gates"
                    )
                if "contents: write" in text:
                    errors.append("release-proof-dispatch.yml must not mutate repository content")

            if filename == "trusted-release-proof.yml":
                if workflow_events(text) != {"workflow_dispatch"}:
                    errors.append("trusted-release-proof.yml must be workflow_dispatch-only")
                serial_promote = central_ref(
                    args.workflows_repository,
                    "reusable-release-promote.yml",
                    args.required_sha,
                )
                require_fragments(
                    text,
                    (
                        "source_sha: ${{ github.sha }}",
                        "needs: proof",
                        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE != 'true'",
                        serial_promote,
                        "actions: write",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )

            if filename == "release-promotion.yml":
                require_fragments(
                    text,
                    (
                        "workflow_run:",
                        'workflows: ["Trusted Release Proof"]',
                        "types: [completed]",
                        "workflow_dispatch:",
                        "source_sha:",
                        "proof_run_id:",
                        "github.event.workflow_run.event == 'workflow_dispatch'",
                        "github.event.workflow_run.conclusion == 'success'",
                        "github.event_name == 'workflow_dispatch'",
                        "workflow_run.head_sha",
                        "actions: write",
                        "PRODKIT_GITHUB_HOSTED_CONTROL_PLANE == 'true'",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )
                if workflow_events(text) != {"workflow_run", "workflow_dispatch"}:
                    errors.append(
                        "release-promotion.yml must expose only workflow_run and workflow_dispatch"
                    )
                for forbidden in ("time.sleep(", "while time.time()", "wait_for_release"):
                    if forbidden in text:
                        errors.append("release-promotion.yml must not poll or wait for Release")

            if filename == "release.yml":
                require_fragments(
                    text,
                    (
                        "target_sha: ${{ github.sha }}",
                        "proof_workflow_file: .github/workflows/trusted-release-proof.yml",
                        "verification-dispatch:",
                        "needs: release",
                        "actions: write",
                        "source_sha: ${{ github.sha }}",
                        "release_run_id: ${{ github.run_id }}",
                        "verification_workflow_file: release-verification.yml",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )
                dispatcher = central_ref(
                    args.workflows_repository,
                    "reusable-release-verification-dispatch.yml",
                    args.required_sha,
                )
                if dispatcher not in text:
                    errors.append("release.yml missing independent verification dispatcher")
                if "proof-gate:" in text or "urllib.request" in text:
                    errors.append(
                        "release.yml must not duplicate central proof-gate implementation"
                    )
                for pattern in direct_release_patterns:
                    if re.search(pattern, text, re.I):
                        errors.append(
                            f"release.yml contains local publication implementation: {pattern}"
                        )

            if filename == "release-verification.yml":
                if workflow_events(text) != {"workflow_dispatch"}:
                    errors.append("release-verification.yml must be workflow_dispatch-only")
                require_fragments(
                    text,
                    (
                        "source_sha: ${{ github.sha }}",
                        "release_run_id: ${{ inputs.release_run_id }}",
                        "actions: write",
                        "contents: read",
                        "automatic_cleanup: true",
                        "cleanup_workflow_file: branch-cleanup.yml",
                        trusted_runner_fragment,
                    ),
                    errors,
                    filename,
                )
                if "contents: write" in text:
                    errors.append(
                        "release-verification.yml may dispatch cleanup but must not mutate refs directly"
                    )

        if errors:
            findings.append({"repository": repo, "errors": sorted(set(errors))})

    report = {
        "organization": args.org,
        "workflows_repository": args.workflows_repository,
        "required_sha": args.required_sha,
        "repositories_checked": repositories_checked,
        "noncompliant": findings,
    }
    output = json.dumps(report, indent=2)
    print(output)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    if findings:
        raise SystemExit(f"{len(findings)} repositories violate workflow policy")


if __name__ == "__main__":
    main()
