# Runner Requirements

ProdKit reusable workloads are runner-agnostic through their `runner_json` input. The caller chooses the runner directly; runner selection is not a separate prerequisite workflow.

## Default target

Generated trusted workloads default to:

```json
["self-hosted","Linux","X64"]
```

To use a different trusted target, set the non-secret Actions variable `PRODKIT_RUNNER_JSON` to a complete JSON value accepted by `runs-on`, for example:

```json
["self-hosted","Linux","X64","prodkit-ci"]
```

A GitHub-hosted target can be represented as:

```json
"ubuntu-latest"
```

There is intentionally no `policy`, `auto`, hosted probe, resolver, or in-workflow failover in newly generated callers. GitHub Actions has no reliable ordered runner fallback, and a controller job adds queueing and failure state without guaranteeing recovery from an indefinitely queued runner.

## Fork safety

Generated CI and Security callers force fork-originated pull requests to `ubuntu-latest`, regardless of `PRODKIT_RUNNER_JSON`. Persistent trusted runners must not execute untrusted fork code by default.

CodeQL is skipped for fork PRs by the generated caller unless a repository deliberately provides a safe hosted integration.

Release, Trusted Release Proof, Release Metadata, and Organization Audit are trusted operator workflows rather than fork-PR entry points.

## Failure boundary

Runner availability is an infrastructure concern outside the reusable workload. A workflow targets one runner class once. Product, test, security, migration, packaging, or publication failures never trigger a runner switch or automatic retry on a second trust boundary.

If the configured self-hosted runner is unavailable, fix/restart that runner or intentionally change `PRODKIT_RUNNER_JSON` for subsequent runs. Do not build retry-until-green logic into release workflows.

## Concurrency

Consumer CI/Security workflows own their concurrency groups. On a single self-hosted runner, CI and Security may queue behind one another, but there is no additional runner-resolution job consuming a slot first.

Release uses a version-scoped non-cancelling concurrency lock so publication transactions cannot race.

## Self-hosted requirements

Trusted self-hosted runners should provide:

- Git;
- Bash;
- Python 3;
- Docker Engine/CLI where container, PostgreSQL, Trivy, SBOM, browser, or release adapters need it;
- outbound HTTPS to GitHub and required registries;
- enough disk space for package caches, container images, browser runtimes, and release artifacts.

Keep release runners isolated from untrusted workloads. Avoid Docker commands that create root-owned files in bind-mounted repository workspaces. Containerized Python should use `PYTHONDONTWRITEBYTECODE=1` when bytecode would otherwise be written into a host-mounted source tree.

Repository adapters are responsible for cleaning their own run-scoped containers/volumes/artifacts. Reusable workflows must not depend on a destructive pre-checkout workspace-cleanup controller.

Keep the GitHub Actions Runner current enough for the pinned actions used by the control plane, especially Node-24-based attestation actions.

## Backward compatibility

`reusable-runner-policy.yml` remains available only so repositories already pinned to historical control-plane SHAs are not broken retroactively. New bootstrap output, normative documentation, organization audit rules, and control-plane self-callers do not use it.
