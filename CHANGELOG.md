# Changelog

All notable changes to this repository are documented here.

## [0.1.5] - 2026-08-25

- Complete the normal release lifecycle so exact-main gate completion automatically reaches Trusted Release Proof, promotion, publication, independent verification, and merged release-branch cleanup without operator orchestration.
- Extend immutable Release Verification to dispatch canonical Branch Cleanup only after tag, release metadata/body, exact source, Release-run identity, remote assets, and `SHA256SUMS` all verify.
- Keep destructive ref mutation isolated in the existing Branch Cleanup workflow; Release Verification receives only `actions: write`, `contents: read`, and `pull-requests: read` so it can prove and dispatch cleanup but cannot delete refs itself.
- Infer exactly one same-repository merged release/hotfix PR branch from the immutable release commit, require the branch to still point to the merged PR head, and fail closed on ambiguity or post-merge branch movement.
- Permit cleanup after later `main` advancement only when the verified release SHA remains the merge base/ancestor, and bind destructive cleanup to the current default-branch SHA.
- Treat an already-absent release branch as idempotent cleanup success and retain every manual `workflow_dispatch` path as recovery-only fallback.
- Preserve the optional protected `release` environment as the single human publication-approval boundary; proof, promotion, verification, and cleanup remain automatic around it.
- Add a permanent regression contract for verified automatic cleanup and document coordinated consumer adoption of one immutable v0.1.5 lifecycle pin.

## [0.1.4] - 2026-08-23

- Bridge automatically dispatched proof to Release Promotion with an exact-source, bounded GitHub-hosted observer so v0.1.4 does not depend on a suppressed `workflow_run` edge.

- Add automatic release-intent detection after exact-main `CI`/`Security` completion without converting `Trusted Release Proof` away from its dispatch-only trust boundary.
- Add `reusable-release-proof-dispatch.yml` and generated `Release Proof Dispatch` callers. They run from successful default-branch gate completions, require the trigger SHA to still be current `main`, derive one canonical SemVer from the release manifest, and proceed only while that version is unpublished.
- Defer cleanly while another required exact-SHA gate is still queued/in progress, fail closed when a required gate has completed unsuccessfully, ignore stale-main completions, and avoid duplicate active/successful proof dispatches.
- Keep the automatic dispatcher GitHub-hosted, non-blocking, `contents: read`, and limited to `actions: write`; it cannot publish, tag, or mutate repository content.
- Keep `Trusted Release Proof` itself `workflow_dispatch` only and source-bound to `${{ github.sha }}`. The dispatcher validates that caller contract before invoking it on `main`, preserving the existing exact-proof authorization used by Release.
- Preserve the existing completion topology after proof: successful proof → `Release Promotion` → dispatch-only `Release` → protected `release` environment publication → immutable-tag `Release Verification`.
- Add bootstrap, organization-audit, workflow-inventory, and regression-test coverage so consumers must install and immutably pin the new automatic proof-dispatch stage together with the rest of the release workflow family.
- Include the v0.1.3 verification-dispatch interpolation fix and its regression guard in the next immutable consumer pin.

## [0.1.3] - 2026-08-23

- Fix automatic post-publication verification so it cannot be suppressed by GitHub's chained `workflow_run` depth limit.
- Add `reusable-release-verification-dispatch.yml`; Release invokes it only after publication succeeds, and it validates the exact parent Release run, immutable tag/source identity, and dispatch-only verification caller before triggering verification.
- Make generated `Release Verification` callers `workflow_dispatch` only, derive the source from `${{ github.sha }}` on the immutable tag, and remain read-only.
- Bind automatic verification to the exact parent Release run ID while preserving source identity without a manually copied SHA and manual recovery after a completed Release.
- Keep verification dispatch non-blocking and GitHub-hosted so it never waits while occupying a trusted product runner.
- Update organization audit, contract tests, lifecycle documentation, generated callers and release notes to enforce the verification-dispatch boundary.
- Keep the immutable `v0.1.2` release unchanged; v0.1.3 is the patch-level lifecycle correction discovered during v0.1.2 closure.

## [0.1.2] - 2026-08-23

- Add reusable exact-main post-gate branch-cleanup authorization without duplicating the v0.1.1 deletion engine.
- Keep `Branch Cleanup` explicitly `workflow_dispatch` only while adding an optional `expected_default_sha` handoff so upstream authorization and destructive cleanup remain bound to the same immutable default-branch revision.
- Add `reusable-gated-branch-cleanup.yml`, which accepts an exact reviewed branch list, requires a `workflow_run` from a default-branch push, verifies configurable exact-SHA workflow gates by immutable workflow path, and dispatches the permanent Branch Cleanup workflow only after all required gates are green.
- Defer safely when required gates are missing/in progress, fail closed on completed non-success gates, ignore stale-main triggers, and authorize dispatch only from the last completed required gate event to avoid normal CI/Security/CodeQL fan-out duplication.
- Verify the target cleanup workflow is `workflow_dispatch` only and exposes the exact-SHA reusable cleanup contract before dispatch; grant the authorization layer `actions: write` but not `contents: write`, so it cannot delete refs itself.
- Add permanent dormant `post-gate-branch-cleanup.yml` callers. They activate only when `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` contains a non-empty reviewed exact branch list and support an optional `PRODKIT_GATED_CLEANUP_GATES_JSON` exact workflow-path gate set.
- Extend bootstrap, organization audit, regression contracts, adoption guidance, and control-plane self-callers to enforce the two-layer cleanup topology and immutable central pinning.
- Preserve the v0.1.1 Branch Cleanup safety model unchanged: complete preflight, protected/default/open-PR rejection, exact target-SHA revalidation, repeated default-SHA checks, serialized deletion, idempotent absent refs, and post-delete absence verification.
- Keep `v0.1.0` and `v0.1.1` immutable; `v0.1.2` is an additive workflow-control-plane checkpoint.

## [0.1.1] - 2026-08-22

- Add centrally governed Branch Cleanup as a normative post-merge/post-release maintenance capability.
- Require cleanup to be explicitly dispatched with an exact JSON array of branch names, defaulting to dry-run on GitHub-hosted execution.
- Bind destructive cleanup to the reviewed default-branch SHA and reject the default branch, protected branches, malformed/duplicate targets, and branches that are heads of open pull requests.
- Revalidate default-branch identity, target protection, open-PR status, and exact target SHA immediately before deletion; verify every deleted ref is absent afterward and fail closed on races.
- Serialize repository cleanup runs and emit structured cleanup evidence for operator review.
- Add the canonical `branch-cleanup.yml` consumer caller to bootstrap output and make organization audit/contracts enforce the dispatch-only, exact-SHA-pinned cleanup architecture.
- Fix compact CI/Security cancellation handling so aggregate verifiers do not turn GitHub-cancelled superseded runs into false failures while genuine failures remain fail-closed.
- Align the README reusable-workload surface, generated caller list, lifecycle, and organization-audit guidance with the new cleanup contract.
- Keep `v0.1.0` immutable; `v0.1.1` is the next reviewed control-plane checkpoint for consumers to pin by exact commit SHA.

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