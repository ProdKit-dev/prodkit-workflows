#!/usr/bin/env python3
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    # Self manifest validates current version.
    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/validate_release_manifest.py"),
            (ROOT / "VERSION").read_text().strip(),
            "--root",
            str(ROOT),
        ],
        check=True,
    )

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
            if f"example/workflows/.github/workflows/" not in text or f"@{sha}" not in text:
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

    if "default: '\"ubuntu-latest\"'" not in reusable_ci:
        raise SystemExit("reusable CI must default to GitHub-hosted")
    if "default: '\"ubuntu-latest\"'" not in reusable_security:
        raise SystemExit("reusable Security must default to GitHub-hosted")
    for required in (
        "gitleaks_config_path:",
        "--report-format json",
        "gitleaks-report.json",
        "Preserve redacted Gitleaks evidence",
    ):
        if required not in reusable_security:
            raise SystemExit(f"reusable Security diagnostics contract missing: {required}")

    for required in (
        "python_enabled:",
        "node_enabled:",
        "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
        'npm install --global "pnpm@${{ inputs.pnpm_version }}"',
    ):
        if required not in reusable_release:
            raise SystemExit(f"reusable release toolchain contract missing: {required}")

    # CI/Security concurrency belongs to the caller so two independent calls to
    # the same reusable workflow can coexist in one workflow run (for example a
    # hosted/self-hosted portability canary). Release keeps its own version lock.
    for name in ("reusable-ci.yml", "reusable-security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if "\nconcurrency:\n" in text:
            raise SystemExit(f"reusable workflow must not own caller concurrency: {name}")

    # This public repository must not automatically send PR code to a persistent
    # self-hosted runner. Automatic CI/Security use GitHub-hosted runners and the
    # self-hosted target is available only through explicit workflow_dispatch.
    for name in ("ci.yml", "security.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        if '"ubuntu-latest"' not in text or "workflow_dispatch:" not in text:
            raise SystemExit(f"self caller is not hosted-first: {name}")
        if "inputs.runner == 'self-hosted'" not in text:
            raise SystemExit(f"self-hosted failover selector missing: {name}")
        if "concurrency:" not in text or "cancel-in-progress: true" not in text:
            raise SystemExit(f"self caller concurrency contract missing: {name}")

    print("contract tests passed")


if __name__ == "__main__":
    main()
