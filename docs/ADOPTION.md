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

Generated callers support GitHub-hosted execution, trusted self-hosted execution, and hosted-first automatic failover. Configure the non-secret GitHub Actions variable `PRODKIT_RUNNER_MODE` at organization or repository level:

- `auto` → run a non-poisoning `ubuntu-latest` availability probe; if it does not emit `available=true`, route the real trusted workload to `["self-hosted","Linux","X64"]`;
- `github-hosted` → strict `ubuntu-latest`;
- `self-hosted` → strict `["self-hosted","Linux","X64"]`;
- unset → same as `auto`;
- unknown non-empty value → strict GitHub-hosted fail-safe.

Repository-level configuration overrides organization-level configuration. Manual `workflow_dispatch` exposes `runner: policy | auto | github-hosted | self-hosted`; `policy` follows `PRODKIT_RUNNER_MODE` and explicit choices override it for that dispatch.

Fork-originated pull requests are always routed to GitHub-hosted runners and never participate in self-hosted fallback. The hosted probe does not checkout or execute repository code, uses `continue-on-error: true`, and writes `available=true` only if its step actually runs. Its infrastructure failure is therefore routing evidence rather than a failed product gate. Failover is decided before the real reusable workflow begins, so a test/security/release failure never triggers retry on another runner. See `docs/RUNNERS.md` for the exact limitations, including indefinitely queued hosted jobs and the absence of automatic self-hosted-to-hosted fallback.

## 4. Stabilize required status names

The supplied caller jobs remain named `ci` and `security` even when automatic failover is enabled. GitHub therefore exposes the final reusable checks as `ci / CI Required` and `security / Security Required`. Run both workflows once before configuring them as required checks.

## 5. Apply organization rulesets safely

Import `rulesets/org-main.json` and `rulesets/org-release-tags.json` at the organization level. The shipped recipes are intentionally **disabled by default** even though their repository condition is `~ALL`.

Before activation:

1. change repository targeting from `~ALL` to only the repositories that have completed migration;
2. verify `ci / CI Required` and `security / Security Required` already exist on those repositories;
3. review bypass actors, approval count, and status-check sources;
4. activate the ruleset only after that review;
5. expand the repository target set incrementally as additional repositories migrate.

Do not activate the `~ALL` condition while unmigrated repositories still depend on local workflow names.

## 6. Migrate releases

Replace old release implementations only after the new CI/Security push runs are permanent on `main`. Preserve historical tags/releases. Do not rewrite old release commits. New releases use exactly one publication path: `workflow_dispatch(version, target_sha)`. Under `auto`, runner failover is settled before any guarded release step starts.

## 7. Audit drift

Configure a fine-grained PAT or GitHub App token with read access to the organization repositories as `ORG_AUDIT_TOKEN` in the control-plane repository, then run `Organization Audit`. The auditor fails on floating pins, missing wrappers, local release implementation patterns, or obsolete central SHAs.
