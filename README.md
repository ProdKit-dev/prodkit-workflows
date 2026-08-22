# ProdKit Workflows

`prodkit-workflows` is the organization-level library of reusable CI, Security, release, CodeQL, branch-cleanup, metadata, and governance workloads for ProdKit repositories.

The reliability boundary is intentionally simple: **the consumer caller chooses a runner; `prodkit-workflows` executes the workload.** Runner selection is not a separate workflow state machine.

## Design principles

- **Direct execution.** CI, Security, proof, promotion, release, verification, metadata, CodeQL, cleanup authorization, and audit callers pass `runner_json` directly to the reusable workload they invoke. There is no default probe/resolver/preflight controller hop.
- **Thin consumers.** Generated callers define triggers and inputs; reusable workflows own API authorization, evidence checks, build/publish mechanics, cleanup safety, and retry semantics. Release callers do not copy a local proof-gate implementation.
- **No expensive gate duplication.** Permanent exact-SHA CI/Security are verified as evidence by Trusted Release Proof; they are not rerun inside proof. The repository release payload is built once during proof and promoted unchanged into publication.
- **Completion-boundary promotion.** `Trusted Release Proof` finishes first. A separate `Release Promotion` caller starts from its successful `workflow_run` completion event, then dispatches Release. Release can therefore never race a proof run that is still `in_progress`.
- **One workload job for normal CI and Security.** Compact CI exposes `ci / CI Required`; compact Security exposes `security / Security Required`. Compatibility/scanning dimensions remain visible as steps.
- **Immutable reuse.** Cross-repository callers pin a full 40-character `prodkit-workflows` commit SHA. Floating branches/tags are not production contracts.
- **Fork safety.** Generated CI/Security callers force fork-originated pull requests to `ubuntu-latest`. Persistent trusted runners never execute untrusted fork code by default.
- **Dispatch-only deletion.** Branch Cleanup remains a post-merge/post-release maintenance operation. It accepts exact branch names, defaults to dry-run, and rejects any destructive invocation that is not rooted in explicit `workflow_dispatch` authorization.
- **Optional gated authorization.** Post-Gate Branch Cleanup may verify exact-main CI/Security/CodeQL evidence and dispatch the permanent Branch Cleanup workflow. It never receives `contents: write` and never deletes refs itself.
- **Configurable runner target.** Generated callers read optional `PRODKIT_RUNNER_JSON`. When unset, trusted work defaults to `["self-hosted","Linux","X64"]`. This variable is the complete JSON value passed to `runs-on`; it is not a routing mode.
- **Exact-main releases.** `Trusted Release Proof` certifies the workflow-dispatched `${{ github.sha }}`. `Release Promotion` carries the completed proof run's `head_sha`. `Release` publishes the workflow-dispatched `${{ github.sha }}`. Operators do not copy SHAs between workflows.
- **Resumable publication.** The proof-produced repository payload and later sealed publication payload are workflow-artifact checkpoints. Late failures resume from successful job boundaries.
- **Fail closed.** Missing evidence, invalid manifests, failed enabled controls, tag movement, unsafe cleanup targets, path escapes, unsafe payloads, checksum mismatches, or metadata repair that changes immutable state stop the operation.

## Reusable workload surface

| Capability | Default reusable workflow | Stable result |
| --- | --- | --- |
| Compact CI | `.github/workflows/reusable-ci-compact.yml` | `CI Required` |
| Compact Security | `.github/workflows/reusable-security-compact.yml` | `Security Required` |
| Expanded CI | `.github/workflows/reusable-ci.yml` | `CI Required` |
| Expanded Security | `.github/workflows/reusable-security.yml` | `Security Required` |
| Branch cleanup | `.github/workflows/reusable-branch-cleanup.yml` | explicit dry-run/destructive cleanup evidence |
| Post-gate cleanup authorization | `.github/workflows/reusable-gated-branch-cleanup.yml` | exact-main gate evidence + bounded cleanup dispatch |
| Trusted release proof | `.github/workflows/reusable-release-proof.yml` | exact-source proof + promotable repository payload |
| Release promotion | `.github/workflows/reusable-release-promote.yml` | bounded idempotent Release dispatch |
| Guarded release publication | `.github/workflows/reusable-release.yml` | prepare → import/seal → optional attest → publish |
| Independent release verification | `.github/workflows/reusable-release-verification.yml` | immutable publication verification |
| Release metadata selection | `.github/workflows/reusable-release-metadata-current.yml` | metadata workflow |
| Guarded metadata repair | `.github/workflows/reusable-release-metadata.yml` | metadata repair |
| CodeQL | `.github/workflows/reusable-codeql.yml` | `CodeQL Required` |
| Organization audit | `.github/workflows/reusable-org-audit.yml` | audit |

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain in the repository only for consumers already pinned to older revisions. The compatibility release pipeline delegates to the same central resumable publisher; its proof-payload reuse flag defaults off for historical proof adapters. Bootstrap, generated callers, organization audit expectations, and control-plane self-callers use the direct proof-once/publish-once architecture.

## Consumer setup

Generate callers and repository adapters from an exact reviewed control-plane SHA:

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <40-character-commit-sha> \
  --destination ../prodkit-annotation
```

Bootstrap creates:

```text
.github/workflows/
  ci.yml
  security.yml
  branch-cleanup.yml
  post-gate-branch-cleanup.yml
  trusted-release-proof.yml
  release-promotion.yml
  release.yml
  release-verification.yml
  release-metadata.yml
.prodkit/
  release.json
  workflows/
    ci-hygiene.sh
    ci-python.sh
    ci-node.sh
    ci-postgres.sh
    ci-container.sh
    ci-custom.sh
    security-python.sh
    security-node.sh
    security-container-build.sh
    security-custom.sh
    release-build.sh
    release-proof.sh
    codeql-check.sh
```

`--include-codeql` additionally creates `.github/workflows/codeql.yml`.

For a different trusted runner target, set the non-secret Actions variable `PRODKIT_RUNNER_JSON`, for example:

```text
["self-hosted","Linux","X64","prodkit-ci"]
```

The value must be valid JSON accepted by `runs-on`. Do not use it to route fork PRs to persistent infrastructure; generated CI/Security callers retain the hosted fork guard.

## Compact CI and Security

Compact CI supports Python `3.12`, `3.13`, `3.14` and Node `20`, `22`, `24`; a caller may choose any supported non-empty subset. PostgreSQL, container, hygiene, and custom adapters are independently enabled.

Compact execution keeps dimensions as steps in one required workload job. Enabled steps may use `continue-on-error` so later evidence can still be collected, but the final aggregate verifier fails the job if any required setup/control failed. A visually continued step must not be interpreted as a passed control. Aggregate verification intentionally skips GitHub-cancelled superseded runs while remaining fail-closed for genuine completed failures.

Expanded `reusable-ci.yml` and `reusable-security.yml` remain available when a repository deliberately needs parallel matrix jobs.

## Branch Cleanup

Branch Cleanup is deliberately outside release authorization. After a merge or release is fully closed, explicitly dispatch the generated `Branch Cleanup` workflow with a JSON array of exact stale branch names. Wildcards and pattern expansion are not supported.

The canonical caller defaults to `dry_run=true` and `ubuntu-latest`. The reusable workflow binds cleanup to the reviewed default-branch SHA, preflights the complete target set before mutation, rejects protected/default/open-PR branches, revalidates branch identity immediately before deletion, and verifies deleted refs are absent afterward. A race or unsafe target fails closed.

`v0.1.2` adds an optional `expected_default_sha` input to the caller. Direct operators may leave it empty and retain the normal `${{ github.sha }}` binding. A trusted upstream authorizer may provide a previously certified exact SHA; a default-branch movement between authorization and cleanup then fails before deletion.

### Post-Gate Branch Cleanup

Bootstrap also installs a permanent `Post-Gate Branch Cleanup` caller. It is dormant while `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` is empty.

When populated with a reviewed JSON array of exact branch names, the caller reacts to completed `CI`, `Security`, or `CodeQL` runs on `main`. The reusable authorization workflow requires the trigger to originate from a default-branch `push`, requires its `head_sha` to remain current, verifies the target Branch Cleanup workflow is still dispatch-only, and verifies required exact-SHA push gates by immutable workflow path.

The default gate set is CI + Security. `PRODKIT_GATED_CLEANUP_GATES_JSON` may supply an explicit non-empty list of `{name,path}` objects. Missing/in-progress gates defer; completed non-success gates fail closed. Only the last completed required gate event is allowed to dispatch, so normal CI/Security/CodeQL completion fan-out does not create multiple cleanup requests.

The authorizer rereads the default branch immediately before dispatch and passes the exact certified SHA into the permanent Branch Cleanup workflow with `dry_run=false`. It has `actions: write` for that bounded dispatch but remains `contents: read`, so destructive behavior stays exclusively in the existing cleanup engine.

Recommended use is manual Branch Cleanup dry-run first, then temporarily set `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` for the exact-main cycle that should apply the reviewed deletion set, and clear the variable after closure.

## Canonical lifecycle

```text
pull request
  -> CI + Security

merge to main
  -> exact-main CI + Security
  -> optional Post-Gate Branch Cleanup authorization
     -> exact gate evidence
     -> workflow_dispatch Branch Cleanup with certified main SHA
     -> existing guarded deletion engine

workflow_dispatch Trusted Release Proof
  -> certifies github.sha (current main)
  -> verifies exact-SHA CI + Security evidence; does not rerun them
  -> runs release-specific acceptance only
  -> runs release-build once
  -> uploads proof-produced payload + digest receipt
  -> workflow completes successfully

workflow_run Release Promotion
  -> starts only after completed successful Trusted Release Proof
  -> carries the proof run head_sha
  -> rechecks current-main identity
  -> dispatches Release idempotently and exits

workflow_dispatch Release(version)
  -> github.sha is target source
  -> central prepare: reauthorize exact-SHA CI + Security + exact completed proof run
  -> import/seal: download and verify proof-produced payload
  -> add source archive + SBOM + release metadata + SHA256SUMS
  -> optional attest: consume sealed workflow artifact
  -> publish: consume same sealed artifact
  -> immutable vX.Y.Z tag
  -> resumable draft-first GitHub Release
  -> draft upload/read-back verification
  -> publish

workflow_run Release Verification
  -> independent post-publication checksum/digest verification

workflow_dispatch Branch Cleanup
  -> dry-run explicit stale branch names
  -> operator reviews cleanup evidence
  -> destructive dispatch deletes only the exact validated refs
```

GitHub Artifact Attestations are an optional additional provenance layer. They default off because feature availability depends on repository visibility and organization plan. Explicitly enabling attestations keeps failure release-fatal; the baseline release still requires exact-source proof, proof-produced payload digests, SBOM, `SHA256SUMS`, sealed-payload verification, and independent published-asset verification.

A release caller does not accept a manually copied `target_sha` and does not implement its own proof API query. A proof caller does not accept a manually copied `source_sha`. Dispatch proof from the intended `main` revision; promotion is automatic only after that proof workflow has completed successfully.

### Retry behavior

Do not restart a release from scratch after a late-stage failure. Use GitHub **Re-run failed jobs** on the same Release workflow run. GitHub re-runs failed jobs and their dependent jobs while successful earlier jobs remain complete. A publication failure therefore reuses the successful sealed artifact; it does not rerun proof or `release-build.sh`.

The publisher also resumes partial draft publication: already-correct assets are retained, and only missing or checksum-mismatched assets are uploaded again. If publication already completed, preflight verifies it and exits idempotently.

Mutable Release presentation repair is separate from publication. It may update canonical name/body only after proving the immutable tag and complete published payload remain unchanged.

## Organization policy

Organization rulesets should require:

- `ci / CI Required`
- `security / Security Required`

Run `scripts/audit_org.py` or the Organization Audit workflow to find missing lifecycle callers, floating central refs, obsolete central SHAs, retired runner-controller usage, unsafe destructive-cleanup triggers, post-gate cleanup callers that can mutate refs directly, promotion-before-proof-completion topology, duplicated consumer proof gates, or local publication implementations.

See `docs/CONTRACTS.md`, `docs/RUNNERS.md`, `docs/LIFECYCLE.md`, and `docs/ADOPTION.md` for the normative integration contract.
