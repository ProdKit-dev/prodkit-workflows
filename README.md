# ProdKit Workflows

`prodkit-workflows` is the organization-level CI, security, release, and governance control plane for ProdKit repositories.

It replaces copied repository-specific workflow state machines with immutable, reusable GitHub Actions workflows. Consumer repositories retain only their domain-specific build/test adapters; orchestration, runner routing, security evidence, release policy, source identity, supply-chain proof, publication semantics, and organization drift detection live here.

## Design goals

- **One release policy with separate immutable and mutable operations.** A production release is requested manually with a semantic version and an exact `main` SHA. The guarded release workflow proves that SHA, checks permanent CI/Security evidence, builds from it, attests it, creates an immutable tag, publishes through a draft-first transaction, and independently verifies published assets. A separate guarded metadata-repair entry point may later reconcile only mutable GitHub Release presentation while proving that the existing tag and every published asset remain unchanged.
- **Repository specialization without policy drift.** Consumers implement narrow `.prodkit/workflows/*.sh` adapters. The central workflows own orchestration, permissions, toolchain installation, isolation, final required gates, and release integrity.
- **Compact default checks.** Generated consumers run all enabled CI dimensions inside one `CI Required` job and all enabled Security dimensions inside one `Security Required` job. Compatibility versions and security stages remain individually visible as steps, but they no longer create a large matrix of independent required jobs.
- **Backward-compatible expanded workflows.** `reusable-ci.yml` and `reusable-security.yml` remain available for already-pinned consumers or repositories that explicitly prefer parallel job fan-out. New bootstrap output uses `reusable-ci-compact.yml` and `reusable-security-compact.yml`.
- **Immutable reuse.** Consumer caller workflows are generated with a full 40-character `prodkit-workflows` commit SHA. Floating `main`, `v0`, or branch references are intentionally rejected by bootstrap/audit tooling.
- **Hosted-first automatic runner failover.** `PRODKIT_RUNNER_MODE=auto` (and an unset policy) performs a minimal GitHub-hosted availability probe before trusted workloads. The probe is deliberately **non-poisoning**: it emits `available=true` only when a hosted runner actually starts, and an absent availability output routes the unchanged reusable workflow to `["self-hosted","Linux","X64"]` without turning the infrastructure probe itself into a failed required gate. Explicit `github-hosted` and `self-hosted` remain strict overrides. Fork pull requests are always hosted-only.
- **Stable branch-protection identities.** Failover happens before invoking the reusable workflow, so caller names `ci` and `security` remain unchanged and organization rulesets continue requiring `ci / CI Required` and `security / Security Required`.
- **Fail closed.** Missing evidence, failed enabled steps, unsupported compact compatibility versions, version drift, tag movement, path escapes, symlinked release payloads, empty artifact sets, incomplete drafts, published checksum mismatches, unsafe fork routing, or metadata repair that changes immutable release state stop the operation.
- **Workflow syntax is a release gate.** The control-plane repository runs pinned `rhysd/actionlint:1.7.12` in its hygiene contract; malformed or semantically invalid Actions YAML cannot become a trusted central revision.

## Repository surface

There are three distinct workflow-related layers; their file counts intentionally differ.

| Surface | Role | Count |
| --- | --- | ---: |
| `.github/workflows/` | Four operator-facing workflows plus twelve reusable `workflow_call` implementations | 16 |
| `templates/consumer/.prodkit/workflows/` | Complete generated consumer adapter catalog | 13 |
| `.prodkit/workflows/` | Only adapters enabled by this control-plane repository itself | 4 |

The four operator-facing control-plane workflows are `CI`, `Security`, `Release`, and `Organization Audit`. Consumer bootstrap additionally generates explicit `Trusted Release Proof` and `Release Metadata` lifecycle callers.

| Capability | Default reusable workflow | Stable required gate |
| --- | --- | --- |
| Compact CI orchestration | `.github/workflows/reusable-ci-compact.yml` | `CI Required` |
| Compact Security orchestration | `.github/workflows/reusable-security-compact.yml` | `Security Required` |
| Expanded CI compatibility path | `.github/workflows/reusable-ci.yml` | `CI Required` |
| Expanded Security compatibility path | `.github/workflows/reusable-security.yml` | `Security Required` |
| Runner policy | `.github/workflows/reusable-runner-policy.yml` | routing only |
| Trusted release proof | `.github/workflows/reusable-release-proof.yml` | proof job |
| Release lifecycle pipeline | `.github/workflows/reusable-release-pipeline.yml` | release pipeline |
| Guarded release publication | `.github/workflows/reusable-release.yml` | `Guarded release` |
| Current/historical metadata selection | `.github/workflows/reusable-release-metadata-current.yml` | metadata orchestration |
| Guarded release metadata repair | `.github/workflows/reusable-release-metadata.yml` | `Guarded release metadata repair` |
| CodeQL orchestration | `.github/workflows/reusable-codeql.yml` | `CodeQL Required` |
| Organization drift audit | `.github/workflows/reusable-org-audit.yml` | `Organization workflow audit` |

## Consumer setup

After pushing this repository, obtain the exact commit SHA every consumer should trust. Then generate a consumer integration:

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <40-character-commit-sha> \
  --destination ../prodkit-annotation
```

The generated lifecycle callers are deliberately thin:

```text
.github/workflows/
  ci.yml
  security.yml
  trusted-release-proof.yml
  release.yml
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

`--include-codeql` additionally generates `.github/workflows/codeql.yml`. A consumer enables only the capabilities it needs. Disabled capabilities do not require their adapter file at runtime; enabled capabilities must point to a real non-symlink file beneath `.prodkit/workflows/`.

Compact CI currently supports the organization compatibility set Python `3.12`, `3.13`, `3.14` and Node `20`, `22`, `24`. The caller may select any non-empty subset. Unsupported or duplicate compact-version entries fail closed rather than silently running a different toolchain. The expanded workflows remain available when a repository needs a compatibility matrix outside that compact support set.

Runner selection is configuration, not copied product logic. Set the GitHub Actions variable `PRODKIT_RUNNER_MODE` to `auto`, `github-hosted`, or `self-hosted` at organization or repository level. Unset behaves as `auto`; unknown values fail safe to strict GitHub-hosted execution. Manual dispatch can choose `policy`, `auto`, `github-hosted`, or `self-hosted`; use `runner: auto` to force hosted-first failover for that dispatch. In `auto`, the caller first runs a repository-code-free hosted availability probe. If that probe actually runs it emits `available=true`; otherwise the trusted workload is routed to self-hosted. See `docs/RUNNERS.md`.

See `docs/ADOPTION.md` and `docs/CONTRACTS.md` for the complete consumer contract.

## Compact versus expanded execution

The two modes enforce the same adapter boundary and the same stable branch-protection names, but optimize different things:

| Property | Compact default | Expanded compatibility path |
| --- | --- | --- |
| GitHub job/check count | Low | Higher |
| Compatibility dimensions | Steps in one required job | Independent matrix jobs |
| Parallelism | Serial within the selected runner | Parallel when runner capacity exists |
| Complete failure collection | Enabled steps continue and final gate aggregates outcomes | Matrix jobs independently report outcomes |
| Branch-protection names | `ci / CI Required`, `security / Security Required` | Same |
| Best fit | Normal ProdKit repositories, especially one-runner/self-hosted capacity | Very large matrices or repositories prioritizing parallel latency |

Compact mode does **not** weaken the contract. Enabled steps use `continue-on-error` only so later checks can still execute; the final required step examines every enabled step outcome and fails the job if any setup, adapter, scan, or required evidence upload failed.

## Canonical release flow

```text
release preparation PR
        |
        v
CI + Security
        |
        v
merge to main
        |
        +--> permanent CI (exact SHA)
        +--> permanent Security (exact SHA)
        |
        v
workflow_dispatch Trusted Release Proof(source_sha)
        |
        v
exact-source domain proof
        |
        v
workflow_dispatch Release(version, target_sha)
        |
        +--> non-poisoning hosted availability probe when runner policy is auto
        |        |
        |        +--> available=true -> hosted release
        |        +--> no availability output -> trusted self-hosted release
        v
verify target_sha == current main
verify version manifest + notes + changelog
verify successful push CI/Security on target_sha
verify successful dispatched Trusted Release Proof on target_sha
        |
        v
build exact source -> SBOM -> checksums -> provenance attestation
        |
        v
create immutable vX.Y.Z tag on target_sha
        |
        v
create/recover draft GitHub Release
upload assets -> download and hash-verify assets
        |
        v
publish release -> verify remote checksum set again
```

Failover is decided before the reusable Release workflow begins, so a packaging, attestation, checksum, tag, draft, upload, or publication failure never causes an automatic second release attempt on another runner.

If only mutable GitHub Release presentation later needs correction, do **not** move/recreate the tag or rebuild the payload. Invoke the guarded metadata-repair operation with the historical version and immutable tag source SHA. It reads the canonical title template and `docs/VX.Y.Z.md` from current `main`, proves the tag still resolves to the supplied source SHA, verifies the complete published checksum set, patches only `name` and `body`, and then proves tag, publication flags, asset IDs/names/sizes/digests, and payload checksums are unchanged.

## Organization policy

`rulesets/org-main.json` and `rulesets/org-release-tags.json` are importable organization ruleset templates. The main ruleset expects the stable reusable-workflow checks `ci / CI Required` and `security / Security Required`. GitHub renders reusable workflow status names as `<caller job name> / <reusable job name>`, so do not rename caller jobs without updating the ruleset.

`PRODKIT_RUNNER_MODE` may be configured once at organization level and overridden by an individual repository when needed. `auto` is the recommended hosted-first resilience mode; `github-hosted` and `self-hosted` are strict operator choices. Changing the variable affects subsequent workflow routing without changing the pinned reusable workflow revision.

Run `scripts/audit_org.py` (or the reusable organization audit) to detect repositories that copy lifecycle logic locally, float central workflow refs, omit any of the five default lifecycle callers, use the wrong central workflow family for a caller, or point to an obsolete central SHA.

## Versioning

The API of this repository is the workflow-call interface plus the consumer contract schema and generated caller behavior. Breaking workflow inputs, output semantics, required adapter contracts, runner-routing guarantees, compact compatibility-set semantics, or release manifest semantics require a major version. Consumer repositories should always pin an immutable commit SHA even when a semantic tag exists.
