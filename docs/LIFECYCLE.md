# ProdKit workflow lifecycle

`prodkit-workflows` centralizes reusable workload implementation. Consumer repositories retain thin lifecycle callers, choose their runner directly, and own product-specific adapters/release metadata.

## Lifecycle

| Stage | Trigger | Required purpose | Normal evidence |
| --- | --- | --- | --- |
| Pull request | `pull_request` | Correctness/security feedback before merge | `CI`, `Security`, optional `CodeQL` |
| Main branch | `push` to `main` | Certify the actual merge SHA | successful exact-SHA `CI` and `Security` |
| Release proof authorization | `workflow_run` after successful main gates | Detect an unpublished canonical version and dispatch proof only after all required exact-SHA gates are green | bounded `Release Proof Dispatch` evidence |
| Release candidate | automatically dispatched `workflow_dispatch` | Verify permanent gates, run release-only acceptance, build the promotable payload once | completed successful `Trusted Release Proof` + proof-produced payload receipt |
| Promotion | `workflow_run` after completed successful `Trusted Release Proof` | Dispatch the proven version without racing proof completion or waiting for publication | bounded idempotent Release dispatch |
| Publication | promoted `workflow_dispatch` | Import/seal the proof-produced payload, optionally attest, and publish behind the `release` environment | immutable tag + Release + checksums/SBOM; optional GitHub provenance |
| Verification | `workflow_dispatch` on immutable release tag | Independently verify immutable publication without chained-workflow suppression | exact tag/source/metadata/assets/checksums |
| Post-gate cleanup authorization | dormant `workflow_run` caller | Authorize one reviewed exact stale-branch set only after configured exact-SHA gates | gate run IDs + bounded Branch Cleanup dispatch |
| Branch cleanup | explicit `workflow_dispatch` | Validate and delete only exact reviewed refs | SHA-bound cleanup evidence + verified ref absence |
| Metadata repair | canonical metadata push or explicit dispatch | Repair mutable Release presentation only | verified name/body repair with immutable state unchanged |

## Runner ownership

A caller passes `runner_json` directly to the reusable workload. New generated callers do not invoke a runner-policy workflow first.

For trusted workloads the default target is `["self-hosted","Linux","X64"]`; `PRODKIT_RUNNER_JSON` may replace that JSON in generated generic callers. CI/Security fork PRs are forced to GitHub-hosted execution.

This intentionally avoids hosted probes, resolver jobs, destructive workspace preflight, and automatic runner switching. A workload gets one execution target and either succeeds or fails.

Branch Cleanup defaults to `ubuntu-latest`. Post-Gate Branch Cleanup also prefers `ubuntu-latest` but may honor `PRODKIT_RUNNER_JSON` for trusted private-repository control-plane execution where hosted jobs are unavailable. Release Proof Dispatch is intentionally GitHub-hosted because it performs only short read/dispatch authorization and must not occupy the trusted product runner while starting proof.

### Single-runner non-blocking rule

The lifecycle must remain correct with only one trusted self-hosted runner. A job occupying that runner must never dispatch another workflow that also needs the runner and then poll, sleep, or otherwise wait for the child to finish. Such a parent owns the only execution slot its child requires and can deadlock the release indefinitely.

Cross-workflow sequencing therefore uses completion and dispatch boundaries:

1. exact-main CI/Security/optional CodeQL complete independently;
2. `Release Proof Dispatch` observes successful CI/Security completion, rechecks current-main identity and all required exact-SHA gates, recognizes release intent only when the manifest's canonical version is not already tagged, dispatches `Trusted Release Proof`, and exits without waiting;
3. `Trusted Release Proof` acquires the trusted runner, performs release-specific acceptance, builds the proof-produced payload once, completes successfully, and releases the runner;
4. the separate `Release Promotion` caller starts from that completed proof workflow's `workflow_run` event, derives the release version from the exact proof `head_sha`, dispatches Release idempotently, and exits;
5. Release acquires a runner and advances through short sequential release jobs; the protected `release` environment is the human publication approval boundary when required reviewers are configured;
6. Release finishes publication, then a short GitHub-hosted verification-dispatch job validates the immutable tag/source handoff and dispatches `Release Verification` at that immutable tag without waiting for the child. This **verification-dispatch boundary** avoids GitHub’s chained `workflow_run` depth limit;
7. Post-Gate Branch Cleanup, when activated for maintenance, verifies all configured exact-SHA gates, dispatches Branch Cleanup once, and exits without waiting for deletion;
8. the dispatch-only Branch Cleanup workflow performs guarded deletion.

The **proof-completion boundary** remains mandatory: publication authorization searches only completed successful proof runs, so dispatching Release from a job inside an in-progress proof workflow is a race and is forbidden.

The **automatic proof-dispatch boundary** deliberately leaves `Trusted Release Proof` itself `workflow_dispatch` only. That keeps its exact-source event contract unchanged while allowing release evidence generation to start automatically after main gates are complete.

The **cleanup authorization boundary** follows the same non-blocking principle: the post-gate authorizer never performs deletion itself and never waits for the dispatched Branch Cleanup run.

Long-running controller/orchestrator workflows are not part of the generated default lifecycle.

## Pull request and main

Normal CI and Security use compact reusable workflows. Each renders one stable workload job:

- `ci / CI Required`
- `security / Security Required`

Compatibility and scanning dimensions execute as steps, and the final aggregate verifier fails closed if any enabled control failed. Intermediate steps may use `continue-on-error` to collect later evidence; the aggregate evaluates their recorded `outcome`, not only their visual step presentation.

## Automatic release proof authorization

`Release Proof Dispatch` is a permanent `workflow_run` control-plane caller listening for successful `CI` and `Security` completions on `main`. It does not itself certify or publish anything.

The reusable dispatcher requires the trigger SHA to still equal the current default-branch SHA. It derives one consistent SemVer from the version sources declared in `.prodkit/release.json`. A canonical version whose immutable tag already resolves to current main means there is no new release intent, so the run exits successfully without dispatching proof. If that canonical tag exists on another source, the dispatcher fails closed.

The dispatcher then verifies every required exact-SHA push workflow. A required gate that is missing or still active causes a successful `deferred` outcome; the later successful gate completion provides another authorization event. A completed non-success gate fails closed. This means the first of CI/Security to finish never creates a false failed proof run, while the final successful gate can start proof immediately.

Before dispatch, the authorizer validates the repository `Trusted Release Proof` caller at the exact source. That caller must remain `workflow_dispatch` only and must certify `source_sha: ${{ github.sha }}`. Existing active or successful exact-source proof runs suppress duplicates. Current-main identity is checked again immediately before dispatch.

The dispatcher uses `actions: write` only to invoke the proof workflow and remains `contents: read`; it cannot tag, publish, edit files, or delete refs.

## Release candidate

`Trusted Release Proof` remains `workflow_dispatch` only and certifies `${{ github.sha }}` from the branch/ref on which it is dispatched. In the normal v0.1.4+ lifecycle, `Release Proof Dispatch` performs that dispatch automatically on `main`; operators do not click **Run workflow** or paste a source SHA.

Manual proof dispatch is recovery-only after verifying that no active or successful automatic exact-source proof exists.

The reusable proof first verifies that the SHA is still current `main` and that permanent exact-SHA `CI` and `Security` push workflows already succeeded. It **does not rerun those matrices**. The repository-owned `.prodkit/workflows/release-proof.sh` is therefore reserved for genuinely release-specific acceptance not already represented by permanent CI/Security evidence.

For canonical consumers, the reusable proof executes the repository-owned release-build adapter once, writes repository-owned artifacts beneath `release-payload/`, records names/sizes/SHA-256 digests in `release-payload.json`, proves tracked source remained unchanged, and uploads the whole proof artifact. This proof-produced payload is the promotable payload; Release does not rebuild it.

The proof workflow itself does not dispatch Release. Only after the enclosing `Trusted Release Proof` run reaches `completed` with `success` does the separate `Release Promotion` caller run. It passes `${{ github.event.workflow_run.head_sha }}` to `reusable-release-promote.yml`, which rechecks current-main identity, derives one consistent SemVer from `.prodkit/release.json`, avoids a duplicate dispatch while an exact-source Release run is actively queued/running, otherwise dispatches Release, and exits immediately without waiting.

An existing tag or GitHub Release is not closure evidence by itself. If the tag already resolves to the proven SHA, promotion may re-dispatch the idempotent Release workflow so the publisher can verify or resume the exact release transaction without rebuilding already-complete stages.

Ordinary main pushes do not automatically become releases when their canonical version is already represented by its immutable tag. The unpublished canonical version in the merged source is the release-intent signal.

## Publication and human approval

`Release` remains dispatch-only, but normal lifecycle dispatch is owned by the proof-completion `Release Promotion` workflow. The release target is `${{ github.sha }}` from the dispatch on `main`.

The consumer Release caller is deliberately thin: it passes the exact source and authoritative `Trusted Release Proof` workflow path to `reusable-release.yml`. It does not duplicate GitHub API proof-gate code. The reusable publisher centrally requires a completed successful proof dispatch for the exact SHA and independently rechecks successful `push` runs of `CI` and `Security` for that same SHA. Those are cheap authorization checks, not workload reruns.

Human approval belongs at the protected `release` environment immediately before publication mutation when repository policy requires it. Evidence generation can therefore proceed automatically, while the actual publication boundary remains reviewer-controlled.

Publication is checkpointed at job boundaries:

1. **prepare** — validate current-main identity, permanent CI/Security evidence, exact completed-proof authorization, manifest/version/notes, and any already-published release; capture the exact successful proof run ID;
2. **build/seal** — download the proof artifact from that exact run, verify `release-payload.json`, import the proof-produced payload, add central source/SBOM evidence, seal everything with `release-metadata.json` and `SHA256SUMS`, and upload one sealed workflow artifact;
3. **attest** — optionally download and attest that sealed payload;
4. **publish** — behind the configured `release` environment, download the same sealed payload, create or recover the immutable tag/draft Release, upload only missing or mismatched assets, verify the draft, and publish.

The sealed workflow artifact is the retry boundary. When a late job fails, operators should use GitHub **Re-run failed jobs** rather than restarting the whole workflow. GitHub re-runs failed jobs and dependent jobs while successful earlier jobs remain complete, so a failed attestation or publication does not rerun proof, regenerate the repository payload, or rebuild a successful sealed payload.

Draft recovery is incremental. Correct existing draft assets are retained; only unexpected or checksum-mismatched assets are removed and re-uploaded. A fully published release is verified during preflight and treated as idempotently complete.

GitHub Artifact Attestations are optional because feature availability depends on repository visibility and GitHub organization plan. The reusable publisher defaults `attest` to `false`. A consumer may explicitly set `attest: true` only when the feature is available; once enabled, attestation failure is release-fatal. Exact-source gates, proof-produced payload digests, SBOM generation, `SHA256SUMS`, sealed-payload verification, and draft read-back remain independent of GitHub Artifact Attestations.

The publisher verifies the draft transaction before making it public. Post-publication verification is intentionally owned by the independent `Release Verification` workflow rather than duplicated inside the publisher.

Tag creation never reruns the proof and a product/release failure never switches runners.

## Independent verification

The generated `Release Verification` caller is `workflow_dispatch` only. The parent Release workflow invokes `reusable-release-verification-dispatch.yml` after publication succeeds; the dispatcher validates the exact parent Release run, immutable `vX.Y.Z` tag and published target, then dispatches verification on that tag and exits immediately. The verification caller derives `source_sha` from `${{ github.sha }}` at the immutable tag and forwards only the parent Release run ID for provenance binding.

This **verification-dispatch boundary** avoids another chained `workflow_run` hop. Verification is read-only. It derives the version, notes path, and expected Release name from immutable source metadata; recursively resolves annotated/lightweight tags to the exact source SHA; verifies draft/prerelease/target metadata; requires canonical Release notes; requires the remote asset set to match `SHA256SUMS` exactly; and verifies GitHub asset digests or downloads/hashes assets when the API digest is unavailable.

Because verification is dispatched only after reusable publication succeeds, and the dispatcher itself is short and non-blocking, it cannot hold the runner needed by publication or wait on the verification child.

## Post-gate branch cleanup

`Post-Gate Branch Cleanup` is a permanent dormant `workflow_run` authorization caller. It does nothing while `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` is empty.

When activated with a reviewed exact branch list, the reusable authorizer requires the triggering run to originate from a default-branch `push`, requires the trigger `head_sha` to equal the current default-branch SHA, validates the target cleanup workflow remains `workflow_dispatch` only, and verifies configured required exact-SHA push workflows by immutable workflow path.

The default required gates are CI and Security. `PRODKIT_GATED_CLEANUP_GATES_JSON` may provide an explicit non-empty list of `{name,path}` objects. Missing or in-progress required gates defer safely; a completed non-success required gate fails closed. Only the final completed required gate event may dispatch, preventing CI/Security/CodeQL completion fan-out from creating duplicate cleanup requests.

Immediately before dispatch the authorizer rereads the default branch. It then calls permanent `Branch Cleanup` with the exact reviewed branch list, `dry_run=false`, and exact certified SHA. The authorizer has `actions: write` but remains `contents: read`; it cannot delete refs.

The downstream Branch Cleanup workflow remains the only mutation boundary. It independently requires `workflow_dispatch`, performs complete preflight, rejects default/protected/open-PR branches, revalidates every target SHA immediately before deletion, rechecks default SHA throughout mutation, and verifies every deleted ref is absent.

## Metadata repair

Release metadata repair is separate from publication. It may reconcile canonical GitHub Release name/body from current repository metadata only after proving historical tag and payload identity remain unchanged.

It cannot move/create tags, rebuild or replace assets, change checksums, or change publication flags.

## Backward compatibility

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available for older immutable consumers. The compatibility release pipeline delegates proof authorization and publication to the same resumable central publisher instead of maintaining a second proof-gate implementation. Its proof-payload reuse flag defaults off so historical proof adapters remain valid until deliberately migrated.

Consumers adopting v0.1.4 should pin the complete generated workflow family to the exact v0.1.4 commit and include `release-proof-dispatch.yml`. Earlier immutable pins keep their historical manual-proof behavior.

Quality is a release-presentation reference, not a runner-controller dependency.
