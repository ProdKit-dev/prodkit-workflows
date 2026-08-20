# ProdKit Workflows

`prodkit-workflows` is the organization-level CI, security, release, and governance control plane for ProdKit repositories.

It replaces copied repository-specific release state machines with immutable, reusable GitHub Actions workflows. Consumer repositories retain only their domain-specific build/test adapters; release policy, source identity, supply-chain proof, publication semantics, and organization drift detection live here.

## Design goals

- **One release policy with separate immutable and mutable operations.** A production release is requested manually with a semantic version and an exact `main` SHA. The guarded release workflow proves that SHA, checks required CI/Security evidence, builds from it, attests it, creates an immutable tag, publishes through a draft-first transaction, and independently verifies published assets. A separate guarded metadata-repair entry point may reconcile only the mutable GitHub Release name/body from canonical repository metadata while proving that the existing tag and every published asset remain unchanged.
- **Repository specialization without policy drift.** Consumers implement narrow `.prodkit/workflows/*.sh` adapters. The central workflows own orchestration, permissions, toolchain installation, isolation, final required gates, and release integrity.
- **Immutable reuse.** Consumer caller workflows are generated with a full 40-character `prodkit-workflows` commit SHA. Floating `main`, `v0`, or branch references are intentionally rejected by the bootstrap/audit tooling.
- **Conditional hosted/self-hosted/both policy.** CI and Security can run on GitHub-hosted Ubuntu, trusted `["self-hosted","Linux","X64"]`, or both complete lanes through `PRODKIT_RUNNER_MODE`, with per-dispatch overrides and a fail-safe hosted default. Fork pull requests are never sent to persistent self-hosted runners.
- **Fail closed.** Missing evidence, version drift, tag movement, path escapes, symlinked release payloads, empty artifact sets, incomplete drafts, published checksum mismatches, or metadata repair that changes immutable release state stop the operation.
- **Workflow syntax is a release gate.** The control-plane repository runs pinned `rhysd/actionlint:1.7.12` in its hygiene contract; malformed or semantically invalid Actions YAML cannot become a trusted central revision.

## Repository surface

There are three distinct workflow-related layers; their file counts intentionally differ.

| Surface | Role | Count |
| --- | --- | ---: |
| `.github/workflows/` | Four top-level workflows plus five reusable `workflow_call` implementations | 9 |
| `templates/consumer/.prodkit/workflows/` | Complete generated consumer adapter catalog | 11 |
| `.prodkit/workflows/` | Only adapters enabled by this control-plane repository itself | 4 |

The four operator-facing workflows are `CI`, `Security`, `Release`, and `Organization Audit`. Their reusable implementations are `reusable-ci.yml`, `reusable-security.yml`, `reusable-release.yml`, `reusable-release-metadata.yml`, and `reusable-org-audit.yml`. Release metadata repair is an internal reusable release operation rather than a fifth product-level workflow.

| Capability | Reusable workflow | Stable organization-facing gate |
| --- | --- | --- |
| CI orchestration | `.github/workflows/reusable-ci.yml` | `ci / CI Required` |
| Security orchestration | `.github/workflows/reusable-security.yml` | `security / Security Required` |
| Guarded release publication | `.github/workflows/reusable-release.yml` | `Guarded release` |
| Guarded release metadata repair | `.github/workflows/reusable-release-metadata.yml` | `Guarded release metadata repair` |
| Organization drift audit | `.github/workflows/reusable-org-audit.yml` | `Organization workflow audit` |

## Consumer setup

After pushing this repository, obtain the commit SHA you want every consumer to trust. Then generate a consumer integration:

```bash
python3 scripts/bootstrap_consumer.py \
  --workflows-repository ProdKit-dev/prodkit-workflows \
  --workflows-sha <40-character-commit-sha> \
  --destination ../prodkit-quality
```

The generated files are deliberately thin:

```text
.github/workflows/
  ci.yml
  security.yml
  release.yml
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
```

That is the complete adapter catalog. A consumer enables only the capabilities it needs. Disabled capabilities do not require their adapter file at runtime; enabled capabilities must point to a real non-symlink file beneath `.prodkit/workflows/`.

## Runner modes

Runner selection is configuration, not copied workflow logic. Set the GitHub Actions variable `PRODKIT_RUNNER_MODE` at organization or repository level:

```text
github-hosted  -> GitHub-hosted only
self-hosted    -> self-hosted only
both           -> both complete CI/Security lanes must pass
unset/unknown  -> GitHub-hosted fail-safe default
```

Manual CI/Security dispatch can choose `policy`, `github-hosted`, `self-hosted`, or `both`. Fork-originated pull requests are always forced to GitHub-hosted execution.

`both` is strict parity/redundancy, not fallback. GitHub Actions has no native ordered `runs-on` fallback. If hosted quota/capacity is unavailable, redispatch the **same exact SHA** with `runner: self-hosted`. Release accepts successful exact-SHA required workflow evidence from either a normal `push` or a trusted `workflow_dispatch`, so the failover path remains releasable.

Release itself remains single-runner (`policy | github-hosted | self-hosted`) to prevent competing publication transactions. Organization Audit is also single-runner. See `docs/RUNNERS.md`, `docs/ADOPTION.md`, and `docs/CONTRACTS.md`.

## Canonical release flow

```text
release preparation PR
        |
        v
candidate CI + Security + domain proof
        |
        v
merge to main
        |
        +--> exact-SHA CI evidence (push or trusted dispatch)
        +--> exact-SHA Security evidence (push or trusted dispatch)
        |
        v
workflow_dispatch(version, target_sha)
        |
        v
verify target_sha == current main
verify version manifest + notes + changelog
verify successful exact-SHA required workflows
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

If only the mutable GitHub Release presentation later needs correction, do **not** move/recreate the tag or rebuild the payload. Invoke the Guarded release metadata repair operation with the historical version and immutable tag source SHA. It reads the canonical title template and `docs/VX.Y.Z.md` from current `main`, proves the tag still resolves to the supplied source SHA, verifies the complete published checksum set, patches only `name` and `body`, and then proves tag, publication flags, asset IDs/names/sizes/digests, and payload checksums are unchanged.

## Organization policy

`rulesets/org-main.json` and `rulesets/org-release-tags.json` are importable organization ruleset templates. The main ruleset expects the stable checks `ci / CI Required` and `security / Security Required`. Caller-level runner-policy gates preserve those contexts whether the repository uses GitHub-hosted, self-hosted, or both.

`PRODKIT_RUNNER_MODE` may be configured once at organization level and overridden by an individual repository when needed. Changing that variable affects subsequent workflow routing without changing the pinned reusable workflow revision.

Run `scripts/audit_org.py` (or the reusable organization audit) to detect repositories that copied release logic locally, float the central workflow ref, omit required wrappers, or point to an obsolete central SHA.

## Versioning

The API of this repository is the workflow-call interface plus the consumer contract schema. Breaking workflow inputs, output semantics, required adapter contracts, runner-mode semantics, or release manifest semantics require a major version. Consumer repositories should always pin an immutable commit SHA even when a semantic tag exists.
