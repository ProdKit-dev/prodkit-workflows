# ProdKit workflow lifecycle

`prodkit-workflows` centralizes reusable workload implementation. Consumer repositories retain thin lifecycle callers, choose their runner directly, and own product-specific adapters/release metadata.

## Lifecycle

| Stage | Trigger | Required purpose | Normal evidence |
| --- | --- | --- | --- |
| Pull request | `pull_request` | Correctness/security feedback before merge | `CI`, `Security`, optional `CodeQL` |
| Main branch | `push` to `main` | Certify the actual merge SHA | successful exact-SHA `CI` and `Security` |
| Post-gate cleanup authorization | dormant `workflow_run` caller | Authorize one reviewed exact stale-branch set only after configured exact-SHA gates | gate run IDs + bounded Branch Cleanup dispatch |
| Branch cleanup | explicit `workflow_dispatch` | Validate and delete only exact reviewed refs | SHA-bound cleanup evidence + verified ref absence |
| Release candidate | explicit `workflow_dispatch` | Verify permanent gates, run release-only acceptance, build the promotable payload once | completed successful `Trusted Release Proof` + proof-produced payload receipt |
| Promotion | `workflow_run` after completed successful `Trusted Release Proof` | Dispatch the proven version without racing proof completion or waiting for publication | bounded idempotent Release dispatch |
| Publication | promoted `workflow_dispatch` | Import/seal the proof-produced payload, optionally attest, and publish | immutable tag + Release + checksums/SBOM; optional GitHub provenance |
| Verification | `workflow_run` after Release | Independently verify immutable publication | exact tag/source/metadata/assets/checksums |
| Metadata repair | canonical metadata push or explicit dispatch | Repair mutable Release presentation only | verified name/body repair with immutable state unchanged |

## Runner ownership

A caller passes `runner_json` directly to the reusable workload. New generated callers do not invoke a runner-policy workflow first.

For trusted workloads the default target is `["self-hosted","Linux","X64"]`; `PRODKIT_RUNNER_JSON` may replace that JSON in generated generic callers. CI/Security fork PRs are forced to GitHub-hosted execution.

This intentionally avoids hosted probes, resolver jobs, destructive workspace preflight, and automatic runner switching. A workload gets one execution target and either succeeds or fails.

Branch Cleanup defaults to `ubuntu-latest`. Post-Gate Branch Cleanup also prefers `ubuntu-latest` but may honor `PRODKIT_RUNNER_JSON` for trusted private-repository control-plane execution where hosted jobs are unavailable.

### Single-runner non-blocking rule

The lifecycle must remain correct with only one trusted self-hosted runner. A job occupying that runner must never dispatch another workflow that also needs the runner and then poll, sleep, or otherwise wait for the child to finish. Such a parent owns the only execution slot its child requires and can deadlock the release indefinitely.

Cross-workflow sequencing therefore uses completion boundaries:

1. exact-main CI/Security/optional CodeQL complete independently;
2. Post-Gate Branch Cleanup, when activated, verifies all configured exact-SHA gates, dispatches Branch Cleanup once, and exits without waiting for deletion;
3. the dispatch-only Branch Cleanup workflow acquires a runner and performs guarded deletion;
4. `Trusted Release Proof` completes successfully and releases its runner;
5. the separate `Release Promotion` caller starts from that completed workflow's `workflow_run` event, derives the release version from the exact proof `head_sha`, dispatches Release idempotently, and exits;
6. Release acquires a runner and advances through short sequential release jobs;
7. `workflow_run` starts independent verification only after Release has completed.

The **proof-completion boundary** is also required on hosted or multi-runner environments: publication authorization searches only completed successful proof runs, so dispatching Release from a job inside an in-progress proof workflow is a race and is forbidden.

The **cleanup authorization boundary** follows the same non-blocking principle: the post-gate authorizer never performs deletion itself and never waits for the dispatched Branch Cleanup run.

Long-running controller/orchestrator workflows are not part of the generated default lifecycle.

## Pull request and main

Normal CI and Security use compact reusable workflows. Each renders one stable workload job:

- `ci / CI Required`
- `security / Security Required`

Compatibility and scanning dimensions execute as steps, and the final aggregate verifier fails closed if any enabled control failed. Intermediate steps may use `continue-on-error` to collect later evidence; the aggregate evaluates their recorded `outcome`, not only their visual step presentation.

## Post-gate branch cleanup

`Post-Gate Branch Cleanup` is a permanent dormant `workflow_run` authorization caller. It does nothing while `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` is empty.

When activated with a reviewed exact branch list, the reusable authorizer requires the triggering run to originate from a default-branch `push`, requires the trigger `head_sha` to equal the current default-branch SHA, validates the target cleanup workflow is still `workflow_dispatch` only, and verifies the configured required exact-SHA push workflows by immutable workflow path.

The default required gates are CI and Security. `PRODKIT_GATED_CLEANUP_GATES_JSON` may provide an explicit non-empty list of `{name,path}` objects. The caller listens by default for CI, Security, and CodeQL completion events. Any additional configured gate must also be named in that static trigger list so its completion can become the final authorization event.

Missing or in-progress required gates cause the authorization run to exit successfully as `deferred`. A completed non-success required gate fails closed. Once all configured gates are green, only the last completed required gate event may dispatch, which prevents CI/Security/CodeQL completion fan-out from creating duplicate cleanup requests.

Immediately before dispatch the authorizer rereads the default branch. It then calls the permanent `Branch Cleanup` workflow with the exact reviewed branch list, `dry_run=false`, and the exact certified SHA. The authorizer has `actions: write` but remains `contents: read`; it cannot delete refs.

The downstream Branch Cleanup workflow remains the only mutation boundary. It independently requires `workflow_dispatch`, binds deletion to the supplied exact SHA, performs complete preflight, rejects default/protected/open-PR branches, revalidates every target SHA immediately before deletion, rechecks the default SHA throughout mutation, and verifies every deleted ref is absent.

For human-reviewed maintenance, run Branch Cleanup with `dry_run=true` before enabling the post-gate branch-list variable. Clear `PRODKIT_GATED_CLEANUP_BRANCHES_JSON` after the one-shot cleanup request is closed.

## Release candidate

`Trusted Release Proof` is dispatch-only and certifies `${{ github.sha }}` from the branch/ref on which it is dispatched. Operators do not paste a source SHA into the workflow.

The reusable proof first verifies that the SHA is still current `main` and that the permanent exact-SHA `CI` and `Security` push workflows already succeeded. It **does not rerun those matrices**. The repository-owned `.prodkit/workflows/release-proof.sh` is therefore reserved for genuinely release-specific acceptance that is not already represented by permanent CI/Security evidence.

For canonical new consumers, the reusable proof then executes the repository-owned release-build adapter once, writes the repository-owned artifacts beneath `release-payload/`, records their names/sizes/SHA-256 digests in `release-payload.json`, proves tracked source remained unchanged, and uploads the whole proof artifact. This proof-produced payload is the promotable payload; Release does not rebuild it.

The proof workflow itself does not dispatch Release. Only after the enclosing `Trusted Release Proof` run reaches `completed` with `success` does the separate `Release Promotion` caller run. It passes `${{ github.event.workflow_run.head_sha }}` to `reusable-release-promote.yml`, which rechecks current-main identity, derives one consistent SemVer from `.prodkit/release.json`, avoids a duplicate dispatch only while an exact-source Release run is actively queued/running, otherwise dispatches the repository Release workflow, and exits immediately without waiting.

An existing tag or GitHub Release is not closure evidence by itself. If the tag already resolves to the proven SHA, promotion may re-dispatch the idempotent Release workflow so the publisher can verify or resume the exact release transaction without rebuilding already-complete stages.

Proof does not run on every pull-request commit, ordinary main push, or tag event.

## Publication

`Release` remains dispatch-only, but the normal lifecycle dispatch is owned by the proof-completion `Release Promotion` workflow rather than a second manual operator step. The release target is `${{ github.sha }}` from the dispatch on `main`.

The consumer Release caller is deliberately thin: it passes the exact source and authoritative `Trusted Release Proof` workflow path to `reusable-release.yml`. It does not duplicate GitHub API proof-gate code. The reusable publisher centrally requires a completed successful proof dispatch for the exact SHA and independently rechecks successful `push` runs of `CI` and `Security` for that same SHA. Those are cheap authorization checks, not reruns of the workloads.

Publication is checkpointed at job boundaries:

1. **prepare** — validate current-main identity, permanent CI/Security evidence, exact completed-proof authorization, manifest/version/notes, and any already-published release; capture the exact successful proof run ID;
2. **build/seal** — on the canonical path, download the proof artifact from that exact run, verify `release-payload.json`, import the proof-produced payload, add central source/SBOM evidence, seal everything with `release-metadata.json` and `SHA256SUMS`, and upload one sealed workflow artifact. A compatibility-only mode can still invoke `release-build.sh` when a historical proof does not contain a promotable payload;
3. **attest** — optionally download and attest that sealed payload;
4. **publish** — download the same sealed payload, create or recover the immutable tag/draft Release, upload only missing or mismatched assets, verify the draft, and publish.

The sealed workflow artifact is the retry boundary. When a late job fails, operators should use GitHub **Re-run failed jobs** rather than restarting the whole workflow. GitHub re-runs failed jobs and their dependent jobs while successful earlier jobs remain complete, so a failed attestation or publication does not rerun proof, regenerate the repository payload, or rebuild a successful sealed payload.

Draft recovery is incremental. Correct existing draft assets are retained; only unexpected or checksum-mismatched assets are removed and re-uploaded. A fully published release is verified during preflight and treated as idempotently complete.

GitHub Artifact Attestations are optional because feature availability depends on repository visibility and GitHub organization plan. The reusable publisher defaults `attest` to `false`. A consumer may explicitly set `attest: true` only when the feature is available; once explicitly enabled, attestation failure is release-fatal. Exact-source gates, proof-produced payload digests, SBOM generation, `SHA256SUMS`, sealed-payload verification, and draft read-back remain independent of GitHub Artifact Attestations.

The publisher verifies the draft transaction before making it public. Post-publication verification is intentionally owned by the independent `Release Verification` workflow rather than duplicated inside the publisher.

Tag creation never reruns the proof and a product/release failure never switches runners.

## Independent verification

The generated `Release Verification` caller listens for completion of the repository `Release` workflow and invokes `reusable-release-verification.yml` only for successful workflow-dispatch publication runs.

Verification is read-only. It derives the version, notes path, and expected Release name from the immutable source manifest; recursively resolves annotated/lightweight tags to the exact source SHA; verifies draft/prerelease/target metadata; requires canonical Release notes; requires the remote asset set to match `SHA256SUMS` exactly; and verifies GitHub asset digests or downloads/hashes assets when the API digest is unavailable.

Because verification begins only after Release completes, it cannot hold the runner needed by publication.

## Metadata repair

Release metadata repair is separate from publication. It may reconcile canonical GitHub Release name/body from current repository metadata only after proving the historical tag and payload identity remain unchanged.

It cannot move/create tags, rebuild or replace assets, change checksums, or change publication flags.

## Backward compatibility

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available for older immutable consumers. The compatibility release pipeline delegates proof authorization and publication to the same resumable central publisher instead of maintaining a second proof-gate implementation. Its proof-payload reuse flag defaults off so historical proof adapters remain valid until deliberately migrated.

Quality is a release-presentation reference, not a runner-controller dependency.
