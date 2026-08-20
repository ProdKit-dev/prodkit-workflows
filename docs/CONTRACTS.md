# Consumer Contracts

## CI adapters

All paths must be regular files beneath `.prodkit/workflows/`.

- `ci-hygiene.sh`: repository structure, architecture, generated-file, migration immutability, documentation, and release metadata checks.
- `ci-python.sh`: receives `PRODKIT_PYTHON_VERSION` and owns dependency sync plus Python checks for that version.
- `ci-node.sh`: receives `PRODKIT_NODE_VERSION` and owns package-manager install/build/test behavior.
- `ci-postgres.sh`: receives `PRODKIT_POSTGRES_HOST`, `PRODKIT_POSTGRES_PORT`, `PRODKIT_POSTGRES_DATABASE`, `PRODKIT_POSTGRES_USER`, and `PRODKIT_POSTGRES_PASSWORD` for an isolated PostgreSQL service.
- `ci-container.sh`: production image build/runtime smoke.
- `ci-custom.sh`: domain-specific gates.

Disabled capabilities are `skipped`; the `CI Required` aggregator accepts only `success` or `skipped`.

## Security adapters

- `security-python.sh`: Python runtime dependency audit.
- `security-node.sh`: Node runtime dependency audit.
- `security-container-build.sh`: must build the image named by `PRODKIT_SECURITY_IMAGE`; the central workflow performs the vulnerability scan.
- `security-custom.sh`: domain-specific security assertions.

Gitleaks and source SBOM generation are centrally owned. `Security Required` accepts only `success` or `skipped`.

## Release manifest

`.prodkit/release.json` is schema version 1. Version sources may be text, JSON, or TOML. Every declared source must equal the requested release version. Release notes and the changelog heading must exist on the exact release SHA.

The reusable release workflow can explicitly provision release toolchains before invoking the build contract:

- `python_enabled`, `python_version`, and `uv_version` provision `uv` plus the requested Python runtime using a full-SHA-pinned setup action.
- `node_enabled`, `node_version`, and `pnpm_version` provision Node.js plus the requested pnpm release.
- Disabled toolchains are not provisioned. Consumers must enable only the runtimes needed by their release build.

The release build script receives:

- `RELEASE_VERSION`
- `RELEASE_TAG`
- `TARGET_SHA`
- `RELEASE_OUTPUT_DIR`
- `PRODKIT_RELEASE_PYTHON_VERSION`
- `PRODKIT_RELEASE_NODE_VERSION`
- `PRODKIT_RELEASE_PNPM_VERSION`

It must place a flat set of regular files in `RELEASE_OUTPUT_DIR`. Do not write `SHA256SUMS` or `release-metadata.json`; the central workflow owns those proof files. Do not create symlink payloads.

Release builds must use locked dependency installation where the ecosystem supports it. A consumer must not rely on mutable preinstalled language runtimes or package-manager versions on a self-hosted runner when the central toolchain inputs can provision them explicitly.
