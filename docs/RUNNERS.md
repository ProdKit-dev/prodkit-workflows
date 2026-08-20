# Runner Requirements

ProdKit supports both GitHub-hosted and self-hosted runners through one runner-selection contract. Reusable workflows remain runner-agnostic through `runner_json`; thin callers decide which target to pass before GitHub routes the job.

## Policy variable

Generated callers read the non-secret GitHub Actions configuration variable `PRODKIT_RUNNER_MODE` from the caller repository context.

| `PRODKIT_RUNNER_MODE` | Automatic trusted events |
| --- | --- |
| `github-hosted` | `ubuntu-latest` |
| `self-hosted` | `["self-hosted","Linux","X64"]` |
| unset or any other value | `ubuntu-latest` |

The variable may be defined at organization level to control many repositories at once. A repository-level variable with the same name overrides the organization-level value, allowing an exceptional repository to choose a different runner policy.

For CI and Security pull requests, fork-originated code is always forced to GitHub-hosted execution even when the configured policy is `self-hosted`. This prevents organization/repository policy from accidentally routing untrusted fork code to a persistent runner.

## Manual override

Generated `workflow_dispatch` callers expose:

- `runner: policy` — use `PRODKIT_RUNNER_MODE`;
- `runner: github-hosted` — force `ubuntu-latest` for this dispatch;
- `runner: self-hosted` — force `["self-hosted","Linux","X64"]` for this dispatch.

Release is dispatch-only, so its default `runner: policy` applies the same condition-based selection without changing the release state machine. Organization Audit uses the same three-state runner input.

## Hosted quota/capacity incidents

GitHub Actions does not provide an `OR` or ordered-fallback form of `runs-on`. A `runs-on` array means that a runner must match **all** labels in the array; it does not mean “try GitHub-hosted, then self-hosted.” Therefore ProdKit does not claim transparent native fallback.

When GitHub-hosted minutes, billing, capacity, or policy make hosted execution unavailable, there are two supported recovery paths:

1. set `PRODKIT_RUNNER_MODE=self-hosted` at organization or repository level so subsequent automatic runs select self-hosted; or
2. redispatch the exact workflow/ref with `runner: self-hosted`.

Automatic detection of a hosted-runner failure and subsequent variable change/redispatch requires a separate trusted watchdog/controller. It should operate on the exact repository, workflow, and source SHA and must not create competing release executions.

A self-hosted runner can help when the GitHub-hosted execution pool or account allowance is unavailable, but it cannot bypass a complete GitHub Actions control-plane outage because GitHub still queues and dispatches self-hosted jobs.

## Concurrency

CI and Security concurrency belongs to each thin caller, not the reusable workflow. That lets distinct calls to the reusable contract coexist while a new run of the same caller/ref still cancels obsolete work. Release keeps its version-scoped non-cancelling lock because publication must never race.

## Security boundary

Never route untrusted public fork code to a persistent self-hosted runner. `prodkit-workflows` itself is public, so its caller expression forces fork-originated pull requests onto GitHub-hosted runners even if `PRODKIT_RUNNER_MODE=self-hosted`.

For private repositories, keep the same fail-closed rule unless the runner is intentionally ephemeral and isolated for untrusted code.

## Self-hosted requirements

Self-hosted runners used for CI/Security/Release should provide Git, Bash, Python 3, Docker Engine/CLI, and outbound HTTPS to GitHub plus required package registries. Release runners should be isolated from untrusted workloads. Keep the self-hosted GitHub Actions Runner at **v2.327.1 or newer**; current `actions/attest` Node 24 releases require at least that runner generation.

Avoid permanent host ports for test databases. The reusable PostgreSQL job binds a random localhost port and cleans its run-scoped container.
