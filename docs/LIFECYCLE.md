# ProdKit workflow lifecycle

`prodkit-workflows` centralizes reusable workload implementation. Consumer repositories retain thin lifecycle callers, choose their runner directly, and own product-specific adapters/release metadata.

## Lifecycle

| Stage | Trigger | Required purpose | Normal evidence |
| --- | --- | --- | --- |
| Pull request | `pull_request` | Correctness/security feedback before merge | `CI`, `Security`, optional `CodeQL` |
| Main branch | `push` to `main` | Certify the actual merge SHA | successful exact-SHA `CI` and `Security` |
| Release candidate | explicit `workflow_dispatch` | Release-grade exact-source acceptance | `Trusted Release Proof` |
| Publication | explicit `workflow_dispatch` | Verify evidence, build, attest, tag, publish | immutable tag + Release + checksums/SBOM/provenance |
| Metadata repair | canonical metadata push or explicit dispatch | Repair mutable Release presentation only | verified name/body repair with immutable state unchanged |

## Runner ownership

A caller passes `runner_json` directly to the reusable workload. New generated callers do not invoke a runner-policy workflow first.

For trusted workloads the default target is `["self-hosted","Linux","X64"]`; `PRODKIT_RUNNER_JSON` may replace that JSON in generated generic callers. CI/Security fork PRs are forced to GitHub-hosted execution.

This intentionally avoids hosted probes, resolver jobs, destructive workspace preflight, and automatic runner switching. A workload gets one execution target and either succeeds or fails.

## Pull request and main

Normal CI and Security use compact reusable workflows. Each renders one stable workload job:

- `ci / CI Required`
- `security / Security Required`

Compatibility and scanning dimensions execute as steps, and the final aggregate verifier fails closed if any enabled control failed.

## Release candidate

`Trusted Release Proof` is dispatch-only and certifies `${{ github.sha }}` from the branch/ref on which it is dispatched. Operators do not paste a source SHA into the workflow.

The reusable proof checks that this SHA is still current `main`, executes the repository-owned `.prodkit/workflows/release-proof.sh`, proves the tracked source remained unchanged, and uploads proof evidence.

It does not run on every pull-request commit, ordinary main push, or tag event.

## Publication

`Release` is dispatch-only. Its only semantic operator input is the version (plus prerelease state when applicable). The release target is `${{ github.sha }}` from the dispatch on `main`.

Before publication the caller requires a successful dispatch of `Trusted Release Proof` for that exact SHA. The guarded reusable publisher independently requires successful `push` runs of `CI` and `Security` for the same exact SHA.

The reusable publisher then validates release metadata, executes the repository release-build adapter, adds central source/SBOM/checksum/provenance evidence, creates or verifies the immutable tag, performs draft-first publication, reads assets back, and verifies the published checksum set.

Tag creation never reruns the proof and a product/release failure never switches runners.

## Metadata repair

Release metadata repair is separate from publication. It may reconcile canonical GitHub Release name/body from current repository metadata only after proving the historical tag and payload identity remain unchanged.

It cannot move/create tags, rebuild or replace assets, change checksums, or change publication flags.

## Backward compatibility

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available for older immutable consumers. They are not part of the generated default lifecycle after the direct-runner architecture became normative.

ProdKit Quality remains a release-presentation reference, not a runner-controller dependency.
