#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_release_manifest.py"


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


def main() -> None:
    # Self manifest validates current version.
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

    # Bootstrap must materialize immutable refs and all adapters.
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
            for required in (
                "workflow_dispatch:",
                "github-hosted",
                "self-hosted",
                '"ubuntu-latest"',
            ):
                if required not in text:
                    raise SystemExit(
                        f"bootstrap hosted-first runner contract missing from {name}: {required}"
                    )

        for name in ("ci.yml", "security.yml"):
            text = (dest / ".github/workflows" / name).read_text()
            if "concurrency:" not in text or "cancel-in-progress: true" not in text:
                raise SystemExit(f"bootstrap caller concurrency contract missing: {name}")

        if not (dest / ".prodkit/release.json").is_file():
            raise SystemExit("bootstrap manifest missing")
        if len(list((dest / ".prodkit/workflows").glob("*.sh"))) < 10:
            raise SystemExit("bootstrap adapters incomplete")

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
    contracts = (ROOT / "docs/CONTRACTS.md").read_text()

    for name, text in (
        ("CI", reusable_ci),
        ("Security", reusable_security),
        ("Release", reusable_release),
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
        "unknown release manifest keys",
        "Validate consumer release payload contract",
        "consumer release payload set is empty",
        "consumer emitted central-owned artifact",
        "release-metadata.json",
        "repository.spdx.json",
        "SHA256SUMS",
    ):
        if required not in reusable_release:
            raise SystemExit(f"reusable Release contract missing: {required}")

    # CI/Security concurrency belongs to the caller so two independent calls to
    # the same reusable workflow can coexist. Release keeps its own version lock.
    for name in ("reusable-ci.yml", "reusable-security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if "\nconcurrency:\n" in text:
            raise SystemExit(f"reusable workflow must not own caller concurrency: {name}")
    if "group: release-${{ inputs.version }}" not in reusable_release:
        raise SystemExit("reusable Release version concurrency contract missing")

    # Public self callers are hosted-first with explicit trusted failover.
    for name in ("ci.yml", "security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if '"ubuntu-latest"' not in text or "workflow_dispatch:" not in text:
            raise SystemExit(f"self caller is not hosted-first: {name}")
        if "inputs.runner == 'self-hosted'" not in text:
            raise SystemExit(f"self-hosted failover selector missing: {name}")
        if "concurrency:" not in text or "cancel-in-progress: true" not in text:
            raise SystemExit(f"self caller concurrency contract missing: {name}")

    for phrase in (
        "exact lowercase 40-character Git commit SHA",
        "Adapter path contract",
        "at least one payload",
        "Release publication state machine",
        "required_workflows_json",
        "gitleaks_config_path",
    ):
        if phrase not in contracts:
            raise SystemExit(f"CONTRACTS.md missing normative contract: {phrase}")

    print("contract tests passed")


if __name__ == "__main__":
    main()
