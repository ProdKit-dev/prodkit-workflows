#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.request


def api(url, token):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prodkit-workflows-audit",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.load(response), response.headers
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, {}
        raise


def file_text(repo, path, token):
    obj, _ = api(f"https://api.github.com/repos/{repo}/contents/{path}", token)
    if not obj:
        return None
    return base64.b64decode(obj["content"]).decode()


def main():
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

    repos = []
    page = 1
    while True:
        data, _ = api(
            f"https://api.github.com/orgs/{args.org}/repos?per_page=100&page={page}&type=all",
            token,
        )
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    required = {
        "ci.yml": "reusable-ci-compact.yml",
        "security.yml": "reusable-security-compact.yml",
        "trusted-release-proof.yml": "reusable-release-proof.yml",
        "release-promotion.yml": "reusable-release-promote.yml",
        "release.yml": "reusable-release.yml",
        "release-verification.yml": "reusable-release-verification.yml",
        "release-metadata.yml": "reusable-release-metadata-current.yml",
    }
    direct_release_patterns = [
        r"softprops/action-gh-release",
        r"gh\s+release\s+create",
        r"/releases(?:/|\b)",
        r"git\s+tag\s+",
        r"npm\s+publish",
        r"uv\s+publish",
    ]

    findings = []
    repositories_checked = 0
    for repository in sorted(repos, key=lambda value: value["name"]):
        name = repository["name"]
        if repository.get("archived"):
            continue
        if args.repository_prefix and not name.startswith(args.repository_prefix):
            continue
        if repository["full_name"] == args.workflows_repository:
            continue

        repositories_checked += 1
        repo = repository["full_name"]
        errors = []
        for filename, target in required.items():
            text = file_text(repo, f".github/workflows/{filename}", token)
            if text is None:
                errors.append(f"missing .github/workflows/{filename}")
                continue

            expected = (
                f"{args.workflows_repository}/.github/workflows/{target}@{args.required_sha}"
            )
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

            if filename == "trusted-release-proof.yml":
                if "workflow_dispatch:" not in text:
                    errors.append("trusted-release-proof.yml must remain explicitly dispatched")
                if "reusable-release-promote.yml@" in text or "actions: write" in text:
                    errors.append(
                        "trusted-release-proof.yml must finish before Release promotion starts"
                    )

            if filename == "release-promotion.yml":
                required_fragments = (
                    "workflow_run:",
                    'workflows: ["Trusted Release Proof"]',
                    "types: [completed]",
                    "github.event.workflow_run.event == 'workflow_dispatch'",
                    "github.event.workflow_run.conclusion == 'success'",
                    "workflow_run.head_sha",
                    "actions: write",
                )
                if any(fragment not in text for fragment in required_fragments):
                    errors.append(
                        "release-promotion.yml must dispatch only after a completed successful proof"
                    )
                for forbidden in ("time.sleep(", "while time.time()", "wait_for_release"):
                    if forbidden in text:
                        errors.append(
                            "release-promotion.yml must not poll or wait for Release"
                        )

            if filename == "release.yml":
                if "target_sha: ${{ github.sha }}" not in text:
                    errors.append("release.yml must publish the dispatched current-main SHA")
                if "proof_workflow_file: .github/workflows/trusted-release-proof.yml" not in text:
                    errors.append("release.yml must delegate Trusted Release Proof authorization centrally")
                if "proof-gate:" in text or "urllib.request" in text:
                    errors.append("release.yml must not duplicate central proof-gate implementation")
                for pattern in direct_release_patterns:
                    if re.search(pattern, text, re.I):
                        errors.append(
                            f"release.yml contains local publication implementation: {pattern}"
                        )

            if filename == "release-verification.yml":
                if "workflow_run:" not in text or 'workflows: ["Release"]' not in text:
                    errors.append("release-verification.yml must run after Release completion")
                if "actions: write" in text or "contents: write" in text:
                    errors.append("release-verification.yml must remain read-only")

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
