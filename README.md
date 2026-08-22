# ProdKit Workflows

`prodkit-workflows` is the organization-level library of reusable CI, Security, release, CodeQL, metadata, and governance workloads for ProdKit repositories.

The reliability boundary is intentionally simple: **the consumer caller chooses a runner; `prodkit-workflows` executes the workload.** Runner selection is not a separate workflow state machine.

## Design principles

- **Direct execution.** CI, Security, proof, release, metadata, CodeQL, and audit callers pass `runner_json` directly to the reusable workload they invoke. There is no default probe/resolver/preflight controller hop.
- **Thin consumers.** Generated callers define triggers and inputs; reusable workflows own API authorization, evidence checks, build/publish mechanics, and retry semantics. Release callers do not copy a local proof-gate implementation.
- **No expensive gate duplication.** Permanent exact-SHA CI/Security are verified as evidence by Trusted Release Proof; they are not rerun inside proof. The repository release payload is built once during proof and promoted unchanged into publication.
- **One workload job for normal CI and Security.** Compact CI exposes `ci / CI Required`; compact Security exposes `security / Security Required`. Compatibility/scanning dimensions remain visible as steps.
- **Immutable reuse.** Cross-repository callers pin a full 40-character `prodkit-workflows` commit SHA. Floating branches/tags are not production contracts.
- **Fork safety.** Generated CI/Security callers force fork-originated pull requests to `ubuntu-latest`. Persistent trusted runners never execute untrusted fork code by default.
- **Configurable runner target.** Generated callers read optional `PRODKIT_RUNNER_JSON`. When unset, trusted work defaults to `["self-hosted","Linux","X64"]`. This variable is the complete JSON value passed to `runs-on`; it is not a routing mode.
- **Exact-main releases.** `Trusted Release Proof` certifies the workflow-dispatched `${{ github.sha }}`. `Release` publishes the workflow-dispatched `${{ github.sha }}`. Operators no longer copy SHA values between workflows.
- **Resumable publication.** The proof-produced repository payload and later sealed publication payload are workflow-artifact checkpoints. Late failures resume from successful job boundaries.
- **Fail closed.** Missing evidence, invalid manifests, failed enabled controls, tag movement, path escapes, unsafe payloads, checksum mismatches, or metadata repair that changes immutable state stop the operation.

## Reusable workload surface

| Capability | Default reusable workflow | Stable result |
| --- | --- | --- |
| Compact CI | `.github/workflows/reusable-ci-compact.yml` | `CI Required` |
| Compact Security | `.github/workflows/reusable-security-compact.yml` | `Security Required` |
| Expanded CI | `.github/workflows/reusable-ci.yml` | `CI Required` |
| Expanded Security | `.github/workflows/reusable-security.yml` | `Security Required` |
| Trusted release proof | `.github/workflows/reusable-release-proof.yml` | exact-source proof + promotable repository payload |
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
  trusted-release-proof.yml
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

Compact execution keeps dimensions as steps in one required workload job. Enabled steps may use `continue-on-error` so later evidence can still be collected, but the final aggregate verifier fails the job if any required setup/control failed.

Expanded `reusable-ci.yml` and `reusable-security.yml` remain available when a repository deliberately needs parallel matrix jobs.

## Canonical lifecycle

```text
pull request
  -> CI + Security

merge to main
  -> exact-main CI + Security

workflow_dispatch Trusted Release Proof
  -> certifies github.sha (current main)
  -> verifies exact-SHA CI + Security evidence; does not rerun them
  -> runs release-specific acceptance only
  -> runs release-build once
  -> uploads proof-produced payload + digest receipt
  -> promotion dispatches Release and exits

workflow_dispatch Release(version)
  -> github.sha is target source
  -> central prepare: reauthorize exact-SHA CI + Security + exact proof run
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
```

GitHub Artifact Attestations are an optional additional provenance layer. They default off because feature availability depends on repository visibility and organization plan. Explicitly enabling attestations keeps failure release-fatal; the baseline release still requires exact-source proof, proof-produced payload digests, SBOM, `SHA256SUMS`, sealed-payload verification, and independent published-asset verification.

A release caller does not accept a manually copied `target_sha` and does not implement its own proof API query. A proof caller does not accept a manually copied `source_sha`. Dispatch from the intended `main` revision.

### Retry behavior

Do not restart a release from scratch after a late-stage failure. Use GitHub **Re-run failed jobs** on the same Release workflow run. GitHub re-runs failed jobs and their dependent jobs while successful earlier jobs remain complete. A publication failure therefore reuses the successful sealed artifact; it does not rerun proof or `release-build.sh`.

The publisher also resumes partial draft publication: already-correct assets are retained, and only missing or checksum-mismatched assets are uploaded again. If publication already completed, preflight verifies it and exits idempotently.

Mutable Release presentation repair is separate from publication. It may update canonical name/body only after proving the immutable tag and complete published payload remain unchanged.

## Organization policy

Organization rulesets should require:

- `ci / CI Required`
- `security / Security Required`

Run `scripts/audit_org.py` or the Organization Audit workflow to find missing lifecycle callers, floating central refs, obsolete central SHAs, retired runner-controller usage, duplicated consumer proof gates, or local publication implementations.

See `docs/CONTRACTS.md`, `docs/RUNNERS.md`, `docs/LIFECYCLE.md`, and `docs/ADOPTION.md` for the normative integration contract.
