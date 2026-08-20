# Changelog

All notable changes to this repository are documented here.

## [0.0.0] - 2026-08-20

- Establish the ProdKit organization-wide workflow control plane.
- Add reusable CI, Security, Release, and organization-audit workflows.
- Add exact-SHA guarded release with immutable tags, draft-first publication, checksum verification, SPDX SBOM generation, and GitHub artifact provenance attestations.
- Add guarded release metadata repair for already-published immutable tags: canonical Release name/body may be reconciled from current manifest/version docs only after the tag SHA and complete published checksum set verify, and the workflow proves publication flags and asset identity remain unchanged afterward.
- Provision explicitly versioned Python/uv and Node/pnpm toolchains for consumer release builds instead of relying on mutable self-hosted-runner state.
- Add a versioned consumer release manifest contract and bootstrap generator.
- Add importable organization main-branch and semantic release-tag rulesets that are disabled by default for safe incremental rollout.
- Add standalone repository and organization drift validators.
- Make GitHub-hosted Ubuntu the default reusable CI, Security, Release, and organization-audit execution target while retaining trusted self-hosted execution.
- Add policy-driven runner selection through `PRODKIT_RUNNER_MODE`, with organization/repository configuration and forced GitHub-hosted execution for fork pull requests.
- Extend CI/Security runner mode with strict `both` execution: GitHub-hosted and self-hosted run the same complete reusable contract independently and both must pass.
- Preserve stable organization checks `ci / CI Required` and `security / Security Required` across GitHub-hosted, self-hosted, and `both` modes through caller-level policy gates.
- Keep Release and Organization Audit single-runner so publication transactions cannot race and duplicate audits do not consume both runner pools.
- Accept successful exact-SHA `workflow_dispatch` required-workflow evidence for Release in addition to normal `push` evidence, making trusted self-hosted quota/capacity redispatch releasable while still rejecting PR-only evidence.
- Enforce adapter containment beneath `.prodkit/workflows/` instead of relying on string-prefix matching.
- Enforce the complete release-manifest v1 shape at runtime, including required non-empty version sources and rejection of unknown fields.
- Reject empty, nested, symlinked, or central-proof-name consumer release payloads before source archives, SBOMs, metadata, and checksums are added.
- Preserve redacted full-history Gitleaks JSON evidence and support repository-contained reviewed Gitleaks allowlist configuration.
- Lock `docs/CONTRACTS.md`, reusable workflow behavior, bootstrap output, manifest schema, runner-mode semantics, metadata-repair behavior, and local validators together with regression tests.
- Clarify the three workflow-related repository layers: 9 GitHub workflow YAMLs, an 11-file consumer adapter catalog, and the 4 adapters enabled by the control-plane repository itself.
- Make contract tests assert the exact workflow, template-adapter, generated-adapter, and self-adapter file sets rather than accepting an approximate adapter count.
