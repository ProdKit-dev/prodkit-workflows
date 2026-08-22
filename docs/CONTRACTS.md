# Consumer Contracts

This document is normative for consumers of `ProdKit-dev/prodkit-workflows`. Reusable workflows, caller templates, bootstrap output, validators, organization audit, and contract tests must implement the same guarantees.

## Ownership boundary

`prodkit-workflows` owns reusable workload implementation: CI/Security aggregation, toolchain setup, evidence generation, exact-source proof mechanics, guarded publication, metadata repair, CodeQL orchestration, and organization audit.

Consumer repositories own:

- workflow triggers and direct runner target selection;
- `.prodkit/release.json`;
- canonical version notes/changelog;
- repository-specific adapters beneath `.prodkit/workflows/`.

New consumers **must not** insert a runner-controller workflow between their caller and the reusable workload. They pass `runner_json` directly.

All cross-repository reusable workflow calls must pin an exact lowercase 40-character Git commit SHA.

## Reusable surface

Normative reusable workloads:

- `reusable-ci-compact.yml` — default compact CI;
- `reusable-security-compact.yml` — default compact Security;
- `reusable-ci.yml` — expanded compatibility CI;
- `reusable-security.yml` — expanded compatibility Security;
- `reusable-codeql.yml`;
- `reusable-release-proof.yml`;
- `reusable-release.yml`;
- `reusable-release-metadata-current.yml`;
- `reusable-release-metadata.yml`;
- `reusable-org-audit.yml`.

Compatibility-only surfaces retained for already-pinned consumers:

- `reusable-runner-policy.yml`;
- `reusable-release-pipeline.yml`.

Bootstrap and organization audit must not require new consumers to use those compatibility-only controllers.

## Direct runner contract

Generated callers may read the non-secret Actions variable `PRODKIT_RUNNER_JSON`. Its value is the complete JSON value accepted by GitHub `runs-on`, for example:

```json
["self-hosted","Linux","X64"]
```

When unset, trusted generated workloads default to that self-hosted label set.

Generated CI/Security callers force fork-originated pull requests to `"ubuntu-latest"`. Persistent trusted runners must not execute fork code by default.

New callers must not contain:

- `PRODKIT_RUNNER_MODE`;
- a `runner` prerequisite job whose sole purpose is routing;
- `needs.runner.outputs.runner_json`;
- hosted availability probes or automatic failover state machines.

A workload gets one runner target. Product/security/release failures never cause automatic execution on a second trust boundary.

## Lifecycle

1. **Pull request** — CI, Security, optional CodeQL.
2. **Main** — exact-main CI and Security certify the merge SHA.
3. **Release candidate** — explicitly dispatch `Trusted Release Proof` on the intended current `main`; it certifies `${{ github.sha }}`.
4. **Publication** — proof promotion dispatches `Release` on the same current `main`; the central publisher verifies prior exact-SHA evidence and publishes `${{ github.sha }}`.
5. **Verification** — `Release Verification` independently checks the immutable published transaction.
6. **Metadata repair** — independently reconcile mutable Release name/body while proving immutable source/payload identity is unchanged.

Operators do not manually copy source/target SHAs between proof and release workflows.

## CI

Generated consumers use `reusable-ci-compact.yml` by default. It owns checkout, adapter containment, toolchain provisioning, compatibility selection, PostgreSQL isolation, and final aggregate outcome evaluation.

Available adapters:

- `ci-hygiene.sh`;
- `ci-python.sh` with `PRODKIT_PYTHON_VERSION`;
- `ci-node.sh` with `PRODKIT_NODE_VERSION`;
- `ci-postgres.sh` with isolated PostgreSQL connection variables;
- `ci-container.sh`;
- `ci-custom.sh`.

Compact CI supports Python `3.12`, `3.13`, `3.14` and Node `20`, `22`, `24`. Duplicate or unsupported requested versions fail closed.

Enabled dimensions run as steps inside one reusable job named `CI Required`. Intermediate steps may continue after failure only to collect more evidence; the final verifier fails if any enabled control failed.

`reusable-ci.yml` is the deliberate expanded/parallel compatibility path.

## Security

Generated consumers use `reusable-security-compact.yml` by default. It owns checkout, full-history Gitleaks, dependency-audit adapters, source SPDX SBOM, container vulnerability scan, custom security, evidence uploads, and final aggregate verification.

Repository adapters:

- `security-python.sh`;
- `security-node.sh`;
- `security-container-build.sh`;
- `security-custom.sh`.

Enabled controls must all pass. `continue-on-error` on intermediate evidence stages does not make a failed required control green.

`reusable-security.yml` remains the expanded compatibility path.

## Stable required checks

The required branch-protection identities are:

- caller job `ci` + reusable job `CI Required` => `ci / CI Required`;
- caller job `security` + reusable job `Security Required` => `security / Security Required`.

Do not require individual compatibility/scanning steps as branch-protection checks.

## CodeQL

`reusable-codeql.yml` owns the language matrix, initialization/analysis, SARIF evidence, and `CodeQL Required` aggregation. A repository may provide `.prodkit/workflows/codeql-check.sh` for its SARIF acceptance policy.

CodeQL is opt-in. Generated CodeQL callers do not execute fork PRs on persistent trusted runners.

## Trusted Release Proof

`reusable-release-proof.yml` accepts an exact `source_sha`, verifies it remains current configured `main`, checks out that exact source, provisions the requested baseline toolchains, validates the repository proof adapter, runs it, confirms tracked source remained immutable, and uploads a canonical proof receipt/evidence artifact.

The generated caller supplies:

```yaml
source_sha: ${{ github.sha }}
```

The proof caller is `workflow_dispatch` only. A proof on another SHA/event does not satisfy publication.

## Publication

New generated Release callers call `reusable-release.yml` directly. They do not use `reusable-release-pipeline.yml`, do not implement a local API proof gate, and do not implement publication logic.

The generated caller supplies:

```yaml
target_sha: ${{ github.sha }}
proof_workflow_file: .github/workflows/trusted-release-proof.yml
```

The central publisher owns proof authorization. It verifies that `proof_workflow_file` has a successful `workflow_dispatch` run for the exact target SHA, independently requires successful exact-SHA `push` runs for `CI` and `Security`, and verifies the target is still current `main`. Dynamic workflow display names are never authorization identities.

Publication is split into resumable jobs:

- **prepare** validates source/evidence/manifest state and recognizes an already-complete published release;
- **build** runs the repository build adapter, validates the consumer payload, adds source/SBOM evidence, creates `release-metadata.json` and `SHA256SUMS`, and uploads the resulting **sealed payload** as a workflow artifact;
- **attest** optionally downloads and attests the same sealed payload;
- **publish** downloads that sealed payload, creates or recovers the immutable tag/draft Release, retains already-correct draft assets, uploads only missing or mismatched assets, verifies the draft, and makes it public.

Successful job boundaries are checkpoints. If attestation or publication fails after the build succeeded, operators use GitHub **Re-run failed jobs**; the successful build job is not repeated and downstream jobs reuse its sealed workflow artifact. A failed publication resumes a compatible draft rather than unconditionally deleting and re-uploading all assets.

GitHub Artifact Attestations are capability-dependent and therefore opt-in in both the direct publisher and retained compatibility pipeline. The default release contract does not require them. When explicitly enabled, attestation failure remains release-fatal. Exact-source proof, SBOM generation, `SHA256SUMS`, sealed-payload verification, and draft asset read-back remain required independently of attestation support.

The publisher verifies the draft before publication. Independent post-publication checksum/digest verification belongs to `Release Verification`; it is not duplicated in the publisher.

Tag movement is forbidden. An existing tag on another commit fails hard. A verified already-published release is treated idempotently.

## Release manifest

`.prodkit/release.json` schema version 1 defines version sources, canonical notes/changelog, release-build adapter, artifact directory, source-archive policy, and Release name template. Unknown properties are rejected.

The visible organization contract is:

- tag `vX.Y.Z`;
- canonical GitHub Release title defined by the repository manifest;
- canonical version document begins `# vX.Y.Z — <milestone>`;
- GitHub Release body equals the canonical version document.

## Metadata repair

`reusable-release-metadata-current.yml` selects an explicit published version/source pair or the current workspace version/tag, then delegates to `reusable-release-metadata.yml`.

Repair verifies the immutable tag and complete published checksum set before changing mutable presentation. It may patch canonical Release `name` and `body`, then re-verifies tag, publication flags/timestamp where applicable, asset identity, digests, and payload checksums.

It cannot create/move tags, create a missing Release, rebuild/upload/delete/replace assets, alter checksums, or change draft/prerelease state.

## Bootstrap surface

`bootstrap_consumer.py` installs callers for:

- CI;
- Security;
- Trusted Release Proof;
- Release;
- Release Verification;
- Release Metadata;
- optionally CodeQL.

Generated callers directly invoke the appropriate reusable workload and directly provide `runner_json`. CI/Security use compact workflows by default.

## Organization audit

The organization auditor requires these workflow families at the requested immutable central SHA:

- `ci.yml` -> `reusable-ci-compact.yml`;
- `security.yml` -> `reusable-security-compact.yml`;
- `trusted-release-proof.yml` -> `reusable-release-proof.yml`;
- `release.yml` -> `reusable-release.yml`;
- `release-verification.yml` -> `reusable-release-verification.yml`;
- `release-metadata.yml` -> `reusable-release-metadata-current.yml`.

It also rejects floating references, retired runner-controller usage, manually copied release target semantics, duplicated consumer proof gates, missing central proof delegation, and local publication implementation in consumer `release.yml`.

## Compatibility policy

Already-pinned consumers remain immutable and may continue using `reusable-runner-policy.yml` or `reusable-release-pipeline.yml` until deliberately migrated. The retained compatibility release pipeline delegates to the same central proof authorization and resumable publisher rather than maintaining a second implementation. New bootstrap output and current organization policy use the direct-runner architecture.
