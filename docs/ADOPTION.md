# Adoption Guide

## 1. Publish the control plane

Create `ProdKit-dev/prodkit-workflows`, push this repository, protect `main`, and run CI/Security once. Create a protected `release` environment for the release workflow.

## 2. Pin the workflow implementation

Choose the exact commit SHA of the reviewed `prodkit-workflows` revision. Do not use `@main`, `@v0`, or another movable reference.

## 3. Generate a consumer integration

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <sha> \
  --destination ../consumer
```

Edit the generated adapters and disable unused capabilities in caller workflows. If a repository does not have both `package.json` and `pyproject.toml`, remove the irrelevant version source from `.prodkit/release.json`.

## 4. Select runner mode

Generated CI and Security callers support GitHub-hosted-only, self-hosted-only, or strict dual-runner execution. Configure the non-secret GitHub Actions variable `PRODKIT_RUNNER_MODE` at organization or repository level:

- `github-hosted` → run only on `ubuntu-latest`;
- `self-hosted` → run only on `["self-hosted","Linux","X64"]`;
- `both` → run the complete contract independently on both runner classes and require both;
- unset/unknown → GitHub-hosted fail-safe default.

Repository-level configuration overrides organization-level configuration. Manual CI/Security `workflow_dispatch` exposes `runner: policy | github-hosted | self-hosted | both`; `policy` follows `PRODKIT_RUNNER_MODE` and explicit choices override it for that dispatch.

Fork-originated pull requests are always routed to GitHub-hosted runners, even if the configured policy requests self-hosted or both. GitHub Actions has no native ordered runner fallback.

`both` is for parity/redundancy, not failover. During a GitHub-hosted quota/capacity incident, switch or redispatch the exact source SHA with `runner: self-hosted`. The exact-SHA dispatch result can satisfy Release evidence just like the normal exact-SHA push result.

Release remains single-runner with `runner: policy | github-hosted | self-hosted` so two publication transactions cannot race. Organization Audit is also single-runner.

## 5. Stabilize required status names

The thin callers expose stable final runner-policy gates:

- `ci / CI Required`
- `security / Security Required`

Those names remain the same for GitHub-hosted, self-hosted, and `both`. Run both workflows once before configuring them as required checks.

## 6. Apply organization rulesets safely

Import `rulesets/org-main.json` and `rulesets/org-release-tags.json` at the organization level. The shipped recipes are intentionally **disabled by default** even though their repository condition is `~ALL`.

Before activation:

1. change repository targeting from `~ALL` to only the repositories that have completed migration;
2. verify `ci / CI Required` and `security / Security Required` already exist on those repositories;
3. review bypass actors, approval count, and status-check sources;
4. activate the ruleset only after that review;
5. expand the repository target set incrementally as additional repositories migrate.

Do not activate the `~ALL` condition while unmigrated repositories still depend on local workflow names.

## 7. Migrate releases

Replace old release implementations only after the new CI/Security evidence path is permanent on `main`. Preserve historical tags/releases. Do not rewrite old release commits. New releases use exactly one path: `workflow_dispatch(version, target_sha)`.

The normal evidence path is a completed successful exact-SHA `push` run for every required workflow. During trusted runner failover, a completed successful exact-SHA `workflow_dispatch` run is also accepted. Pull-request-only success never satisfies Release.

## 8. Audit drift

Configure a fine-grained PAT or GitHub App token with read access to the organization repositories as `ORG_AUDIT_TOKEN` in the control-plane repository, then run `Organization Audit`. The auditor fails on floating pins, missing wrappers, local release implementation patterns, or obsolete central SHAs.
