# Consumer Contracts

This document is normative for consumers of `ProdKit-dev/prodkit-workflows`. The reusable workflows, generated caller templates, bootstrap output, local validators, and contract tests must implement the same guarantees. A change to one without the corresponding contract/test change is drift.

## Repository layers and file ownership

`prodkit-workflows` deliberately has three different workflow-related surfaces. They are not expected to contain the same number of files.

| Surface | Purpose | Canonical files |
| --- | --- | --- |
| `.github/workflows/` | Executable GitHub Actions callers plus reusable workflow implementations owned by this control-plane repository | `ci.yml`, `security.yml`, `release.yml`, `org-audit.yml`, `reusable-ci.yml`, `reusable-security.yml`, `reusable-release.yml`, `reusable-org-audit.yml` |
| `templates/consumer/.prodkit/workflows/` | Complete consumer adapter catalog emitted by bootstrap | `ci-hygiene.sh`, `ci-python.sh`, `ci-node.sh`, `ci-postgres.sh`, `ci-container.sh`, `ci-custom.sh`, `security-python.sh`, `security-node.sh`, `security-container-build.sh`, `security-custom.sh`, `release-build.sh` |
| `.prodkit/workflows/` | Adapters that this repository itself currently enables when testing/releasing the control plane | `ci-hygiene.sh`, `ci-custom.sh`, `security-custom.sh`, `release-build.sh` |

The adapter sections below define the **available consumer interfaces**, not a requirement that every repository keep every adapter file active. A consumer may delete or omit an adapter only when the corresponding capability is disabled in its caller. If a capability is enabled, its configured adapter must exist and satisfy this contract.

The control-plane repository itself intentionally has only four `.prodkit/workflows/` files because its own CI disables Python, Node, PostgreSQL, and container adapters, while its own Security disables Python, Node, and container adapters. Central Gitleaks and source-SBOM jobs do not require consumer adapter files. `release-build.sh` is always repository-owned when Release is used.

The GitHub Actions UI normally surfaces the four top-level control-plane workflows (`CI`, `Security`, `Release`, and `Organization Audit`) as operator-facing workflows. The four `reusable-*.yml` files are implementation entry points invoked through `workflow_call`; they are not additional product-level workflow concepts.

## Control-plane pinning and runners

Consumer repositories must call reusable workflows through an exact lowercase 40-character Git commit SHA. Floating branches and tags are not an accepted production contract.

GitHub-hosted Ubuntu is the normal/default execution target for CI, Security, and Release. Thin callers may expose an explicit `github-hosted` / `self-hosted` dispatch choice and may pass `["self-hosted","Linux","X64"]` for trusted failover. Automatic pull-request execution in the public workflow repository must never send fork-originated code to a persistent self-hosted runner.

GitHub Actions does not provide ordered `runs-on` fallback. Hosted-to-self-hosted failover is therefore an explicit redispatch of the same source SHA, not a claim of transparent native fallback.

CI and Security concurrency belongs to the thin caller so independent calls to the same reusable workflow can coexist. Reusable Release owns a version-scoped non-cancelling concurrency lock.

## Adapter path contract

Every **enabled** CI or Security adapter path must resolve to a regular, non-symlink file beneath the checked-out repository's `.prodkit/workflows/` directory. Absolute paths, traversal outside that directory, and symlink files are rejected before execution.

Disabled capabilities do not require their adapter file to exist. They are represented by GitHub Actions as `skipped`; an enabled capability must finish `success` to satisfy the final aggregator.

## CI adapters

The reusable CI contract exposes these optional consumer adapters:

- `ci-hygiene.sh`: repository structure, architecture, generated-file, migration immutability, documentation, and release metadata checks.
- `ci-python.sh`: receives `PRODKIT_PYTHON_VERSION` and owns dependency sync plus Python checks for that version.
- `ci-node.sh`: receives `PRODKIT_NODE_VERSION` and owns package-manager install/build/test behavior.
- `ci-postgres.sh`: receives `PRODKIT_POSTGRES_HOST`, `PRODKIT_POSTGRES_PORT`, `PRODKIT_POSTGRES_DATABASE`, `PRODKIT_POSTGRES_USER`, and `PRODKIT_POSTGRES_PASSWORD` for an isolated PostgreSQL service.
- `ci-container.sh`: production image build/runtime smoke.
- `ci-custom.sh`: domain-specific gates.

The stable final job is `CI Required`. It accepts only `success` or `skipped` for every declared capability and fails closed on any other result.

## Security adapters and central evidence

The reusable Security contract exposes these optional consumer adapters:

- `security-python.sh`: Python runtime dependency audit.
- `security-node.sh`: Node runtime dependency audit.
- `security-container-build.sh`: must build the image named by `PRODKIT_SECURITY_IMAGE`; the central workflow performs the vulnerability scan.
- `security-custom.sh`: domain-specific security assertions.

Full-history Gitleaks scanning and source SBOM generation are centrally owned. The Gitleaks scan is redacted and preserves a JSON evidence artifact even on failure. A consumer may provide an optional repository-relative `gitleaks_config_path` for reviewed false-positive allowlists; the config must be a regular, non-symlink file contained in the repository. The allowlist remains consumer-owned and must be narrowly scoped rather than disabling the central detector.

The source SBOM must be SPDX 2.3. Container vulnerability scanning is centrally owned after `security-container-build.sh` produces the requested image.

The stable final job is `Security Required`. It accepts only `success` or `skipped` and fails closed on any other result.

## Release manifest

`.prodkit/release.json` is schema version 1 and must conform to `contracts/release-manifest.schema.json`: required blocks are `schema_version`, `version`, `notes`, and `build`; unknown properties are rejected. `version.sources` must contain at least one source. Version sources may be text, JSON, or TOML, and every declared source must equal the requested release version on the exact target SHA.

Release-note and changelog paths must remain inside the checked-out repository. The rendered release notes file and changelog heading must exist on the exact release SHA. The release build script must be a regular, non-symlink file contained in the repository.

## Release source and evidence preconditions

Release is dispatch-only. `target_sha` must be a full lowercase 40-character SHA, must be the checked-out commit, and must still be the current configured main branch before publication proceeds.

`required_workflows_json` is a non-empty array of workflow names. Every listed workflow must have a completed successful `push` run for exactly `target_sha`. Pull-request success, a success on another SHA, or a still-running workflow does not satisfy release evidence.

## Release toolchains and build adapter

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

Release builds must use locked dependency installation where the ecosystem supports it. A consumer must not rely on mutable preinstalled language runtimes or package-manager versions on a self-hosted runner when the central toolchain inputs can provision them explicitly.

## Release artifact ownership

The consumer build adapter must place at least one payload in `RELEASE_OUTPUT_DIR`. Its output must be a flat set of regular, non-symlink files. Directories, symlinks, and an empty consumer payload set are rejected before central proof files are added.

The following names are central-workflow-owned and must not be emitted by the consumer build adapter:

- `SHA256SUMS`
- `release-metadata.json`
- `repository.spdx.json`
- the exact source archive name `<repository>-<tag>.tar.gz`

The central workflow may add the exact Git source archive and SPDX SBOM, then writes `release-metadata.json` and `SHA256SUMS`. It rechecks that the final artifact directory contains only flat regular files and verifies `SHA256SUMS` locally before publication.

## Release publication state machine

A release tag is immutable: an existing tag on another commit is a hard failure. Publication is retry-safe and draft-first. A workflow-owned draft for the same tag is reconciled deterministically; multiple releases for one tag require manual reconciliation.

Before publishing, every uploaded draft asset is read back and verified against its local SHA-256 digest. After publication, `SHA256SUMS` is treated as the published authority: the complete remote asset set and every payload checksum are verified again, including GitHub's asset digest metadata when GitHub supplies it.

When enabled, provenance attestation is generated from the central checksum file. Re-running an already published release is idempotent only if the immutable tag, complete asset set, `SHA256SUMS`, downloaded payload hashes, and available GitHub digest metadata all verify.
