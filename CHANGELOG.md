# Changelog

All notable changes to this repository are documented here.

## [0.0.0] - 2026-08-20

- Establish the ProdKit organization-wide workflow control plane.
- Add reusable CI, Security, Release, and organization-audit workflows.
- Add exact-SHA guarded release with immutable tags, draft-first publication, checksum verification, SPDX SBOM generation, and GitHub artifact provenance attestations.
- Provision explicitly versioned Python/uv and Node/pnpm toolchains for consumer release builds instead of relying on mutable self-hosted-runner state.
- Add a versioned consumer release manifest contract and bootstrap generator.
- Add importable organization main-branch and semantic release-tag rulesets that are disabled by default for safe incremental rollout.
- Add standalone repository and organization drift validators.
