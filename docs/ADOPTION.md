# Adoption Guide

## 1. Validate the control plane

Protect `ProdKit-dev/prodkit-workflows/main` and require its CI/Security checks. Maintain a protected `release` environment for publication workflows that use it. Configure required reviewers on that environment when human publication approval is required.

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

The generated integration includes `Release Proof Dispatch`, `Trusted Release Proof`, `Release Promotion`, `Release`, `Release Verification`, `Branch Cleanup`, and `Post-Gate Branch Cleanup`. Keep the workflow family pinned to one reviewed central revision; partial release-lifecycle migration is unsupported.

The destructive cleanup caller remains explicitly dispatched and pinned to the same central revision; consumers must not replace it with repository-local branch-deletion code. The post-gate caller is a dormant authorization layer and cannot delete refs directly.

## 4. Configure the runner directly

New generated callers do not invoke a runner-selection controller.

Trusted work defaults to:

```json
["self-hosted","Linux","X64"]
```

If a repository needs another trusted target, set the non-secret Actions variable `PRODKIT_RUNNER_JSON` to the complete JSON value accepted by `runs-on`.

Fork-originated CI/Security pull requests remain forced to `ubuntu-latest`; do not remove that guard for persistent runners.

There is no automatic runner failover in the normative architecture. If a runner is unavailable, repair it or deliberately change the direct runner target for subsequent runs. See `docs/RUNNERS.md`.

Branch Cleanup defaults to GitHub-hosted `ubuntu-latest`. Post-Gate Branch Cleanup also prefers GitHub-hosted execution but honors `PRODKIT_RUNNER_JSON` for installations where trusted private-repository control-plane jobs must use a self-hosted runner. Release Proof Dispatch is intentionally GitHub-hosted because it is a short non-mutating control-plane dispatcher and must not occupy the trusted product runner while starting proof.

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

1. prepare the release candidate so all manifest version sources expose the intended new SemVer, its release notes exist, and the changelog contains the matching heading;
2. merge the release candidate to `main`;
3. wait for exact-main CI and Security to pass;
4. `Release Proof Dispatch` automatically recognizes the unpublished canonical version, verifies both exact-SHA permanent gates, validates the dispatch-only proof caller, and dispatches `Trusted Release Proof` on `main`;
5. after proof succeeds, wait for the `Release Promotion` workflow triggered from that completed proof; it derives the semantic version from the exact source and dispatches `Release` automatically;
6. if the repository protects the `release` environment with required reviewers, approve publication there after reviewing the already-completed exact-source evidence;
7. wait for the automatically dispatched `Release` run, which uses `${{ github.sha }}` as the target and verifies exact-SHA CI, Security, and proof evidence before any tag/publication transaction;
8. wait for `Release Verification` after successful publication to independently verify the immutable release transaction.

Do not manually dispatch `Trusted Release Proof` during the normal v0.1.4+ lifecycle. Manual proof dispatch remains a recovery mechanism only after confirming the automatic dispatcher did not already create an active or successful exact-source proof run.

Do not manually dispatch `Release` after a successful proof when `Release Promotion` is active. A manual Release dispatch is an operator recovery action only after confirming automatic promotion did not already create an active or completed exact-source Release run; otherwise it creates redundant production execution and ambiguous approval/failure history.

Operators should not manually copy commit SHAs between these workflows.

The automatic proof dispatcher evaluates exact-main gate completions only. Ordinary main merges do not become releases when the canonical version is already represented by its immutable tag. A new unpublished canonical version is the release-intent signal; a conflicting existing tag fails closed.

## 8. Clean obsolete branches safely

### Manual reviewed cleanup

Use the generated `Branch Cleanup` workflow instead of repository-local cleanup scripts or transient operator workflows.

The workflow is `workflow_dispatch` only. Supply `branches_json` as a JSON array of exact branch names. Leave `dry_run` enabled for the first pass, inspect the evidence summary, then deliberately dispatch again with `dry_run=false` when the targets are correct.

The optional `expected_default_sha` input may normally remain empty. When empty, cleanup binds itself to `${{ github.sha }}` at dispatch time. A trusted upstream authorization workflow may provide an already-reviewed exact SHA; if `main` moved before cleanup begins, deletion fails closed.

The reusable cleanup contract fails closed when:

- the default branch moved away from the exact SHA reviewed at dispatch time;
- a requested branch is the repository default branch;
- a requested branch is protected;
- a requested branch is the head of an open pull request;
- the target list is malformed, duplicated, empty, or uses branch names outside the conservative ref contract.

The implementation preflights the complete target set before mutation, deletes only explicit names, rechecks the default SHA during mutation, verifies each deleted ref is absent, and writes cleanup evidence to the workflow log/summary. Already-absent branches are idempotent success.

Do not expose destructive cleanup through `push`, `schedule`, `workflow_run`, or unauthenticated/comment-driven triggers. The canonical Branch Cleanup caller grants `contents: write` only to its cleanup job.

### Optional automatic post-gate authorization

`Post-Gate Branch Cleanup` removes the need for a repository-local temporary cleanup closer. It remains dormant until the repository variable `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` is populated with a non-empty reviewed JSON array of exact branch names.

Recommended operation:

1. run manual Branch Cleanup with `dry_run=true` for the intended exact target list;
2. review the resulting evidence and ensure every target is expected;
3. set `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` to that exact JSON list before the main push whose permanent gates should authorize deletion;
4. leave `PRODKIT_GATED_CLEANUP_GATES_JSON` unset to require exact-SHA CI and Security, or set it to an explicit JSON array of `{name,path}` gate objects;
5. let the required push workflows complete;
6. inspect `Post-Gate Branch Cleanup` authorization evidence and the subsequently dispatched `Branch Cleanup` deletion evidence;
7. clear `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` after the one-shot maintenance request is closed.

The generated caller listens for `CI`, `Security`, and `CodeQL` completions. If you configure another required gate in `PRODKIT_GATED_CLEANUP_GATES_JSON`, add its workflow display name to the caller's static `workflow_run.workflows` list so the final required gate can trigger authorization.

The gated authorizer requires the trigger to be a default-branch `push`, verifies the exact trigger SHA still equals current `main`, validates all required gates by immutable workflow path and exact SHA, and verifies the target Branch Cleanup caller is `workflow_dispatch` only. Missing/in-progress gates defer. A failed/cancelled/skipped required gate fails closed. Only the last completed required gate event dispatches, preventing normal CI/Security/CodeQL completion fan-out from producing duplicate requests.

Immediately before dispatch the authorizer rereads the default branch. It dispatches the permanent Branch Cleanup workflow with `dry_run=false` plus the exact certified SHA. The downstream cleanup engine independently rechecks that SHA before deletion.

The post-gate authorizer has `actions: write` so it can dispatch Branch Cleanup, but it must remain `contents: read`; it does not delete branches itself.

## 9. Audit drift

Configure `ORG_AUDIT_TOKEN` with read access to the target repositories and run Organization Audit. The auditor rejects:

- missing lifecycle, automatic proof-dispatch, manual cleanup, or post-gate cleanup callers;
- floating central refs;
- obsolete central SHAs;
- retired runner-controller usage;
- proof-dispatch callers that are not `workflow_run` only, are not exact-main/gate-bound, use a mutable/floating central reference, or obtain `contents: write`;
- Trusted Release Proof callers that are not `workflow_dispatch` only;
- non-dispatch destructive cleanup callers;
- post-gate cleanup callers that are not `workflow_run` only, do not use exact-SHA handoff, or obtain `contents: write`;
- the retired nested Release pipeline as the generated release contract;
- local publication implementations in consumer `release.yml`.

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available only for consumers already pinned to historical revisions; do not generate new integrations from them.

## Verification dispatch

After `Release` publishes successfully, do not manually start the normal verification path. Release automatically dispatches `Release Verification` on the immutable release tag through the central verification-dispatch boundary. Manual `Release Verification` dispatch is recovery-only; select the immutable `vX.Y.Z` tag and leave `release_run_id` empty after the parent Release has completed.
