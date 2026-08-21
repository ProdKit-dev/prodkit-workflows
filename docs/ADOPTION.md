# Adoption Guide

## 1. Validate the control plane

Protect `ProdKit-dev/prodkit-workflows/main` and require its CI/Security checks. Maintain a protected `release` environment for publication workflows that use it.

## 2. Pin one reviewed revision

Consumers must call reusable workflows at an exact 40-character commit SHA. Do not use `@main`, `@v0`, or another movable ref.

## 3. Generate a consumer integration

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <sha> \
  --destination ../consumer
```

Edit repository-owned adapters and disable unused capabilities. Keep release metadata in `.prodkit/release.json` aligned with the repository’s actual version sources and release notes.

## 4. Configure the runner directly

New generated callers do not invoke a runner-selection controller.

Trusted work defaults to:

```json
["self-hosted","Linux","X64"]
```

If a repository needs another trusted target, set the non-secret Actions variable `PRODKIT_RUNNER_JSON` to the complete JSON value accepted by `runs-on`.

Fork-originated CI/Security pull requests remain forced to `ubuntu-latest`; do not remove that guard for persistent runners.

There is no automatic runner failover in the normative architecture. If a runner is unavailable, repair it or deliberately change the direct runner target for subsequent runs. See `docs/RUNNERS.md`.

## 5. Stabilize required checks

Run CI and Security once and confirm GitHub exposes:

- `ci / CI Required`
- `security / Security Required`

Configure organization/repository rulesets to require those aggregate checks.

## 6. Apply rulesets incrementally

The shipped organization ruleset recipes are disabled by default. Before activation:

1. target only repositories that have completed migration;
2. verify the required check names already exist;
3. review bypass actors, approvals, and status-check sources;
4. enable rulesets only after validation;
5. expand repository scope gradually.

## 7. Migrate release proof/publication

Preserve historical tags/releases. Do not rewrite old release commits.

For a new release:

1. merge the release candidate to `main`;
2. wait for exact-main CI and Security to pass;
3. dispatch `Trusted Release Proof` on `main` — the proof source is automatically `${{ github.sha }}`;
4. after proof succeeds, dispatch `Release` on the same `main` revision with the semantic version;
5. Release automatically uses `${{ github.sha }}` as the target and verifies exact-SHA CI, Security, and proof evidence before any tag/publication transaction.

Operators should not manually copy commit SHAs between these workflows.

## 8. Audit drift

Configure `ORG_AUDIT_TOKEN` with read access to the target repositories and run Organization Audit. The auditor rejects:

- missing lifecycle callers;
- floating central refs;
- obsolete central SHAs;
- retired runner-controller usage;
- the retired nested Release pipeline as the generated release contract;
- local publication implementations in consumer `release.yml`.

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available only for consumers already pinned to historical revisions; do not generate new integrations from them.
