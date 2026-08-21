# Changelog

All notable changes to this repository are documented here.

## [0.0.0] - 2026-08-20

- Establish the ProdKit organization-wide reusable workflow control plane.
- Add compact CI and Security workflows that execute enabled dimensions as steps inside one stable required job: `ci / CI Required` and `security / Security Required`.
- Keep expanded CI/Security workflows available as backward-compatible parallel-matrix paths.
- Make runner selection a direct caller responsibility through `runner_json`; generated callers no longer add a hosted probe, runner resolver, workspace-preflight controller, or `PRODKIT_RUNNER_MODE` state machine.
- Default trusted generated work to `["self-hosted","Linux","X64"]`, allow a complete `PRODKIT_RUNNER_JSON` override, and force fork-originated CI/Security PRs to GitHub-hosted execution.
- Retain `reusable-runner-policy.yml` only for already-pinned historical consumers.
- Separate lifecycle stages: pull-request validation, exact-main certification, explicit release-candidate proof, immutable publication, and mutable Release metadata repair.
- Make `Trusted Release Proof` dispatch-only and certify `${{ github.sha }}` directly so operators do not copy a source SHA between workflows.
- Make generated `Release` dispatch-only, publish `${{ github.sha }}` directly, require successful exact-SHA `CI`/`Security` push evidence, and explicitly verify a successful exact-SHA `Trusted Release Proof` before publication.
- Make new generated Release callers invoke `reusable-release.yml` directly; retain `reusable-release-pipeline.yml` only for backward compatibility.
- Add guarded immutable release publication with version/manifest validation, product build adapters, source archive, SPDX SBOM, checksums, provenance attestation, immutable tags, draft-first publication, and remote asset verification.
- Add guarded Release metadata repair that can reconcile canonical name/body while proving tag/source/payload identity is unchanged.
- Add reusable CodeQL and organization audit workloads.
- Make organization audit require the direct workflow families and reject retired runner-controller usage, floating central refs, obsolete SHAs, missing proof gating, and local publication implementations.
- Add a versioned consumer release manifest contract and bootstrap generator for CI, Security, Trusted Release Proof, Release, Release Metadata, and optional CodeQL.
- Enforce adapter containment beneath `.prodkit/workflows/`, release-manifest shape, payload safety, redacted security evidence, and immutable central pins with regression tests.
- Preserve backward compatibility for consumers pinned to earlier workflow-controller revisions while making direct workload execution normative for new consumers.
