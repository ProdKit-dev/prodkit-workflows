# ProdKit workflow lifecycle

`prodkit-workflows` centralizes reusable workload implementation. Consumer repositories retain thin lifecycle callers, choose their runner directly, and own product-specific adapters/release metadata.

## Lifecycle

| Stage | Trigger | Required purpose | Normal evidence |
| --- | --- | --- | --- |
| Pull request | `pull_request` | Correctness/security feedback before merge | `CI`, `Security`, optional `CodeQL` |
| Main branch | `push` to `main` | Certify the actual merge SHA | successful exact-SHA `CI` and `Security` |
| Release candidate | explicit `workflow_dispatch` | Release-grade exact-source acceptance | `Trusted Release Proof` |
| Promotion | successful proof dependency | Dispatch the proven version without waiting for publication | bounded idempotent Release dispatch |
| Publication | promoted `workflow_dispatch` | Validate, build/seal, optionally attest, and publish | immutable tag + Release + checksums/SBOM; optional GitHub provenance |
| Verification | `workflow_run` after Release | Independently verify immutable publication | exact tag/source/metadata/assets/checksums |
| Metadata repair | canonical metadata push or explicit dispatch | Repair mutable Release presentation only | verified name/body repair with immutable state unchanged |

## Runner ownership

A caller passes `runner_json` directly to the reusable workload. New generated callers do not invoke a runner-policy workflow first.

For trusted workloads the default target is `["self-hosted","Linux","X64"]`; `PRODKIT_RUNNER_JSON` may replace that JSON in generated generic callers. CI/Security fork PRs are forced to GitHub-hosted execution.

This intentionally avoids hosted probes, resolver jobs, destructive workspace preflight, and automatic runner switching. A workload gets one execution target and either succeeds or fails.

### Single-runner non-blocking rule

The lifecycle must remain correct with only one trusted self-hosted runner. A job occupying that runner must never dispatch another workflow that also needs the runner and then poll, sleep, or otherwise wait for the child to finish. Such a parent owns the only execution slot its child requires and can deadlock the release indefinitely.

Cross-workflow sequencing therefore uses completion boundaries:

1. proof completes and releases the runner;
2. a bounded promotion job derives the release version from the exact source, dispatches Release idempotently, and exits;
3. Release acquires the free runner and advances through short sequential release jobs;
4. `workflow_run` starts independent verification only after Release has completed.

Long-running controller/orchestrator workflows are not part of the generated default lifecycle.

## Pull request and main

Normal CI and Security use compact reusable workflows. Each renders one stable workload job:

- `ci / CI Required`
- `security / Security Required`

Compatibility and scanning dimensions execute as steps, and the final aggregate verifier fails closed if any enabled control failed.

## Release candidate

`Trusted Release Proof` is dispatch-only and certifies `${{ github.sha }}` from the branch/ref on which it is dispatched. Operators do not paste a source SHA into the workflow.

The reusable proof checks that this SHA is still current `main`, executes the repository-owned `.prodkit/workflows/release-proof.sh`, proves the tracked source remained unchanged, and uploads proof evidence.

After proof succeeds, the generated caller invokes `reusable-release-promote.yml`. Promotion rechecks current-main identity, derives one consistent SemVer from `.prodkit/release.json`, avoids a duplicate dispatch only while an exact-source Release run is actively queued/running, otherwise dispatches the repository Release workflow, and exits immediately without waiting.

An existing tag or GitHub Release is not closure evidence by itself. If the tag already resolves to the proven SHA, promotion may re-dispatch the idempotent Release workflow so the publisher can verify or resume the exact release transaction without rebuilding already-complete stages.

Proof does not run on every pull-request commit, ordinary main push, or tag event.

## Publication

`Release` remains dispatch-only, but the normal lifecycle dispatch is owned by proof promotion rather than a second manual operator step. The release target is `${{ github.sha }}` from the dispatch on `main`.

The consumer Release caller is deliberately thin: it passes the exact source, toolchain settings, and the authoritative `Trusted Release Proof` workflow path to `reusable-release.yml`. It does not duplicate GitHub API proof-gate code. The reusable publisher centrally requires a successful proof dispatch for the exact SHA and successful `push` runs of `CI` and `Security` for that same SHA.

Publication is checkpointed at job boundaries:

1. **prepare** — validate current-main identity, permanent CI/Security evidence, proof authorization, manifest/version/notes, and any already-published release;
2. **build** — execute the repository release-build adapter, add source/SBOM evidence, seal the payload with `release-metadata.json` and `SHA256SUMS`, and upload the sealed payload as a workflow artifact;
3. **attest** — optionally download and attest that sealed payload;
4. **publish** — download the same sealed payload, create or recover the immutable tag/draft Release, upload only missing or mismatched assets, verify the draft, and publish.

The sealed workflow artifact is the retry boundary. When a late job fails, operators should use GitHub **Re-run failed jobs** rather than restarting the whole workflow. GitHub re-runs failed jobs and their dependent jobs while successful earlier jobs remain complete, so a failed attestation or publication does not rebuild a successful sealed payload.

Draft recovery is incremental. Correct existing draft assets are retained; only unexpected or checksum-mismatched assets are removed and re-uploaded. A fully published release is verified during preflight and treated as idempotently complete.

GitHub Artifact Attestations are optional because feature availability depends on repository visibility and GitHub organization plan. The reusable publisher defaults `attest` to `false`. A consumer may explicitly set `attest: true` only when the feature is available; once explicitly enabled, attestation failure is release-fatal. Exact-source gates, SBOM generation, `SHA256SUMS`, sealed-payload verification, and draft read-back remain independent of GitHub Artifact Attestations.

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

`reusable-runner-policy.yml` and `reusable-release-pipeline.yml` remain available for older immutable consumers. The compatibility release pipeline now delegates proof authorization and publication to the same resumable central publisher instead of maintaining a second proof-gate implementation.

Quality is a release-presentation reference, not a runner-controller dependency.
