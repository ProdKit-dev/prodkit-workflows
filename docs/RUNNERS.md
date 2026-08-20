# Runner Requirements

ProdKit supports GitHub-hosted, self-hosted, or strict dual-runner execution through one runner-selection contract. Reusable workflows remain runner-agnostic through `runner_json`; thin callers decide which complete contract lanes to invoke before GitHub routes the jobs.

## Policy variable

Generated CI and Security callers read the non-secret GitHub Actions configuration variable `PRODKIT_RUNNER_MODE` from the caller repository context.

| `PRODKIT_RUNNER_MODE` | Automatic trusted events |
| --- | --- |
| `github-hosted` | run the complete contract only on `ubuntu-latest` |
| `self-hosted` | run the complete contract only on `["self-hosted","Linux","X64"]` |
| `both` | run the complete contract independently on both runner classes; both must pass |
| unset or any other value | GitHub-hosted fail-safe default |

The variable may be defined at organization level to control many repositories at once. A repository-level variable with the same name overrides the organization-level value, allowing an exceptional repository to choose a different runner policy.

For CI and Security pull requests, fork-originated code is always forced to GitHub-hosted execution even when the configured policy is `self-hosted` or `both`. This prevents organization/repository policy from accidentally routing untrusted fork code to a persistent runner.

## Manual override

Generated CI and Security `workflow_dispatch` callers expose:

- `runner: policy` — use `PRODKIT_RUNNER_MODE`;
- `runner: github-hosted` — force the GitHub-hosted lane for this dispatch;
- `runner: self-hosted` — force the self-hosted lane for this dispatch;
- `runner: both` — run and require both complete lanes for this dispatch.

Release remains single-runner and exposes only `policy | github-hosted | self-hosted`; two release jobs must never race an immutable tag/publication transaction. If `PRODKIT_RUNNER_MODE=both`, Release's `policy` mode resolves safely to GitHub-hosted unless an operator explicitly selects self-hosted. Organization Audit is also intentionally single-runner.

## Stable required checks

The thin CI and Security callers own a final policy gate after the selected reusable lanes:

- `ci / CI Required`
- `security / Security Required`

Those organization-facing names do not change when a repository switches between GitHub-hosted, self-hosted, and `both`.

In single-runner mode the selected lane must succeed and the unselected lane must be skipped. In `both` mode both complete reusable contracts must succeed. This means `both` is strict parity/redundancy, not a fallback mode.

## Hosted quota/capacity incidents

GitHub Actions does not provide an `OR` or ordered-fallback form of `runs-on`. A `runs-on` array means that a runner must match **all** labels in the array; it does not mean “try GitHub-hosted, then self-hosted.” Therefore ProdKit does not claim transparent native fallback.

When GitHub-hosted minutes, billing, capacity, or policy make hosted execution unavailable, use `self-hosted`, not `both`:

1. set `PRODKIT_RUNNER_MODE=self-hosted` at organization or repository level so subsequent automatic runs select self-hosted; or
2. redispatch the exact workflow/ref with `runner: self-hosted`.

The redispatch executes the same immutable reusable workflow and adapters. Reusable Release accepts successful exact-SHA required-workflow evidence from either a normal `push` run or a trusted `workflow_dispatch` run, so a self-hosted recovery run remains releasable. Pull-request-only evidence is never accepted for Release.

Automatic detection of a hosted-runner failure and subsequent variable change/redispatch requires a separate trusted watchdog/controller. It should operate on the exact repository, workflow, and source SHA, be idempotent, and never create competing release executions.

A self-hosted runner can help when the GitHub-hosted execution pool or account allowance is unavailable, but it cannot bypass a complete GitHub Actions control-plane outage because GitHub still queues and dispatches self-hosted jobs.

## Concurrency

CI and Security concurrency belongs to each thin caller, not the reusable workflow. That lets the hosted and self-hosted reusable lanes coexist in `both` mode while a new run of the same caller/ref still cancels obsolete work. Release keeps its version-scoped non-cancelling lock because publication must never race.

## Security boundary

Never route untrusted public fork code to a persistent self-hosted runner. `prodkit-workflows` itself is public, so its caller expressions force fork-originated pull requests onto GitHub-hosted runners even if `PRODKIT_RUNNER_MODE=self-hosted` or `both`.

For private repositories, keep the same fail-closed rule unless the runner is intentionally ephemeral and isolated for untrusted code.

## Self-hosted requirements

Self-hosted runners used for CI/Security/Release should provide Git, Bash, Python 3, Docker Engine/CLI, and outbound HTTPS to GitHub plus required package registries. Release runners should be isolated from untrusted workloads. Keep the self-hosted GitHub Actions Runner at **v2.327.1 or newer**; current `actions/attest` Node 24 releases require at least that runner generation.

Avoid permanent host ports for test databases. The reusable PostgreSQL job binds a random localhost port and cleans its run-scoped container.
