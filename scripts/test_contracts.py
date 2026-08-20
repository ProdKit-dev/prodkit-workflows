#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_release_manifest.py"

EXPECTED_GITHUB_WORKFLOWS = {
    "ci.yml",
    "security.yml",
    "release.yml",
    "org-audit.yml",
    "reusable-ci.yml",
    "reusable-security.yml",
    "reusable-release.yml",
    "reusable-release-metadata.yml",
    "reusable-org-audit.yml",
}

EXPECTED_CONSUMER_ADAPTERS = {
    "ci-hygiene.sh",
    "ci-python.sh",
    "ci-node.sh",
    "ci-postgres.sh",
    "ci-container.sh",
    "ci-custom.sh",
    "security-python.sh",
    "security-node.sh",
    "security-container-build.sh",
    "security-custom.sh",
    "release-build.sh",
}

EXPECTED_SELF_ADAPTERS = {
    "ci-hygiene.sh",
    "ci-custom.sh",
    "security-custom.sh",
    "release-build.sh",
}


def run_validator(root: pathlib.Path, version: str = "1.2.3", *, expect_success: bool) -> None:
    result = subprocess.run(
        ["python3", str(VALIDATOR), version, "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise SystemExit(f"validator unexpectedly failed: {result.stderr}")
    if not expect_success and result.returncode == 0:
        raise SystemExit("validator unexpectedly accepted an invalid manifest")


def write_manifest_fixture(root: pathlib.Path, manifest: dict[str, object]) -> None:
    (root / ".prodkit/workflows").mkdir(parents=True)
    (root / ".prodkit/workflows/release-build.sh").write_text("#!/bin/sh\nexit 0\n")
    (root / "VERSION").write_text("1.2.3\n")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3]\n")
    (root / "docs").mkdir()
    (root / "docs/V1.2.3.md").write_text("# v1.2.3\n")
    (root / ".prodkit/release.json").write_text(json.dumps(manifest))


def base_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "version": {"sources": [{"type": "text", "path": "VERSION"}]},
        "notes": {
            "path_template": "docs/V{version}.md",
            "changelog_path": "CHANGELOG.md",
            "changelog_heading_template": "## [{version}]",
        },
        "build": {
            "script": ".prodkit/workflows/release-build.sh",
            "artifact_dir": "dist/release",
            "source_archive": True,
        },
        "release": {"name_template": "Example {tag}"},
    }


def test_manifest_contract() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        write_manifest_fixture(root, base_manifest())
        run_validator(root, expect_success=True)

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        manifest = base_manifest()
        manifest["version"] = {"sources": []}
        write_manifest_fixture(root, manifest)
        run_validator(root, expect_success=False)

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        manifest = base_manifest()
        manifest["unexpected"] = True
        write_manifest_fixture(root, manifest)
        run_validator(root, expect_success=False)

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        manifest = base_manifest()
        manifest["version"] = {"sources": [{"type": "text", "path": "../VERSION"}]}
        write_manifest_fixture(root, manifest)
        run_validator(root, expect_success=False)

    schema = json.loads((ROOT / "contracts/release-manifest.schema.json").read_text())
    if schema.get("additionalProperties") is not False:
        raise SystemExit("release schema must reject unknown top-level properties")
    sources = schema["properties"]["version"]["properties"]["sources"]
    if sources.get("minItems") != 1:
        raise SystemExit("release schema must require at least one version source")


def assert_runner_policy(text: str, *, name: str, fork_safe: bool) -> None:
    for required in (
        "workflow_dispatch:",
        "default: policy",
        "PRODKIT_RUNNER_MODE",
        "- auto",
        "github-hosted",
        "self-hosted",
        "runner-probe:",
        "Hosted runner availability",
        "runs-on: ubuntu-latest",
        "continue-on-error: true",
        "available: ${{ steps.probe.outputs.available }}",
        "id: probe",
        "needs: runner-probe",
        "needs.runner-probe.outputs.available != 'true'",
        '"ubuntu-latest"',
        "inputs.runner == 'policy'",
        "inputs.runner == 'self-hosted'",
        "inputs.runner == 'auto'",
        "vars.PRODKIT_RUNNER_MODE == 'auto'",
    ):
        if required not in text:
            raise SystemExit(f"runner policy missing from {name}: {required}")
    if "needs.runner-probe.result == 'failure'" in text:
        raise SystemExit(f"runner policy in {name} still routes from a poisoning failed job")
    if fork_safe:
        if "github.event.pull_request.head.repo.full_name == github.repository" not in text:
            raise SystemExit(f"fork safety missing from {name}")
        if text.count("github.event.pull_request.head.repo.full_name == github.repository") < 2:
            raise SystemExit(f"fork safety must guard both probe and self-hosted routing in {name}")


def main() -> None:
    subprocess.run(
        [
            "python3",
            str(VALIDATOR),
            (ROOT / "VERSION").read_text().strip(),
            "--root",
            str(ROOT),
        ],
        check=True,
    )
    test_manifest_contract()

    github_workflows = {p.name for p in (ROOT / ".github/workflows").glob("*.yml")}
    if github_workflows != EXPECTED_GITHUB_WORKFLOWS:
        raise SystemExit(
            "control-plane workflow surface drift: "
            f"actual={sorted(github_workflows)} expected={sorted(EXPECTED_GITHUB_WORKFLOWS)}"
        )

    self_adapters = {p.name for p in (ROOT / ".prodkit/workflows").glob("*.sh")}
    if self_adapters != EXPECTED_SELF_ADAPTERS:
        raise SystemExit(
            "control-plane self-adapter surface drift: "
            f"actual={sorted(self_adapters)} expected={sorted(EXPECTED_SELF_ADAPTERS)}"
        )

    template_adapters = {
        p.name for p in (ROOT / "templates/consumer/.prodkit/workflows").glob("*.sh")
    }
    if template_adapters != EXPECTED_CONSUMER_ADAPTERS:
        raise SystemExit(
            "consumer adapter template surface drift: "
            f"actual={sorted(template_adapters)} expected={sorted(EXPECTED_CONSUMER_ADAPTERS)}"
        )

    with tempfile.TemporaryDirectory() as td:
        dest = pathlib.Path(td) / "consumer"
        dest.mkdir()
        sha = "a" * 40
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts/bootstrap_consumer.py"),
                "--workflows-repository",
                "example/workflows",
                "--workflows-sha",
                sha,
                "--destination",
                str(dest),
            ],
            check=True,
        )
        for name in ["ci.yml", "security.yml", "release.yml"]:
            text = (dest / ".github/workflows" / name).read_text()
            if "example/workflows/.github/workflows/" not in text or f"@{sha}" not in text:
                raise SystemExit("bootstrap pin failure")
            assert_runner_policy(
                text,
                name=f"bootstrap {name}",
                fork_safe=name in {"ci.yml", "security.yml"},
            )

        for name in ("ci.yml", "security.yml"):
            text = (dest / ".github/workflows" / name).read_text()
            if "concurrency:" not in text or "cancel-in-progress: true" not in text:
                raise SystemExit(f"bootstrap caller concurrency contract missing: {name}")

        if not (dest / ".prodkit/release.json").is_file():
            raise SystemExit("bootstrap manifest missing")
        generated_adapters = {p.name for p in (dest / ".prodkit/workflows").glob("*.sh")}
        if generated_adapters != EXPECTED_CONSUMER_ADAPTERS:
            raise SystemExit(
                "bootstrap adapter catalog drift: "
                f"actual={sorted(generated_adapters)} "
                f"expected={sorted(EXPECTED_CONSUMER_ADAPTERS)}"
            )

        release = (dest / ".github/workflows/release.yml").read_text()
        for required in (
            "python_enabled: true",
            'python_version: "3.12"',
            'uv_version: "0.10.0"',
            "node_enabled: true",
            'node_version: "24"',
            'pnpm_version: "11.21.0"',
        ):
            if required not in release:
                raise SystemExit(f"bootstrap release toolchain contract missing: {required}")

    reusable_ci = (ROOT / ".github/workflows/reusable-ci.yml").read_text()
    reusable_security = (ROOT / ".github/workflows/reusable-security.yml").read_text()
    reusable_release = (ROOT / ".github/workflows/reusable-release.yml").read_text()
    reusable_release_metadata = (
        ROOT / ".github/workflows/reusable-release-metadata.yml"
    ).read_text()
    reusable_org_audit = (ROOT / ".github/workflows/reusable-org-audit.yml").read_text()
    contracts = (ROOT / "docs/CONTRACTS.md").read_text()
    readme = (ROOT / "README.md").read_text()
    runners = (ROOT / "docs/RUNNERS.md").read_text()

    for name, text in (
        ("CI", reusable_ci),
        ("Security", reusable_security),
        ("Release", reusable_release),
        ("Release Metadata", reusable_release_metadata),
        ("Organization Audit", reusable_org_audit),
    ):
        if "default: '\"ubuntu-latest\"'" not in text:
            raise SystemExit(f"reusable {name} must default to GitHub-hosted")

    if reusable_ci.count("contract path escapes .prodkit/workflows") < 6:
        raise SystemExit("reusable CI does not validate every adapter path")
    if reusable_security.count("contract path escapes .prodkit/workflows") < 4:
        raise SystemExit("reusable Security does not validate every adapter path")

    for required in (
        "gitleaks_config_path:",
        "--report-format json",
        "gitleaks-report.json",
        "Preserve redacted Gitleaks evidence",
        "gitleaks_config_path escapes repository",
    ):
        if required not in reusable_security:
            raise SystemExit(f"reusable Security diagnostics contract missing: {required}")

    for required in (
        "python_enabled:",
        "node_enabled:",
        "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
        'npm install --global "pnpm@${{ inputs.pnpm_version }}"',
        "at least one version source required",
        "reject_unknown(manifest",
        "Validate consumer release payload contract",
        "consumer release payload set is empty",
        "consumer emitted central-owned artifact",
        "release-metadata.json",
        "repository.spdx.json",
        "SHA256SUMS",
    ):
        if required not in reusable_release:
            raise SystemExit(f"reusable Release contract missing: {required}")

    for required in (
        "source_sha:",
        "Guarded release metadata repair",
        "does not resolve to requested source SHA",
        "SHA256SUMS",
        '"name": expected_name',
        '"body": expected_body',
        "release publication flags changed during metadata repair",
        "published asset identity changed during metadata-only repair",
        "immutable tag moved during metadata repair",
    ):
        if required not in reusable_release_metadata:
            raise SystemExit(f"reusable Release Metadata contract missing: {required}")

    for name in ("reusable-ci.yml", "reusable-security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if "\nconcurrency:\n" in text:
            raise SystemExit(f"reusable workflow must not own caller concurrency: {name}")
    if "group: release-${{ inputs.version }}" not in reusable_release:
        raise SystemExit("reusable Release version concurrency contract missing")
    if "group: release-metadata-${{ inputs.version }}" not in reusable_release_metadata:
        raise SystemExit("reusable Release Metadata version concurrency contract missing")

    for name in ("ci.yml", "security.yml", "release.yml", "org-audit.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        assert_runner_policy(
            text,
            name=f"self caller {name}",
            fork_safe=name in {"ci.yml", "security.yml"},
        )
    for name in ("ci.yml", "security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if "concurrency:" not in text or "cancel-in-progress: true" not in text:
            raise SystemExit(f"self caller concurrency contract missing: {name}")

    for phrase in (
        "exact lowercase 40-character Git commit SHA",
        "Repository layers and file ownership",
        "Complete consumer adapter catalog",
        "Disabled capabilities do not require their adapter file to exist",
        "PRODKIT_RUNNER_MODE",
        "Hosted-first failover contract",
        "fork-originated pull requests are always forced onto GitHub-hosted runners",
        "real CI test failure",
        "non-poisoning",
        "at least one payload",
        "Release publication state machine",
        "Release metadata repair",
        "required_workflows_json",
        "gitleaks_config_path",
    ):
        if phrase not in contracts:
            raise SystemExit(f"CONTRACTS.md missing normative contract: {phrase}")

    for phrase in (
        "Hosted-first automatic runner failover",
        "non-poisoning",
        "runner: auto",
        "ci / CI Required",
        "security / Security Required",
    ):
        if phrase not in readme:
            raise SystemExit(f"README runner failover contract missing: {phrase}")

    for phrase in (
        "Automatic hosted-first failover",
        "non-poisoning",
        "jobs that fail before step 1",
        "genuine test",
        "There is intentionally no automatic self-hosted-to-hosted failover",
    ):
        if phrase not in runners:
            raise SystemExit(f"RUNNERS.md failover contract missing: {phrase}")

    if "default to `self-hosted" in readme:
        raise SystemExit("README still claims self-hosted is the default")

    print("contract tests passed")


if __name__ == "__main__":
    main()
