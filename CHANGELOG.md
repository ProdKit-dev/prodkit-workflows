# Changelog

All notable changes to this repository are documented here.

## [0.0.0] - 2026-08-20

- Establish the ProdKit organization-wide workflow control plane.
- Add reusable CI, Security, Release, Release Metadata, CodeQL, Release Proof, runner-policy, and organization-audit orchestration.
- Add compact CI and Security reusable workflows that execute enabled compatibility/scanning dimensions as steps inside one stable required job, reducing Actions job/check fan-out while preserving `ci / CI Required` and `security / Security Required`.
- Keep the original expanded CI/Security workflows available as backward-compatible parallel-matrix paths for already-pinned consumers or repositories requiring compatibility versions outside the compact organization set.
- Make generated consumers and the control-plane canary callers use compact CI/Security by default.
- Separate lifecycle stages: pull-request validation, main-branch certification, explicit release-candidate proof, immutable publication, and mutable Release metadata repair.
- Make `Trusted Release Proof` an explicit `workflow_dispatch` release-candidate gate instead of a workflow that re-runs on every pull request, main push, and release tag.
- Require publication to verify successful exact-SHA main `CI` and `Security` plus one successful dispatched `Trusted Release Proof` for the same current-main source SHA.
- Centralize hosted/self-hosted runner selection in `Reusable Runner Policy`; consumer callers no longer embed `runner-probe`, `fromJSON(...)`, self-hosted labels, or failover expressions.
- Keep hosted-first automatic failover available for `policy`/`auto`, preserve strict explicit hosted/self-hosted overrides, and force fork-originated pull requests onto the hosted lane when fork safety is enabled.
- Add reusable CodeQL matrix orchestration with repository-owned SARIF policy adapters.
- Add reusable current-release metadata selection and optional organization-style normalization of published SemVer Release names while preserving bodies, publication flags, tags, and asset identity.
- Add exact-SHA guarded release with immutable tags, draft-first publication, checksum verification, SPDX SBOM generation, and GitHub artifact provenance attestations.
- Add guarded release metadata repair for already-published immutable tags: canonical Release name/body may be reconciled from current manifest/version docs only after the tag SHA and complete published checksum set verify, and the workflow proves publication flags and asset identity remain unchanged afterward.
- Provision explicitly versioned Python/uv and Node/pnpm toolchains for consumer release builds instead of relying on mutable self-hosted-runner state.
- Add a versioned consumer release manifest contract and bootstrap generator.
- Bootstrap CI, Security, Trusted Release Proof, Release, and Release Metadata callers by default; CodeQL is opt-in with `--include-codeql`.
- Make organization audit validate all five default lifecycle callers and their correct central workflow families, including the Release pipeline and Release Metadata selector.
- Add importable organization main-branch and semantic release-tag rulesets that are disabled by default for safe incremental rollout.
- Add standalone repository and organization drift validators.
- Enforce adapter containment beneath `.prodkit/workflows/` instead of relying on string-prefix matching.
- Enforce the complete release-manifest v1 shape at runtime, including required non-empty version sources and rejection of unknown fields.
- Reject empty, nested, symlinked, or central-proof-name consumer release payloads before source archives, SBOMs, metadata, and checksums are added.
- Preserve redacted full-history Gitleaks JSON evidence and support repository-contained reviewed Gitleaks allowlist configuration.
- Lock lifecycle boundaries, reusable workflow behavior, bootstrap output, manifest schema, runner semantics, compact execution, and local validators together with regression tests.
- Maintain an exact control-plane surface of 16 GitHub workflows, a 13-file consumer adapter catalog, and the 4 adapters enabled by the control-plane repository itself.
