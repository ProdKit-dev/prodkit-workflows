# Changelog

All notable changes to this repository are documented here.

## [0.1.0] - 2026-08-22

- Promote the organization workflow control plane from bootstrap status to the first stable operational release.
- Make compact CI and Security the normative generated path while preserving stable required-check identities and backward-compatible expanded workflows.
- Keep runner selection direct and deterministic through `runner_json`, with trusted self-hosted defaults, explicit override support, and fork isolation.
- Remove duplicated expensive release work: permanent exact-SHA CI/Security are verified as evidence instead of rerun by Trusted Release Proof.
- Build the repository-owned promotable release payload exactly once during proof and bind it to a digest receipt.
- Make Release import the exact proof-produced payload instead of rebuilding the same artifacts.
- Split publication into resumable prepare, build/seal, optional-attestation, and publish jobs so GitHub `Re-run failed jobs` can resume late failures without restarting successful work.
- Make draft recovery incremental, preserving already-correct assets and replacing only missing or checksum-mismatched payloads.
- Centralize exact-SHA proof authorization in the reusable publisher and remove copied proof-gate implementations from generated callers and compatibility wrappers.
- Require Trusted Release Proof to complete fully before promotion starts; promotion now runs in a separate `workflow_run`-triggered `Release Promotion` workflow.
- Keep promotion non-blocking and single-runner-safe: it dispatches Release idempotently and never polls a child workflow while holding a runner.
- Add independent read-only Release Verification after publication.
- Make GitHub Artifact Attestations capability-dependent and disabled by default while preserving fail-closed source, checksum, SBOM, and publication verification.
- Align generated callers, bootstrap, organization audit, lifecycle contracts, security model, and adoption guidance with proof-once / publish-once semantics.
- Update adoption guidance so operators wait for automatic `Release Promotion` after proof instead of manually dispatching a duplicate Release.
- Preserve compatibility entry points for older pinned consumers without allowing them to redefine the new normative lifecycle.

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
