# Runner Requirements

ProdKit callers are **GitHub-hosted first**. Generated CI, Security, and Release callers target `ubuntu-latest` for normal execution and expose a manual `runner` choice that can switch the same reusable workflow to `["self-hosted","Linux","X64"]` when GitHub-hosted capacity, billing limits, or policy make hosted runners unavailable.

The reusable workflows still accept `runner_json` as the low-level runner contract. Existing consumers that already pass an explicit value remain unchanged. New generated callers always pass an explicit runner target rather than relying on the reusable workflow default.

## Failover semantics

GitHub Actions does not provide an `OR` or ordered-fallback form of `runs-on`. A `runs-on` array means that a runner must match **all** labels in the array; it does not mean “try GitHub-hosted, then self-hosted.” Therefore ProdKit does not claim transparent native fallback.

For a hosted-runner quota/capacity incident, rerun the exact workflow/ref with `runner: self-hosted`. The workflow uses the same pinned reusable contract and emits the same stable required job names. Automatic detection and redispatch requires a separate trusted watchdog/controller and is intentionally not emulated with duplicate release jobs or race-prone parallel execution.

A self-hosted runner can help when the GitHub-hosted execution pool or account allowance is unavailable, but it cannot bypass a complete GitHub Actions control-plane outage because GitHub still queues and dispatches self-hosted jobs.

## Security boundary

Never route untrusted public fork code to a persistent self-hosted runner. GitHub recommends self-hosted runners primarily for private repositories because fork pull requests can execute attacker-controlled code on the runner. `prodkit-workflows` itself is public, so its automatic pull-request CI and Security paths use GitHub-hosted runners; self-hosted execution is an explicit manual failover path only.

For private repositories, self-hosted fallback should still reject fork-originated pull requests unless the runner is ephemeral and intentionally provisioned for untrusted workloads.

## Self-hosted requirements

Self-hosted runners used for CI/Security/Release should provide Git, Bash, Python 3, Docker Engine/CLI, and outbound HTTPS to GitHub plus required package registries. Release runners should be isolated from untrusted workloads. Keep the self-hosted GitHub Actions Runner at **v2.327.1 or newer**; current `actions/attest` Node 24 releases require at least that runner generation.

Avoid permanent host ports for test databases. The reusable PostgreSQL job binds a random localhost port and cleans its run-scoped container.
