#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def check(security_only: bool = False) -> list[str]:
    errors: list[str] = []

    # JSON integrity.
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text())
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")

    # Text hygiene and accidental credentials.
    secret_patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if "\r\n" in text:
            errors.append(f"{path.relative_to(ROOT)}: CRLF")
        for line_number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"{path.relative_to(ROOT)}:{line_number}: trailing whitespace")
        for pattern in secret_patterns:
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: possible credential")

    if not security_only:
        expected = [
            ".github/workflows/reusable-ci.yml",
            ".github/workflows/reusable-security.yml",
            ".github/workflows/reusable-release.yml",
            "contracts/release-manifest.schema.json",
            "rulesets/org-main.json",
            "rulesets/org-release-tags.json",
        ]
        for relative in expected:
            if not (ROOT / relative).is_file():
                errors.append(f"missing {relative}")

        # All production third-party Action refs must be full SHA. Local uses are allowed.
        # Templates intentionally contain a replacement sentinel.
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                match = re.search(r"\buses:\s*([^\s#]+)", line)
                if not match:
                    continue
                ref = match.group(1)
                if ref.startswith("./"):
                    continue
                if "@" not in ref or not re.fullmatch(r".+@[0-9a-f]{40}", ref):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{line_number}: action/workflow not full-SHA pinned: {ref}"
                    )

        # Organization ruleset recipes must be safe to import. Import must never
        # immediately enforce against ~ALL before repository targeting is reviewed.
        for relative in ("rulesets/org-main.json", "rulesets/org-release-tags.json"):
            payload = json.loads((ROOT / relative).read_text())
            if payload.get("source_type") != "Organization":
                errors.append(f"{relative}: expected Organization source_type")
            if payload.get("enforcement") != "disabled":
                errors.append(f"{relative}: import recipe must be disabled by default")

        version = (ROOT / "VERSION").read_text().strip()
        if f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text():
            errors.append("CHANGELOG missing current version")
        if not (ROOT / f"docs/V{version}.md").is_file():
            errors.append("version release notes missing")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--security-only", action="store_true")
    args = parser.parse_args()
    errors = check(args.security_only)
    if errors:
        print("\n".join("ERROR: " + error for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("repository checks passed")


if __name__ == "__main__":
    main()
