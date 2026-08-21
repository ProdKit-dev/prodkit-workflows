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
    "reusable-runner-policy.yml",
    "reusable-release-proof.yml",
    "reusable-codeql.yml",
    "reusable-release-pipeline.yml",
    "reusable-release-metadata-current.yml",
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
    "release-proof.sh",
    "codeql-check.sh",
}

EXPECTED_SELF_ADAPTERS = {
    "ci-hygiene.sh",
    "ci-custom.sh",
    "security-custom.sh",
    "release-build.sh",
}

DEFAULT_CALLERS = {
    "ci.yml",
    "security.yml",
    "trusted-release-proof.yml",
    "release.yml",
    "release-metadata.yml",
}


def require(text: str, fragments: tuple[str, ...], *, name: str) -> None:
    for fragment in fragments:
        if fragment not in text:
            raise SystemExit(f"{name} missing contract fragment: {fragment}")


def run_validator(root: pathlib.Path, *, expect_success: bool) -> None:
    result = subprocess.run(
        ["python3", str(VALIDATOR), "1.2.3", "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise SystemExit(f"validator unexpectedly failed: {result.stderr}")
    if not expect_success and result.returncode == 0:
        raise SystemExit("validator unexpectedly accepted an invalid manifest")


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


def write_manifest_fixture(root: pathlib.Path, manifest: dict[str, object]) -> None:
    (root / ".prodkit/workflows").mkdir(parents=True)
    (root / ".prodkit/workflows/release-build.sh").write_text("#!/bin/sh\nexit 0\n")
    (root / "VERSION").write_text("1.2.3\n")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3]\n")
    (root / "docs").mkdir()
    (root / "docs/V1.2.3.md").write_text("# v1.2.3\n")
    (root / ".prodkit/release.json").write_text(json.dumps(manifest))


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

    schema = json.loads((ROOT / "contracts/release-manifest.schema.json").read_text())
    if schema.get("additionalProperties") is not False:
        raise SystemExit("release schema must reject unknown top-level properties")


def assert_thin_caller(path: pathlib.Path) -> None:
    text = path.read_text()
    require(
        text,
        (
            "reusable-runner-policy.yml@",
            "needs: runner",
            "needs.runner.outputs.runner_json",
        ),
        name=str(path),
    )
    for forbidden in (
        "runner-probe:",
        "needs.runner-probe",
        "fromJSON(",
        '["self-hosted","Linux","X64"]',
    ):
        if forbidden in text:
            raise SystemExit(f"consumer caller owns runner internals: {path}: {forbidden}")


def test_bootstrap() -> None:
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
        generated = {path.name for path in (dest / ".github/workflows").glob("*.yml")}
        if generated != DEFAULT_CALLERS:
            raise SystemExit(f"bootstrap workflow drift: {sorted(generated)}")
        for name in DEFAULT_CALLERS:
            text = (dest / ".github/workflows" / name).read_text()
            if f"@{sha}" not in text or "example/workflows/.github/workflows/" not in text:
                raise SystemExit(f"bootstrap pin failure: {name}")
        for name in (
            "ci.yml",
            "security.yml",
            "release.yml",
            "release-metadata.yml",
            "trusted-release-proof.yml",
        ):
            assert_thin_caller(dest / ".github/workflows" / name)

        adapters = {path.name for path in (dest / ".prodkit/workflows").glob("*.sh")}
        if adapters != EXPECTED_CONSUMER_ADAPTERS:
            raise SystemExit(f"bootstrap adapter drift: {sorted(adapters)}")

    with tempfile.TemporaryDirectory() as td:
        dest = pathlib.Path(td) / "consumer"
        dest.mkdir()
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts/bootstrap_consumer.py"),
                "--workflows-sha",
                "b" * 40,
                "--destination",
                str(dest),
                "--include-codeql",
            ],
            check=True,
        )
        if not (dest / ".github/workflows/codeql.yml").is_file():
            raise SystemExit("bootstrap --include-codeql did not install CodeQL caller")
        assert_thin_caller(dest / ".github/workflows/codeql.yml")


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

    workflows = {path.name for path in (ROOT / ".github/workflows").glob("*.yml")}
    if workflows != EXPECTED_GITHUB_WORKFLOWS:
        raise SystemExit(
            f"control-plane workflow drift: actual={sorted(workflows)} expected={sorted(EXPECTED_GITHUB_WORKFLOWS)}"
        )

    self_adapters = {path.name for path in (ROOT / ".prodkit/workflows").glob("*.sh")}
    if self_adapters != EXPECTED_SELF_ADAPTERS:
        raise SystemExit(f"control-plane self-adapter drift: {sorted(self_adapters)}")

    template_adapters = {
        path.name for path in (ROOT / "templates/consumer/.prodkit/workflows").glob("*.sh")
    }
    if template_adapters != EXPECTED_CONSUMER_ADAPTERS:
        raise SystemExit(f"consumer adapter template drift: {sorted(template_adapters)}")

    test_bootstrap()

    runner = (ROOT / ".github/workflows/reusable-runner-policy.yml").read_text()
    require(
        runner,
        (
            "PRODKIT_RUNNER_MODE",
            "Hosted runner availability",
            "continue-on-error: true",
            "github.event.pull_request.head.repo.full_name == github.repository",
            "runner_json:",
            "lane:",
            "unsupported runner mode",
        ),
        name="Reusable Runner Policy",
    )

    proof = (ROOT / ".github/workflows/reusable-release-proof.yml").read_text()
    require(
        proof,
        (
            "source_sha:",
            "Exact-source enterprise proof",
            "origin/$MAIN_BRANCH",
            "proof path escapes .prodkit/workflows",
            "Assert source remained immutable",
            "trusted-release-proof-${{ inputs.source_sha }}",
        ),
        name="Reusable Release Proof",
    )

    release_pipeline = (ROOT / ".github/workflows/reusable-release-pipeline.yml").read_text()
    require(
        release_pipeline,
        (
            "Verify release-candidate proof",
            '"event": "workflow_dispatch"',
            "missing successful workflow_dispatch",
            "uses: ./.github/workflows/reusable-release.yml",
            "required_push_workflows_json:",
            "required_workflows_json: ${{ inputs.required_push_workflows_json }}",
        ),
        name="Reusable Release Pipeline",
    )

    codeql = (ROOT / ".github/workflows/reusable-codeql.yml").read_text()
    require(
        codeql,
        (
            "CodeQL (${{ matrix.language }})",
            "github/codeql-action/init@ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd",
            "CodeQL Required",
            "check_script:",
        ),
        name="Reusable CodeQL",
    )

    metadata = (ROOT / ".github/workflows/reusable-release-metadata-current.yml").read_text()
    require(
        metadata,
        (
            "Select published release",
            "version and source_sha must be supplied together",
            "uses: ./.github/workflows/reusable-release-metadata.yml",
            "normalize_all_titles:",
            "Normalize SemVer Release names only",
        ),
        name="Reusable Current Release Metadata",
    )

    for name in ("ci.yml", "security.yml", "release.yml", "org-audit.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if "reusable-runner-policy.yml" not in text:
            raise SystemExit(f"self caller bypasses centralized runner policy: {name}")
        for forbidden in ("runner-probe:", "needs.runner-probe", "fromJSON("):
            if forbidden in text:
                raise SystemExit(f"self caller contains runner implementation detail: {name}: {forbidden}")

    lifecycle = (ROOT / "docs/LIFECYCLE.md").read_text()
    require(
        lifecycle,
        (
            "Pull request",
            "Main branch",
            "Release candidate",
            "Publication",
            "Metadata repair",
            "Trusted Release Proof",
            "workflow_dispatch",
            "does not run on every pull-request commit",
            "Quality is a release-presentation reference",
        ),
        name="LIFECYCLE.md",
    )

    print("contract tests passed")


if __name__ == "__main__":
    main()
