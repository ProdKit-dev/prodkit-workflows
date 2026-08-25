# Runner Requirements

ProdKit reusable workloads are runner-agnostic through their `runner_json` input. The caller chooses the runner directly; runner selection is not a separate prerequisite workflow.

## Default trusted target

Generated trusted workloads default to:

```json
["self-hosted","Linux","X64"]
```

To use another trusted target, set the non-secret Actions variable `PRODKIT_RUNNER_JSON` to a complete JSON value accepted by `runs-on`, for example:

```json
["self-hosted","Linux","X64","prodkit-ci"]
```

A GitHub-hosted target is represented as:

```json
"ubuntu-latest"
```

There is intentionally no automatic runner failover. GitHub Actions does not provide a reliable ordered fallback between runner trust classes; switching runner class after a workload fails or queues would blur evidence and authority boundaries.

## v0.1.6 release control plane

v0.1.6 removes the assumption that short release control-plane jobs always have GitHub-hosted capacity. The normal generated lifecycle uses `PRODKIT_RUNNER_JSON` for Release Proof Dispatch, the serialized promotion job, Release Promotion recovery, Release verification dispatch, Branch Cleanup, and Post-Gate Branch Cleanup.

This default is safe on a single trusted runner because promotion is serialized after proof completion. No job holds the runner while waiting for another workflow that needs the same runner.

Installations that deliberately have reliable GitHub-hosted control-plane capacity may set:

```text
PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true
```

That enables the bounded hosted proof observer from the v0.1.4/v0.1.5 topology. The observer itself remains hard-targeted to `ubuntu-latest`; it polls for proof completion and therefore must never share the only trusted runner needed by proof.

## Fork safety

Generated CI and Security callers force fork-originated pull requests to `ubuntu-latest`, regardless of `PRODKIT_RUNNER_JSON`. Persistent trusted runners must not execute untrusted fork code by default.

CodeQL may be skipped for fork PRs unless a repository deliberately provides a safe hosted integration.

Release, Trusted Release Proof, promotion, metadata, verification and cleanup are trusted repository/operator paths rather than fork-PR entry points.

## Failure boundary

Runner availability is infrastructure state outside the reusable workload. A workload targets one runner class once. Product, test, security, migration, packaging or publication failures never trigger an automatic trust-boundary switch.

If the configured self-hosted runner is unavailable, repair/restart it or intentionally change `PRODKIT_RUNNER_JSON` for subsequent runs. Do not add retry-until-green or automatic runner-switch logic to consumer workflows.

If GitHub-hosted jobs fail before executing any step, either restore hosted Actions availability or leave `PRODKIT_GITHUB_HOSTED_CONTROL_PLANE` unset and use the v0.1.6 serialized trusted-runner path.

## Concurrency

Consumer CI/Security workflows own their concurrency groups. On one self-hosted runner, CI, Security, CodeQL and release jobs may queue behind one another. That is expected and does not require a runner-resolution controller.

Release publication uses a version-scoped non-cancelling concurrency lock so publication transactions cannot race. Branch Cleanup also serializes destructive mutations.

## Self-hosted requirements

Trusted self-hosted runners should provide:

- Git and Bash;
- Python 3;
- Docker Engine/CLI where PostgreSQL, container, Trivy, SBOM, browser or release adapters require it;
- outbound HTTPS to GitHub and required registries;
- enough disk space for package caches, container images, browser runtimes and release artifacts;
- a current GitHub Actions Runner version compatible with pinned actions.

Keep release runners isolated from untrusted workloads. Avoid container commands that create root-owned files in bind-mounted workspaces. Repository adapters are responsible for cleaning their own run-scoped containers, volumes and generated artifacts.

## Backward compatibility

`reusable-runner-policy.yml` remains available only for consumers pinned to historical control-plane SHAs. New bootstrap output, normative documentation, organization audit rules and current control-plane callers use direct runner selection.

v0.1.5 consumers remain immutable. v0.1.6 changes the generated/default runner topology without changing historical workflow behavior.
