#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import tomllib
from typing import Any

TOP_LEVEL_KEYS = {"schema_version", "version", "notes", "build", "release"}
VERSION_KEYS = {"sources"}
SOURCE_KEYS = {"type", "path", "selector"}
NOTES_KEYS = {"path_template", "changelog_path", "changelog_heading_template"}
BUILD_KEYS = {"script", "artifact_dir", "source_archive"}
RELEASE_KEYS = {"name_template"}
SOURCE_TYPES = {"text", "json", "toml"}


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _reject_unknown(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unknown {name} keys: {', '.join(unknown)}")


def _require_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _inside(root: pathlib.Path, raw_path: str, *, allow_root: bool = False) -> pathlib.Path:
    path = pathlib.Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"absolute path is not allowed: {raw_path}")
    resolved = (root / path).resolve()
    if resolved == root:
        if allow_root:
            return resolved
        raise ValueError(f"path resolves to repository root: {raw_path}")
    if root not in resolved.parents:
        raise ValueError(f"path escapes root: {raw_path}")
    return resolved


def _dotted(obj: Any, selector: str) -> Any:
    for part in selector.split("."):
        obj = obj[part]
    return obj


def validate_shape(data: Any) -> dict[str, Any]:
    manifest = _require_object(data, "release manifest")
    _reject_unknown(manifest, TOP_LEVEL_KEYS, "release manifest")

    required = {"schema_version", "version", "notes", "build"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"missing release manifest keys: {', '.join(missing)}")
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported schema_version")

    version_block = _require_object(manifest["version"], "version")
    _reject_unknown(version_block, VERSION_KEYS, "version")
    if "sources" not in version_block:
        raise ValueError("version.sources is required")
    sources = version_block["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError("at least one version source required")
    for index, source_value in enumerate(sources):
        source = _require_object(source_value, f"version.sources[{index}]")
        _reject_unknown(source, SOURCE_KEYS, f"version.sources[{index}]")
        missing_source = {"type", "path"} - set(source)
        if missing_source:
            raise ValueError(
                f"version.sources[{index}] missing keys: {', '.join(sorted(missing_source))}"
            )
        source_type = source["type"]
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source type: {source_type}")
        _require_nonempty_string(source["path"], f"version.sources[{index}].path")
        if "selector" in source:
            _require_nonempty_string(source["selector"], f"version.sources[{index}].selector")

    notes = _require_object(manifest["notes"], "notes")
    _reject_unknown(notes, NOTES_KEYS, "notes")
    if "path_template" not in notes:
        raise ValueError("notes.path_template is required")
    _require_nonempty_string(notes["path_template"], "notes.path_template")
    for key in ("changelog_path", "changelog_heading_template"):
        if key in notes:
            _require_nonempty_string(notes[key], f"notes.{key}")

    build = _require_object(manifest["build"], "build")
    _reject_unknown(build, BUILD_KEYS, "build")
    for key in ("script", "artifact_dir"):
        if key not in build:
            raise ValueError(f"build.{key} is required")
        _require_nonempty_string(build[key], f"build.{key}")
    if "source_archive" in build and not isinstance(build["source_archive"], bool):
        raise ValueError("build.source_archive must be a boolean")

    if "release" in manifest:
        release = _require_object(manifest["release"], "release")
        _reject_unknown(release, RELEASE_KEYS, "release")
        if "name_template" in release:
            _require_nonempty_string(release["name_template"], "release.name_template")

    return manifest


def validate(root: pathlib.Path, manifest_path: pathlib.Path, version: str) -> dict[str, Any]:
    root = root.resolve()
    raw_manifest = manifest_path
    if raw_manifest.is_symlink():
        raise ValueError("manifest must be a regular non-symlink file")
    manifest_path = raw_manifest.resolve()
    if manifest_path == root or root not in manifest_path.parents:
        raise ValueError("manifest escapes root")
    if not manifest_path.is_file():
        raise ValueError("manifest must be a regular non-symlink file")

    data = validate_shape(json.loads(manifest_path.read_text(encoding="utf-8")))

    for source in data["version"]["sources"]:
        path = _inside(root, source["path"])
        if not path.is_file():
            raise ValueError(f"version source missing: {source['path']}")
        source_type = source["type"]
        selector = source.get("selector")
        if source_type == "text":
            actual = path.read_text(encoding="utf-8").strip()
        elif source_type == "json":
            actual = _dotted(
                json.loads(path.read_text(encoding="utf-8")), selector or "version"
            )
        else:
            actual = _dotted(
                tomllib.loads(path.read_text(encoding="utf-8")), selector or "project.version"
            )
        if str(actual) != version:
            raise ValueError(f"version mismatch {source['path']}: {actual} != {version}")

    notes = data["notes"]
    notes_path_value = notes["path_template"].format(version=version, tag="v" + version)
    notes_path = _inside(root, notes_path_value)
    if not notes_path.is_file():
        raise ValueError(f"missing notes {notes_path_value}")

    changelog_path_value = notes.get("changelog_path", "CHANGELOG.md")
    changelog_path = _inside(root, changelog_path_value)
    if not changelog_path.is_file():
        raise ValueError(f"missing changelog {changelog_path_value}")
    heading = notes.get("changelog_heading_template", "## [{version}]").format(
        version=version, tag="v" + version
    )
    if heading not in changelog_path.read_text(encoding="utf-8"):
        raise ValueError(f"changelog missing heading: {heading}")

    build = data["build"]
    raw_script = root / pathlib.Path(build["script"])
    if raw_script.is_symlink():
        raise ValueError("build script invalid")
    script = _inside(root, build["script"])
    artifact = _inside(root, build["artifact_dir"])
    if not script.is_file():
        raise ValueError("build script invalid")
    if artifact.exists() and not artifact.is_dir():
        raise ValueError("artifact_dir exists but is not a directory")

    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default=".prodkit/release.json")
    args = parser.parse_args()
    root = pathlib.Path(args.root)
    validate(root, root / args.manifest, args.version)
    print("release manifest valid")


if __name__ == "__main__":
    main()
