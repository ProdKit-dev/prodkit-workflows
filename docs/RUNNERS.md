# Runner Requirements

ProdKit supports GitHub-hosted and trusted self-hosted runners through one runner-selection contract. Reusable workflows remain runner-agnostic through `runner_json`; thin callers decide which target to pass before GitHub routes the real CI, Security, Release, or Organization Audit workload.

## Policy variable

Generated callers read the non-secret GitHub Actions configuration variable `PRODKIT_RUNNER_MODE` from the caller repository context.

| `PRODKIT_RUNNER_MODE` | Automatic trusted events |
| --- | --- |
| `auto` | run a non-poisoning GitHub-hosted availability probe first; fall back to `["self-hosted","Linux","X64"]` when the probe does not emit `available=true` |
| `github-hosted` | strict `ubuntu-latest`; no automatic self-hosted fallback |
| `self-hosted` | strict `["self-hosted","Linux","X64"]` |
| unset | same as `auto` |
| any other value | fail safe to strict `ubuntu-latest` |

The variable may be defined at organization level to control many repositories at once. A repository-level variable with the same name overrides the organization-level value, allowing an exceptional repository to choose a different runner policy.

For CI and Security pull requests, fork-originated code is always forced to GitHub-hosted execution even when the configured policy is `auto` or `self-hosted`. This prevents organization/repository policy from routing untrusted fork code to a persistent runner.

## Automatic hosted-first failover

`auto` is implemented by the thin caller, not by an invalid multi-runner `runs-on` expression. Before invoking the reusable workflow, the caller schedules a minimal `Hosted runner availability` probe on `ubuntu-latest`. The probe does not checkout or execute repository code and is deliberately **non-poisoning**: its infrastructure failure is routing evidence, not a failed product/security/release gate.

- If the probe actually starts, its step writes `available=true` to a job output and the real reusable workflow runs on GitHub-hosted Ubuntu.
- If GitHub cannot provision the hosted probe (including billing/account/startup failures such as jobs that fail before step 1), the output is absent and the caller invokes the same reusable workflow on `["self-hosted","Linux","X64"]`.
- The probe uses `continue-on-error: true` so a hosted-infrastructure failure does not by itself poison the overall caller workflow result.
- If the probe is skipped because an explicit runner mode was selected, the explicit mode is used unchanged.
- If the workflow is cancelled, the real reusable workflow is not started.

Because failover is decided **before product tests or release steps begin**, a genuine test, audit, migration, security, packaging, or publication failure never triggers a runner switch. This prevents infrastructure fallback from becoming a retry-until-green mechanism.

The caller job names remain `ci`, `security`, `release`, and `audit`, so stable required checks such as `ci / CI Required` and `security / Security Required` do not change when failover is enabled.

## Manual override

Generated `workflow_dispatch` callers expose:

- `runner: policy` — use `PRODKIT_RUNNER_MODE`;
- `runner: auto` — force hosted-first automatic failover for this trusted dispatch;
- `runner: github-hosted` — force strict `ubuntu-latest` for this dispatch;
- `runner: self-hosted` — force strict `["self-hosted","Linux","X64"]` for this dispatch.

Release is dispatch-only, so its default `runner: policy` applies the same selection before any release side effect. Organization Audit uses the same four-state runner input.

## Failure boundary and limitations

GitHub Actions does not provide an `OR` or ordered-fallback form of `runs-on`. A `runs-on` array means that a runner must match **all** labels in the array; it does not mean “try GitHub-hosted, then self-hosted.” ProdKit therefore implements failover as a pre-workload probe plus conditional routing.

This covers hosted-runner failures where the probe fails to produce its positive availability output, including account/billing/startup failures like jobs that fail before step 1. It cannot bypass a complete GitHub Actions control-plane outage, because both hosted and self-hosted jobs still depend on GitHub for queueing and dispatch. A hosted job that remains indefinitely queued rather than reaching a state from which dependent jobs can proceed also cannot trigger in-workflow failover; operators may force `runner: self-hosted` or set `PRODKIT_RUNNER_MODE=self-hosted` for subsequent runs.

There is intentionally no automatic self-hosted-to-hosted failover. An unavailable self-hosted runner can remain queued without producing a failure event that the same workflow can safely react to. Use strict `github-hosted` or `auto` when self-hosted availability is uncertain.

## Concurrency

CI and Security concurrency belongs to each thin caller, not the reusable workflow. That lets distinct calls to the same reusable contract coexist while a new run of the same caller/ref still cancels obsolete work. Release keeps its version-scoped non-cancelling lock because publication must never race.

## Security boundary

Never route untrusted public fork code to a persistent self-hosted runner. `prodkit-workflows` itself is public, so its caller expression forces fork-originated pull requests onto GitHub-hosted runners even if `PRODKIT_RUNNER_MODE=auto` or `self-hosted`.

For private repositories, keep the same fail-closed rule unless the runner is intentionally ephemeral and isolated for untrusted code.

## Self-hosted requirements

Self-hosted runners used for CI/Security/Release should provide Git, Bash, Python 3, Docker Engine/CLI, and outbound HTTPS to GitHub plus required package registries. Release runners should be isolated from untrusted workloads. Keep the self-hosted GitHub Actions Runner at **v2.327.1 or newer**; current `actions/attest` Node 24 releases require at least that runner generation.

Avoid permanent host ports for test databases. The reusable PostgreSQL job binds a random localhost port and cleans its run-scoped container.
