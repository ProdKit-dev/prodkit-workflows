# Adoption Guide

## 1. Validate the control plane

Protect `ProdKit-dev/prodkit-workflows/main` and require its permanent CI/Security checks. Keep publication behind a protected `release` environment when human approval is required.

## 2. Pin one reviewed revision

Consumers must call reusable workflows at an exact 40-character commit SHA. Never use `@main`, `@v0`, or another movable ref for production lifecycle authority.

## 3. Generate one coherent consumer family

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <sha> \
  --destination ../consumer
```

The generated family includes CI, Security, Release Proof Dispatch, Trusted Release Proof, Release Promotion, Release, Release Verification, Branch Cleanup, Post-Gate Branch Cleanup, and Release Metadata. Partial lifecycle migration is unsupported.

Repository-owned adapters remain under `.prodkit/workflows/`. Keep `.prodkit/release.json`, version sources, release notes and changelog headings aligned with the real repository.

## 4. Configure runners

Trusted generated jobs default to:

```json
["self-hosted","Linux","X64"]
```

Set `PRODKIT_RUNNER_JSON` to a complete JSON value accepted by `runs-on` when another trusted target is required.

v0.1.6 uses that same trusted target for the normal short release control plane: proof dispatch, serialized promotion, verification dispatch, Branch Cleanup, and Post-Gate Branch Cleanup. This removes the hard dependency on GitHub-hosted capacity that v0.1.5 exposed in private repositories.

If GitHub-hosted control-plane capacity is deliberately available and desired, set:

```text
PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true
```

That opt-in enables the bounded hosted proof observer. Leave it unset for the default serialized proof-to-promotion topology.

There is no automatic runner failover. If the selected runner is unavailable, repair it or intentionally change `PRODKIT_RUNNER_JSON` for subsequent runs.

## 5. Stabilize required checks

Run CI and Security at least once and verify GitHub exposes stable aggregate checks such as:

- `ci / CI Required`
- `security / Security Required`

Repositories may strengthen release authorization with additional permanent gates such as CodeQL. The consumer caller's `required_workflows_json` must match the intended exact-SHA release gate set.

## 6. Apply repository rules incrementally

Before enabling organization/repository rulesets, verify the required check identities exist, review bypass actors and approvals, and target only repositories that have completed migration.

## 7. Normal release path

Prepare a release PR so all version sources expose the intended SemVer, `docs/V<version>.md` exists, and the changelog contains the matching heading. The normal lifecycle is:

1. merge the release PR to `main`;
2. wait for exact-main CI/Security and any additional configured permanent release gates;
3. `Release Proof Dispatch` verifies current-main identity, release intent and exact-SHA gates, dispatches `Trusted Release Proof`, then exits;
4. Trusted Release Proof validates exact-source evidence, runs release-specific acceptance, builds the promotable payload once, and completes;
5. by default, the dependent `promote proven release` job starts only after proof success and invokes central promotion; no parent holds the runner while waiting for proof;
6. promotion dispatches Release idempotently;
7. approve the protected `release` environment if configured;
8. Release imports and seals the exact proof-produced payload, publishes the immutable tag/Release, and dispatches verification;
9. Release Verification independently verifies source, metadata, assets and checksums;
10. when the verified source came from one same-repository merged `release/` or `hotfix/` PR, verification may dispatch canonical Branch Cleanup for that branch.

Do not manually copy SHAs between lifecycle workflows.

## 8. Hosted observer compatibility mode

When `PRODKIT_GITHUB_HOSTED_CONTROL_PLANE=true`, Release Proof Dispatch also invokes the bounded GitHub-hosted proof observer. The observer waits for the exact proof and explicitly dispatches Release Promotion because GitHub may suppress downstream `workflow_run` events for workflows started by `GITHUB_TOKEN`.

This mode must remain GitHub-hosted; never put that polling observer on the same single trusted runner needed by proof. The default v0.1.6 serialized promotion path exists specifically to avoid that deadlock.

## 9. Manual recovery boundaries

Manual `workflow_dispatch` remains recovery-only:

- manually dispatch Trusted Release Proof only after confirming no active or successful automatic exact-source proof exists;
- manually dispatch Release Promotion only after confirming automatic promotion did not already dispatch Release;
- manually dispatch Release only after confirming there is no active or successful exact-source Release transaction;
- manually dispatch Release Verification only for deliberate re-verification of an already published immutable tag.

Use GitHub **Re-run failed jobs** for late publication failures so already successful proof/build/seal stages are reused.

## 10. Clean branches safely

Use `Branch Cleanup`; never add repository-local deletion scripts. Branch Cleanup is `workflow_dispatch` only, accepts an explicit JSON branch list, defaults to dry-run, binds mutation to an exact default-branch SHA, rejects protected/default/open-PR targets, revalidates immediately before deletion, and verifies absence afterward.

`Post-Gate Branch Cleanup` is dormant until `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` contains a reviewed exact list. It authorizes cleanup after configured exact-SHA gates but has no `contents: write`; the canonical Branch Cleanup workflow remains the only destructive ref authority.

## 11. Audit drift

Run Organization Audit with a token that can read target repositories. The auditor rejects missing lifecycle callers, floating central refs, obsolete central SHAs, retired runner-controller usage, unsafe triggers, local publication implementations, direct cleanup mutation outside Branch Cleanup, broken exact-source handoffs, and lifecycle callers that violate the v0.1.6 serialized/hosted-mode contract.

Audit accepts repositories that strengthen the exact-SHA release gate set beyond the generated CI + Security baseline, provided the central proof/release contracts remain intact.

## 12. Migration from v0.1.5

Keep historical v0.1.5 pins immutable. For a deliberate migration, regenerate or update the complete caller family to one reviewed v0.1.6 SHA, validate CI/Security/CodeQL as applicable, then exercise an actual release end to end. Do not mix v0.1.5 and v0.1.6 lifecycle callers in one repository.
