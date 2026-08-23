# Consumer Contracts

This document is normative for consumers of `ProdKit-dev/prodkit-workflows`. Reusable workflows, caller templates, bootstrap output, validators, organization audit, and contract tests must implement the same guarantees.

## Ownership boundary

`prodkit-workflows` owns reusable workload implementation: CI/Security aggregation, toolchain setup, evidence generation, exact-source proof mechanics, completed-proof promotion, guarded publication, metadata repair, CodeQL orchestration, branch-cleanup safety enforcement, post-gate cleanup authorization, and organization audit.

Consumer repositories own:

- workflow triggers and direct runner target selection;
- explicit branch-cleanup target selection, either as dispatch input or a reviewed dormant-caller repository variable;
- `.prodkit/release.json`;
- canonical version notes/changelog;
- repository-specific adapters beneath `.prodkit/workflows/`.

New consumers **must not** insert a runner-controller workflow between their caller and the reusable workload. They pass `runner_json` directly.

All cross-repository reusable workflow calls must pin an exact lowercase 40-character Git commit SHA.

## Reusable surface

Normative reusable workloads:

- `reusable-ci-compact.yml` — default compact CI;
- `reusable-security-compact.yml` — default compact Security;
- `reusable-ci.yml` — expanded compatibility CI;
- `reusable-security.yml` — expanded compatibility Security;
- `reusable-codeql.yml`;
- `reusable-branch-cleanup.yml`;
- `reusable-gated-branch-cleanup.yml`;
- `reusable-release-proof.yml`;
- `reusable-release-promote.yml`;
- `reusable-release.yml`;
- `reusable-release-verification.yml`;
- `reusable-release-verification-dispatch.yml`;
- `reusable-release-metadata-current.yml`;
- `reusable-release-metadata.yml`;
- `reusable-org-audit.yml`.

Compatibility-only surfaces retained for already-pinned consumers:

- `reusable-runner-policy.yml`;
- `reusable-release-pipeline.yml`.

Bootstrap and organization audit must not require new consumers to use those compatibility-only controllers.

## Direct runner contract

Generated callers may read the non-secret Actions variable `PRODKIT_RUNNER_JSON`. Its value is the complete JSON value accepted by GitHub `runs-on`, for example:

```json
["self-hosted","Linux","X64"]
```

When unset, trusted generated workloads default to that self-hosted label set.

Generated CI/Security callers force fork-originated pull requests to `"ubuntu-latest"`. Persistent trusted runners must not execute fork code by default.

New callers must not contain:

- `PRODKIT_RUNNER_MODE`;
- a `runner` prerequisite job whose sole purpose is routing;
- `needs.runner.outputs.runner_json`;
- hosted availability probes or automatic failover state machines.

A workload gets one runner target. Product/security/release failures never cause automatic execution on a second trust boundary.

Branch Cleanup is the deliberate maintenance exception: its canonical caller passes `"ubuntu-latest"` directly so repository housekeeping does not depend on persistent product runners. Post-Gate Branch Cleanup may use `PRODKIT_RUNNER_JSON` when an installation cannot execute trusted private-repository control-plane jobs on GitHub-hosted infrastructure; its fallback remains `"ubuntu-latest"`.

## Lifecycle

1. **Pull request** — CI, Security, optional CodeQL.
2. **Main** — exact-main CI and Security certify the merge SHA.
3. **Release candidate** — dispatch `Trusted Release Proof`; it verifies those permanent gates, runs only release-specific acceptance, and produces the promotable repository payload once. The proof caller must not dispatch Release itself.
4. **Promotion** — a separate `Release Promotion` caller is triggered by `workflow_run` only after `Trusted Release Proof` is `completed` with `success`; it carries the completed proof's `head_sha` into the bounded reusable promotion workload and exits after idempotently dispatching Release.
5. **Publication** — Release imports the exact proof-produced payload, seals it with central evidence, and publishes it without rebuilding the repository payload.
6. **Verification dispatch** — after publication succeeds, Release calls the bounded verification dispatcher, which validates the exact parent run and immutable tag then triggers `Release Verification` with `workflow_dispatch` on that tag and exits. This **verification-dispatch boundary** avoids chained-`workflow_run` suppression.
7. **Verification** — dispatch-only, read-only `Release Verification` independently checks the immutable published transaction.
8. **Cleanup** — after merge/release closure, either explicitly dispatch Branch Cleanup against exact stale branch names or activate the dormant Post-Gate Branch Cleanup caller with a reviewed exact branch list. Both routes end at the same dispatch-only, exact-SHA-bound deletion engine and never move tags/releases.
9. **Metadata repair** — independently reconcile mutable Release name/body while proving immutable source/payload identity is unchanged.

This proof-completion boundary is mandatory. Publication authorization accepts only completed successful proof runs, so dispatching Release from a job inside the still-running proof workflow is a race and is non-compliant.

Operators do not manually copy source/target SHAs between proof, promotion, and release workflows.

## CI

Generated consumers use `reusable-ci-compact.yml` by default. It owns checkout, adapter containment, toolchain provisioning, compatibility selection, PostgreSQL isolation, and final aggregate outcome evaluation.

Available adapters:

- `ci-hygiene.sh`;
- `ci-python.sh` with `PRODKIT_PYTHON_VERSION`;
- `ci-node.sh` with `PRODKIT_NODE_VERSION`;
- `ci-postgres.sh` with isolated PostgreSQL connection variables;
- `ci-container.sh`;
- `ci-custom.sh`.

Compact CI supports Python `3.12`, `3.13`, `3.14` and Node `20`, `22`, `24`. Duplicate or unsupported requested versions fail closed.

Enabled dimensions run as steps inside one reusable job named `CI Required`. Intermediate steps may use `continue-on-error` only to collect more evidence; their recorded `outcome` remains authoritative and the final verifier fails if any enabled control failed. A visually continued step must not be interpreted as a passed control.

`reusable-ci.yml` is the deliberate expanded/parallel compatibility path.

## Security

Generated consumers use `reusable-security-compact.yml` by default. It owns checkout, full-history Gitleaks, dependency-audit adapters, source SPDX SBOM, container vulnerability scan, custom security, evidence uploads, and final aggregate verification.

Repository adapters:

- `security-python.sh`;
- `security-node.sh`;
- `security-container-build.sh`;
- `security-custom.sh`.

Enabled controls must all pass. `continue-on-error` on intermediate evidence stages does not make a failed required control green.

`reusable-security.yml` remains the expanded compatibility path.

## Stable required checks

The required branch-protection identities are:

- caller job `ci` + reusable job `CI Required` => `ci / CI Required`;
- caller job `security` + reusable job `Security Required` => `security / Security Required`.

Do not require individual compatibility/scanning steps as branch-protection checks.

## CodeQL

`reusable-codeql.yml` owns the language matrix, initialization/analysis, SARIF evidence, and `CodeQL Required` aggregation. A repository may provide `.prodkit/workflows/codeql-check.sh` for its SARIF acceptance policy.

CodeQL is opt-in. Generated CodeQL callers do not execute fork PRs on persistent trusted runners.

## Branch Cleanup

`reusable-branch-cleanup.yml` owns destructive branch-cleanup safety and execution. The canonical generated caller remains `workflow_dispatch` only and passes:

```yaml
branches_json: ${{ inputs.branches_json }}
expected_default_sha: ${{ inputs.expected_default_sha != '' && inputs.expected_default_sha || github.sha }}
dry_run: ${{ inputs.dry_run }}
runner_json: '"ubuntu-latest"'
```

`expected_default_sha` is optional at the caller boundary. A direct operator dispatch may omit it and preserve the v0.1.1 behavior of binding cleanup to the dispatched `${{ github.sha }}`. A trusted upstream authorizer may supply an already-reviewed exact SHA; if the default branch moved before cleanup begins, the reusable cleanup workload fails before deletion.

`branches_json` is a non-empty JSON array of unique exact branch names; wildcards/pattern expansion are not supported. The reusable workflow accepts at most 100 targets and applies conservative Git ref-name validation.

Before any deletion it:

- reads the repository default branch and requires its current ref SHA to equal `expected_default_sha`;
- rejects the default branch itself;
- treats already-absent refs as idempotent success;
- rejects any requested branch that is protected;
- enumerates all open pull requests and rejects branches used as an open PR head;
- preflights the complete target set and performs zero mutations when any safety rejection exists.

When `dry_run=true`, validated present refs are reported as `would_delete` and no mutation occurs. When mutation is enabled, the workflow rechecks the exact default SHA before deletion and before each subsequent ref deletion, deletes only the explicit validated targets, then reads each ref back and requires `404` absence. The workflow emits structured `cleanup-evidence.json` content to logs/step summary and exposes compact evidence as a workflow output.

The canonical caller grants `contents: write` and `pull-requests: read` only to the cleanup job. It must not be exposed through `push`, `schedule`, `issue_comment`, or `workflow_run`; organization audit rejects those mutation triggers. Cleanup is maintenance, not a required branch-protection check.

## Post-Gate Branch Cleanup

`reusable-gated-branch-cleanup.yml` is an authorization/dispatch workload. It **does not delete Git refs** and receives no `contents: write` permission.

The generated `post-gate-branch-cleanup.yml` caller is `workflow_run` only, listens by default for `CI`, `Security`, and `CodeQL` completions on `main`, and is dormant unless the non-secret repository variable `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` is a non-empty JSON array of exact reviewed branch names.

The generated caller supplies:

```yaml
branches_json: ${{ vars.PRODKIT_GATED_CLEANUP_BRANCHES_JSON }}
expected_default_sha: ${{ github.event.workflow_run.head_sha }}
required_gates_json: ${{ vars.PRODKIT_GATED_CLEANUP_GATES_JSON != '' && vars.PRODKIT_GATED_CLEANUP_GATES_JSON || '[{"name":"CI","path":".github/workflows/ci.yml"},{"name":"Security","path":".github/workflows/security.yml"}]' }}
cleanup_workflow_file: branch-cleanup.yml
```

The authorization reusable requires:

- `github.event_name == workflow_run`;
- the triggering workflow run to originate from a `push`;
- the trigger `head_sha` to equal `expected_default_sha`;
- the trigger `head_branch` to equal the repository default branch;
- the current default-branch ref to still equal that exact SHA;
- a non-empty unique branch list and a non-empty unique required-gate list;
- each required gate to be identified by an explicit `.github/workflows/*.yml` path and display name;
- the target cleanup workflow at the exact SHA to exist, expose only `workflow_dispatch`, include the exact-SHA input, and delegate to `reusable-branch-cleanup.yml`.

The authorizer queries exact-SHA `push` runs and selects the latest run for each required workflow path. Missing/in-progress gates produce a successful `deferred` authorization result without dispatch. A completed non-success required gate produces `gate_failed` and fails closed. When every required gate is successful, the authorizer selects the last completed required gate using workflow update time plus run ID as a deterministic tie-breaker; only the matching trigger event may dispatch cleanup. Other completion events produce `not_final_gate` without dispatch.

The default branch is reread immediately before dispatch. The authorizer then calls the permanent Branch Cleanup workflow with `dry_run=false`, the exact reviewed branch list, and the exact certified SHA. The downstream dispatch-only cleanup workflow revalidates the SHA before any mutation.

`PRODKIT_GATED_CLEANUP_GATES_JSON` may override the default CI/Security gates. If a repository adds another required gate, that workflow's display name must also be present in the caller's static `workflow_run.workflows` list so its completion can become the final authorization event.

The post-gate caller receives `actions: write` only to dispatch the permanent cleanup workflow. It remains `contents: read`; direct branch deletion in the authorizer is non-compliant.

## Trusted Release Proof

`reusable-release-proof.yml` accepts an exact `source_sha`, verifies it remains current configured `main`, and verifies successful permanent exact-SHA `CI` and `Security` push runs before doing release-specific work. It does not rerun those permanent matrices.

The repository `.prodkit/workflows/release-proof.sh` adapter is reserved for acceptance that is genuinely release-specific. For canonical new consumers, the reusable proof then executes `.prodkit/workflows/release-build.sh` once using the configured baseline toolchains, writes the repository-owned files beneath `release-payload/`, records each file's size and SHA-256 in `release-payload.json`, confirms tracked source remained immutable, and uploads the proof artifact.

The generated proof caller supplies:

```yaml
source_sha: ${{ github.sha }}
required_workflows_json: '["CI","Security"]'
prepare_release_payload: true
```

It has no release-dispatch job and no `actions: write` permission. A proof on another SHA/event does not satisfy publication. The proof-produced payload receipt is bound to repository, exact source SHA, and version.

## Release Promotion

The generated `release-promotion.yml` caller listens for:

```yaml
workflow_run:
  workflows: ["Trusted Release Proof"]
  types: [completed]
```

Its promotion job runs only when the upstream event was `workflow_dispatch` and the proof conclusion is `success`. It passes `${{ github.event.workflow_run.head_sha }}` to `reusable-release-promote.yml`, which rechecks current-main identity, derives the canonical SemVer, avoids duplicate active exact-source Release runs, dispatches Release, and exits without polling or waiting for publication.

Promotion must not be embedded as a `needs: proof` job in `Trusted Release Proof`; job completion is not workflow completion.

## Publication

New generated Release callers call `reusable-release.yml` directly. They do not use `reusable-release-pipeline.yml`, do not implement a local API proof gate, and do not implement publication logic.

The generated caller supplies:

```yaml
target_sha: ${{ github.sha }}
proof_workflow_file: .github/workflows/trusted-release-proof.yml
reuse_proof_payload: true
```

The central publisher owns proof authorization. It selects the latest completed successful `workflow_dispatch` of `proof_workflow_file` for the exact target SHA, captures that exact proof run ID, independently rechecks successful exact-SHA `push` runs for `CI` and `Security`, and verifies the target is still current `main`. Dynamic workflow display names are never authorization identities.

Publication is split into resumable jobs:

- **prepare** validates source/evidence/manifest state, captures the exact proof run ID, and recognizes an already-complete published release;
- **build/seal** downloads the exact proof artifact, verifies `release-payload.json`, imports the proof-produced repository payload, adds source/SBOM evidence, creates `release-metadata.json` and `SHA256SUMS`, and uploads the resulting **sealed payload** as a workflow artifact;
- **attest** optionally downloads and attests the same sealed payload;
- **publish** downloads that sealed payload, creates or recovers the immutable tag/draft Release, retains already-correct draft assets, uploads only missing or mismatched assets, verifies the draft, and makes it public.

The canonical path never reruns `release-build.sh` during Release. A compatibility-only `reuse_proof_payload: false` path remains available for historical proof artifacts; in that mode the publisher preserves the established `RELEASE_OUTPUT_DIR` release-build contract.

Successful job boundaries are checkpoints. If attestation or publication fails after build/seal succeeded, operators use GitHub **Re-run failed jobs**; the successful earlier jobs remain complete and downstream jobs reuse their workflow artifacts. A failed publication resumes a compatible draft rather than unconditionally deleting and re-uploading all assets.

GitHub Artifact Attestations are capability-dependent and therefore opt-in in both the direct publisher and retained compatibility pipeline. The default release contract does not require them. When explicitly enabled, attestation failure remains release-fatal. Exact-source proof, proof-produced payload digests, SBOM generation, `SHA256SUMS`, sealed-payload verification, and draft asset read-back remain required independently of attestation support.

The publisher verifies the draft before publication. Independent post-publication checksum/digest verification belongs to `Release Verification`; it is not duplicated in the publisher.

Tag movement is forbidden. An existing tag on another commit fails hard. A verified already-published release is treated idempotently.

## Release manifest

`.prodkit/release.json` schema version 1 defines version sources, canonical notes/changelog, release-build adapter, artifact directory, source-archive policy, and Release name template. Unknown properties are rejected.

The visible organization contract is:

- tag `vX.Y.Z`;
- canonical GitHub Release title defined by the repository manifest;
- canonical version document begins `# vX.Y.Z — <milestone>` or `# ProdKit Workflows vX.Y.Z` for the workflow control plane;
- GitHub Release body equals the canonical version document.

## Metadata repair

`reusable-release-metadata-current.yml` selects an explicit published version/source pair or the current workspace version/tag, then delegates to `reusable-release-metadata.yml`.

Repair verifies the immutable tag and complete published checksum set before changing mutable presentation. It may patch canonical Release `name` and `body`, then re-verifies tag, publication flags/timestamp where applicable, asset identity, digests, and payload checksums.

It cannot create/move tags, create a missing Release, rebuild/upload/delete/replace assets, alter checksums, or change draft/prerelease state.

## Bootstrap surface

`bootstrap_consumer.py` installs callers for:

- CI;
- Security;
- Branch Cleanup;
- Post-Gate Branch Cleanup;
- Trusted Release Proof;
- Release Promotion;
- Release;
- Release Verification;
- Release Metadata;
- optionally CodeQL.

Generated callers directly invoke the appropriate reusable workload and directly provide `runner_json`. CI/Security use compact workflows by default. Branch Cleanup remains an explicit dispatch-only mutation boundary; Post-Gate Branch Cleanup is a dormant workflow-run authorizer that can only dispatch that boundary.

## Organization audit

The organization auditor requires these workflow families at the requested immutable central SHA:

- `ci.yml` -> `reusable-ci-compact.yml`;
- `security.yml` -> `reusable-security-compact.yml`;
- `branch-cleanup.yml` -> `reusable-branch-cleanup.yml`;
- `post-gate-branch-cleanup.yml` -> `reusable-gated-branch-cleanup.yml`;
- `trusted-release-proof.yml` -> `reusable-release-proof.yml`;
- `release-promotion.yml` -> `reusable-release-promote.yml`;
- `release.yml` -> `reusable-release.yml`;
- `release-verification.yml` -> `reusable-release-verification.yml`;
- `release-metadata.yml` -> `reusable-release-metadata-current.yml`.

It also rejects floating references, retired runner-controller usage, non-dispatch destructive branch cleanup, non-`workflow_run` post-gate cleanup, post-gate callers with `contents: write`, promotion before proof workflow completion, manually copied release target semantics, duplicated consumer proof gates, missing central proof delegation, and local publication implementation in consumer `release.yml`.

## Compatibility policy

Already-pinned consumers remain immutable and may continue using `reusable-runner-policy.yml` or `reusable-release-pipeline.yml` until deliberately migrated. The retained compatibility release pipeline delegates to the same central proof authorization and resumable publisher rather than maintaining a second implementation. Proof-payload reuse defaults off in that compatibility surface so historical proof adapters remain valid. New bootstrap output and current organization policy use the direct proof-once/promote-after-completion/publish-once architecture plus the dispatch-only Branch Cleanup engine and optional dormant exact-main Post-Gate Branch Cleanup authorizer.
