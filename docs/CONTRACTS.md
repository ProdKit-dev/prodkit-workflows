# Consumer Contracts

This document is normative for consumers of `ProdKit-dev/prodkit-workflows`. Reusable workflows, caller templates, bootstrap output, validators, and contract tests must implement the same guarantees.

## Ownership

`prodkit-workflows` owns organization workflow orchestration. Consumer repositories own configuration, `.prodkit/release.json`, canonical version notes, and repository-specific adapters beneath `.prodkit/workflows/`.

Consumers must not duplicate organization infrastructure such as hosted/self-hosted routing expressions, runner labels, CI/Security aggregators, CodeQL orchestration, exact-source proof orchestration, release publication state machines, or GitHub Release metadata mutation logic.

The control-plane workflow surface includes:

- `reusable-runner-policy.yml`;
- `reusable-ci.yml`;
- `reusable-security.yml`;
- `reusable-codeql.yml`;
- `reusable-release-proof.yml`;
- `reusable-release-pipeline.yml`;
- `reusable-release.yml`;
- `reusable-release-metadata-current.yml`;
- `reusable-release-metadata.yml`;
- `reusable-org-audit.yml`;
- the repository's own thin CI, Security, Release, and Organization Audit callers.

All cross-repository reusable workflow calls must pin an exact lowercase 40-character Git commit SHA. Floating branches and tags are not production contracts.

## Lifecycle

The standard lifecycle is deliberately separated:

1. **Pull request** — run normal `CI`, `Security`, and optional `CodeQL` feedback.
2. **Main branch** — run `CI`, `Security`, and optional `CodeQL` for the actual merge SHA.
3. **Release candidate** — explicitly dispatch `Trusted Release Proof` once for the intended current-main SHA.
4. **Publication** — explicitly dispatch `Release`; publication verifies prior exact-SHA evidence before building, attesting, tagging, and publishing.
5. **Metadata repair** — reconcile mutable GitHub Release presentation separately from immutable source/payload identity.

`Trusted Release Proof` must not be triggered by every pull request, ordinary main push, or `v*` tag. Tag creation must not rerun an already successful proof for the same source SHA.

The release pipeline requires successful exact-SHA main-branch `CI` and `Security` plus one successful `workflow_dispatch` run of `Trusted Release Proof` for the same current-main SHA.

## Runner policy

`Reusable Runner Policy` is the only organization implementation of runner selection. Thin consumers request `policy`, `auto`, `github-hosted`, or `self-hosted` and consume its `runner_json` output.

`PRODKIT_RUNNER_MODE` is a non-secret organization/repository Actions variable:

- unset or `auto`: hosted-first automatic failover;
- `github-hosted`: strict hosted execution;
- `self-hosted`: strict trusted self-hosted execution.

For `auto`, the policy performs a repository-code-free hosted availability probe. If it emits `available=true`, the hosted lane is selected; otherwise the trusted self-hosted lane is selected. Genuine product/test/security/release failures never trigger runner switching because routing completes before the workload starts.

Fork-originated pull requests are forced to the hosted lane when `fork_safe` is enabled. Release operations are not fork-PR entry points and may set `fork_safe: false`.

Consumers must not contain `runner-probe`, `needs.runner-probe`, `fromJSON(...)` runner-selection expressions, or hard-coded `["self-hosted","Linux","X64"]` labels. Those are control-plane implementation details.

GitHub Actions has no native ordered `runs-on` fallback and cannot safely react to a job that remains indefinitely queued. Hosted-first fallback therefore covers failures where the hosted probe fails to produce its positive output; it does not bypass a complete Actions outage.

## CI

`reusable-ci.yml` owns matrix execution, checkout, adapter containment checks, and the stable `CI Required` aggregator. Enabled adapters must be regular non-symlink files beneath `.prodkit/workflows/`.

Available adapters are:

- `ci-hygiene.sh`;
- `ci-python.sh`, receiving `PRODKIT_PYTHON_VERSION`;
- `ci-node.sh`, receiving `PRODKIT_NODE_VERSION`;
- `ci-postgres.sh`, receiving isolated PostgreSQL connection variables;
- `ci-container.sh`;
- `ci-custom.sh`.

Disabled capabilities may be skipped. Any enabled capability must succeed for `CI Required` to pass.

## Security

`reusable-security.yml` owns full-history Gitleaks, source SPDX 2.3 SBOM generation, dependency-audit adapters, container vulnerability scanning, custom security adapters, evidence artifacts, and the stable `Security Required` aggregator.

Repository adapters are:

- `security-python.sh`;
- `security-node.sh`;
- `security-container-build.sh`;
- `security-custom.sh`.

A repository may provide a narrowly reviewed repository-contained Gitleaks configuration. Enabled adapter paths are containment-checked beneath `.prodkit/workflows/`.

## CodeQL

`reusable-codeql.yml` owns the language matrix, CodeQL initialization/analysis, SARIF evidence retention, and the `CodeQL Required` aggregator. Repositories may supply `.prodkit/workflows/codeql-check.sh` to enforce their SARIF policy.

CodeQL is opt-in for repositories that require it. It is not implicitly added to every ProdKit repository.

## Trusted Release Proof

`reusable-release-proof.yml` accepts an exact `source_sha`, requires that SHA to remain current `main`, checks out that exact commit, validates a repository-owned proof adapter beneath `.prodkit/workflows/`, runs it on the resolved trusted runner, verifies tracked source remained immutable, writes a canonical proof receipt, and uploads exact-SHA proof evidence.

The repository adapter is normally `.prodkit/workflows/release-proof.sh`. Domain-specific browser, database, container, packaging, quality, or protocol acceptance belongs there; YAML orchestration and exact-source guarantees belong centrally.

The proof workflow itself is explicitly dispatched. A successful run on another SHA, pull-request event, ordinary main push, or tag event is not release-candidate evidence.

## Release manifest and presentation

`.prodkit/release.json` schema version 1 defines version sources, canonical notes, changelog heading, release build adapter, and Release name template. Unknown properties are rejected.

The organization release-presentation contract follows the ProdKit Quality reference:

- tag: `vX.Y.Z`;
- GitHub Release name: `ProdKit <Repository Name> vX.Y.Z`;
- canonical note begins `# vX.Y.Z — <milestone>`;
- Release body is the complete canonical `docs/VX.Y.Z.md` document.

Quality is a release-presentation reference, not a runner-policy consumer.

## Publication

`reusable-release-pipeline.yml` first verifies a successful dispatched `Trusted Release Proof` for the exact target SHA. It then delegates immutable publication to `reusable-release.yml`, which independently requires successful main `CI` and `Security` for exactly the same SHA.

Publication is dispatch-only. `target_sha` must be a full lowercase 40-character SHA and still equal current configured `main`.

The consumer `release-build.sh` owns product distributables only and writes at least one flat regular payload into `RELEASE_OUTPUT_DIR`. The central workflow owns source archives, repository SBOM, release metadata, `SHA256SUMS`, attestations, immutable tag/release transaction, and remote verification.

A release tag is immutable. An existing tag on another commit is a hard failure. Publication is retry-safe and draft-first. Every uploaded asset is read back and verified before publication; after publication the complete remote asset set and every checksum are independently verified again.

## Metadata repair

`reusable-release-metadata-current.yml` selects either an explicit published version/source pair or the current workspace version/tag, then delegates to guarded `reusable-release-metadata.yml`.

Metadata repair uses current `main` only as the canonical presentation source. It requires the existing immutable tag to resolve exactly to the supplied historical `source_sha`, verifies the published `SHA256SUMS` and every payload, snapshots asset identity/publication flags, PATCHes only Release `name` and `body`, then re-verifies the tag, assets, checksums, draft/prerelease state, and canonical presentation.

When explicitly enabled, current-release metadata orchestration may also normalize every published SemVer Release **name** from `release.name_template`. That operation snapshots and preserves each release body, tag, publication flags, and asset identity; it changes no payload and no historical note body.

Metadata repair cannot create or move tags, create a missing Release, rebuild/upload/delete/replace assets, alter checksums, or change draft/prerelease state.

## Bootstrap surface

`bootstrap_consumer.py` installs thin callers for CI, Security, Trusted Release Proof, Release, and Release Metadata, plus the complete adapter catalog. `--include-codeql` additionally installs the CodeQL caller.

Generated callers contain only lifecycle triggers, minimal repository capability configuration, a call to `Reusable Runner Policy`, and the appropriate reusable workflow call. Runner implementation details must remain absent.
