# ProdKit workflow lifecycle

`prodkit-workflows` centralizes reusable workload implementation. Consumer repositories keep thin callers, choose their runner directly, and own product-specific adapters and release metadata.

## Lifecycle

| Stage | Trigger | Purpose |
| --- | --- | --- |
| Pull request | `pull_request` | CI, Security, optional CodeQL feedback before merge |
| Exact main | `push` to `main` | Certify the actual merged SHA |
| Release proof authorization | `workflow_run` after permanent gates | Detect an unpublished canonical version and dispatch proof |
| Trusted Release Proof | `workflow_dispatch` | Recheck exact-source gates, run release-only acceptance, build promotable payload once |
| Promotion | dependent job after proof by default | Dispatch Release only after proof succeeds |
| Publication | `workflow_dispatch` | Import/seal proof payload and publish behind optional `release` environment approval |
| Verification | `workflow_dispatch` on immutable tag | Independently verify source, metadata, assets and checksums |
| Cleanup authorization | dormant `workflow_run` | Authorize a reviewed exact branch set after configured gates |
| Branch Cleanup | `workflow_dispatch` | Revalidate and delete only exact reviewed refs |
| Metadata repair | explicit/current metadata path | Repair mutable Release presentation without changing immutable payload identity |

## Runner ownership

Reusable workloads accept `runner_json`; callers choose the execution target. Trusted generated work defaults to `["self-hosted","Linux","X64"]` and may be overridden by the non-secret repository variable `PRODKIT_RUNNER_JSON`.

Fork-originated CI/Security pull requests remain isolated from persistent trusted runners. There is no automatic runner failover: runner availability is infrastructure state, not a reason to switch trust boundaries after a workload has started.

Starting in v0.1.6, the normal control plane no longer requires GitHub-hosted capacity. Release proof dispatch, serialized promotion, Release verification dispatch, Branch Cleanup, and Post-Gate Branch Cleanup all use the configured trusted runner. Installations that deliberately want the v0.1.5-style hosted proof observer may set `PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true`.

## Single-runner non-blocking rule

The lifecycle must remain correct with one trusted self-hosted runner. A job occupying that runner must never dispatch another workflow that also needs the runner and then poll, sleep, or wait for the child. That pattern can deadlock indefinitely because the parent owns the only execution slot required by the child.

The v0.1.6 normal path therefore uses **serialized proof-to-promotion** rather than a polling bridge:

1. exact-main CI/Security/optional CodeQL complete independently;
2. `Release Proof Dispatch` verifies current-main identity, release intent and every configured exact-SHA gate, dispatches `Trusted Release Proof`, then exits;
3. `Trusted Release Proof` runs proof on the trusted runner, produces the proof-owned promotable payload, completes, and releases the runner;
4. a separate `promote proven release` job in the same caller has `needs: proof`, starts only after proof success, invokes the central promotion reusable, dispatches Release idempotently, and exits;
5. Release imports the proof-produced payload, seals it, optionally attests it, and publishes behind the protected `release` environment when configured;
6. after Release succeeds, a short verification-dispatch job validates the immutable handoff and dispatches `Release Verification` without waiting for the child;
7. Release Verification independently validates the immutable transaction and may dispatch canonical Branch Cleanup, but it cannot delete refs itself;
8. Branch Cleanup is the only destructive branch-mutation authority.

This preserves the **proof-completion boundary**: promotion cannot begin until proof has completed successfully. It also preserves the **verification-dispatch boundary** that avoids deep chained `workflow_run` suppression.

The optional hosted observer remains available only when `PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true`. In that mode, `Release Proof Dispatch` may also invoke `reusable-release-proof-promotion-dispatch.yml` on `ubuntu-latest`; the observer waits within a bounded timeout for the exact proof and explicitly dispatches Release Promotion. It must never run on the same single trusted runner that proof needs.

## Automatic release proof authorization

`Release Proof Dispatch` is a permanent `workflow_run` caller on main-gate completion. It has `actions: write` so it can dispatch proof and `contents: read`; it cannot tag, publish, edit repository content, or delete refs.

The reusable dispatcher requires the trigger SHA to remain current `main`, derives one consistent SemVer from `.prodkit/release.json`, and treats an existing canonical tag on current main as no new release intent. A conflicting tag on another source fails closed.

Required exact-SHA permanent gates are supplied by the consumer. The generated baseline is CI + Security; repositories may strengthen that set, for example with CodeQL. Missing or active gates defer safely. A completed non-success gate fails closed. Existing active or successful exact-source proof runs suppress duplicates.

Before dispatch, the authorizer verifies that `Trusted Release Proof` remains `workflow_dispatch` only and certifies `source_sha: ${{ github.sha }}`.

## Trusted Release Proof

Trusted Release Proof remains dispatch-only. It certifies the exact current-main source, verifies permanent gate evidence, runs only release-specific repository acceptance, and builds the repository-owned promotable payload once.

The proof payload is content-addressed by its manifest and digests. Release reuses that exact payload rather than rebuilding an independent version of the same artifacts.

In the default v0.1.6 topology, the proof caller contains a second job with `needs: proof`. That job has promotion authority (`actions: write`) but no repository-content mutation authority, and delegates all promotion rules to `reusable-release-promote.yml`.

## Promotion

`reusable-release-promote.yml` rechecks current-main identity, resolves one canonical version, rejects conflicting tags, avoids duplicate active Release dispatches, and dispatches Release without polling publication.

`Release Promotion` remains available as a dual-entry recovery/compatibility caller. Its `workflow_run` path is active only when `PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true`; `workflow_dispatch` remains an explicit recovery handoff. The central publisher independently rechecks exact proof evidence, so promotion delivery cannot weaken publication authorization.

## Publication and approval

Release remains dispatch-only. The reusable publisher validates exact current-main identity, permanent exact-SHA gates, a completed successful exact-source Trusted Release Proof, version sources, release notes and manifest consistency.

Publication is checkpointed into prepare, build/seal, optional attestation, and publish stages. The proof-produced payload is downloaded from the exact successful proof run, verified, augmented with source/SBOM evidence, sealed by `release-metadata.json` and `SHA256SUMS`, and then published behind the configured `release` environment.

GitHub Artifact Attestations are optional and capability-dependent. When enabled they are fail-closed, but source identity, proof payload digests, SBOM generation, checksums and publication verification do not depend on attestations.

Late failures should use GitHub **Re-run failed jobs** so successful earlier publication stages are reused instead of rebuilding a different payload.

## Independent verification

Release dispatches `Release Verification` only after publication succeeds. The dispatch boundary validates the parent Release run and immutable tag/source handoff, then exits.

Release Verification runs from the immutable tag and verifies canonical source identity, Release metadata/body, publication state, remote asset set, checksums and asset digests. It has `actions: write` only because successful verification may dispatch canonical cleanup. It remains `contents: read` and cannot delete branches or alter repository content.

## Verified cleanup

Release Verification may identify the same-repository merged release/hotfix PR associated with the immutable release source and dispatch Branch Cleanup only after the publication transaction verifies.

`Post-Gate Branch Cleanup` is a separate dormant maintenance authorizer controlled by `PRODKIT_GATED_CLEANUP_BRANCHES_JSON`. It verifies exact current-main identity and configured exact-SHA gates, then dispatches Branch Cleanup without deleting refs itself.

Branch Cleanup is `workflow_dispatch` only. It rejects the default branch, protected branches, open-PR heads, malformed/duplicate targets and target movement. It binds deletion to the reviewed default SHA, revalidates immediately before mutation, serializes deletion and verifies each ref is absent afterward.

## Backward compatibility

Consumers stay pinned to immutable workflow SHAs. v0.1.5 consumers keep the v0.1.5 hosted-observer topology until they deliberately migrate. v0.1.6 consumers should install the complete generated caller family from one immutable v0.1.6 source.

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain compatibility entry points for historical consumers; new integrations should use direct runner selection and the current proof/promotion/publication/verification contracts.
