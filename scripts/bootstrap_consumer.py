#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import stat


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install thin immutable prodkit-workflows consumer contracts."
    )
    parser.add_argument("--workflows-repository", default="ProdKit-dev/prodkit-workflows")
    parser.add_argument("--workflows-sha", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--include-codeql", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{40}", args.workflows_sha):
        raise SystemExit("--workflows-sha must be a full lowercase 40-character SHA")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.workflows_repository):
        raise SystemExit("invalid workflows repository")

    src = pathlib.Path(__file__).resolve().parents[1] / "templates"
    dest = pathlib.Path(args.destination).resolve()
    mapping = {
        src / "caller/ci.yml": dest / ".github/workflows/ci.yml",
        src / "caller/security.yml": dest / ".github/workflows/security.yml",
        src / "caller/branch-cleanup.yml": dest / ".github/workflows/branch-cleanup.yml",
        src / "caller/post-gate-branch-cleanup.yml": dest
        / ".github/workflows/post-gate-branch-cleanup.yml",
        src / "caller/trusted-release-proof.yml": dest
        / ".github/workflows/trusted-release-proof.yml",
        src / "caller/release-promotion.yml": dest
        / ".github/workflows/release-promotion.yml",
        src / "caller/release.yml": dest / ".github/workflows/release.yml",
        src / "caller/release-verification.yml": dest
        / ".github/workflows/release-verification.yml",
        src / "caller/release-metadata.yml": dest / ".github/workflows/release-metadata.yml",
        src / "consumer/.prodkit/release.json": dest / ".prodkit/release.json",
    }
    if args.include_codeql:
        mapping[src / "caller/codeql.yml"] = dest / ".github/workflows/codeql.yml"

    for source in (src / "consumer/.prodkit/workflows").iterdir():
        mapping[source] = dest / ".prodkit/workflows" / source.name

    for source, target in mapping.items():
        if target.exists() and not args.force:
            print(f"skip existing {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (
            source.read_text(encoding="utf-8")
            .replace("WORKFLOWS_REPOSITORY", args.workflows_repository)
            .replace("REPLACE_WITH_PRODKIT_WORKFLOWS_SHA", args.workflows_sha)
        )
        target.write_text(text, encoding="utf-8", newline="\n")
        if target.suffix == ".sh":
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
