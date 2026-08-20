# ProdKit Workflows

`prodkit-workflows` is the organization-level CI, security, release, and governance control plane for ProdKit repositories.

It replaces copied repository-specific release state machines with immutable, reusable GitHub Actions workflows. Consumer repositories retain only their domain-specific build/test adapters; release policy, source identity, supply-chain proof, publication semantics, and organization drift detection live here.

## Design goals

- **One release state machine.** A production release is requested manually with a semantic version and an exact `main` SHA. The release workflow proves that SHA, checks permanent CI/Security evidence, builds from it, attests it, creates an immutable tag, publishes through a draft-first transaction, and independently verifies published assets.
- **Repository specialization without policy drift.** Consumers implement narrow `.prodkit/workflows/*.sh` adapters. The central workflows own orchestration, permissions, toolchain installation, isolation, final required gates, and release integrity.
- **Immutable reuse.** Consumer caller workflows are generated with a full 40-character `prodkit-workflows` commit SHA. Floating `main`, `v0`, or branch references are intentionally rejected by the bootstrap/audit tooling.
- **Self-hosted-safe.** PostgreSQL uses a run-scoped container and random localhost port. Security jobs clean release-owned Docker state. Workflows accept a JSON runner label array and default to `self-hosted, linux, x64`.
- **Fail closed.** Missing evidence, version drift, tag movement, path escapes, symlinked release payloads, empty artifact sets, incomplete drafts, or published checksum mismatches stop publication.
- **Workflow syntax is a release gate.** The control-plane repository runs pinned `rhysd/actionlint:1.7.12` in its hygiene contract; malformed or semantically invalid Actions YAML cannot become a trusted central revision.

## Repository surface

| Capability | Reusable workflow | Stable required gate |
| --- | --- | --- |
| CI orchestration | `.github/workflows/reusable-ci.yml` | `CI Required` |
| Security orchestration | `.github/workflows/reusable-security.yml` | `Security Required` |
| Guarded release | `.github/workflows/reusable-release.yml` | `Guarded release` |
| Organization drift audit | `.github/workflows/reusable-org-audit.yml` | `Organization workflow audit` |

## Consumer setup

After pushing this repository, obtain the commit SHA you want every consumer to trust. Then generate a consumer integration:

```bash
python3 scripts/bootstrap_consumer.py   --workflows-repository ProdKit-dev/prodkit-workflows   --workflows-sha <40-character-commit-sha>   --destination ../prodkit-quality
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

Enable only the capabilities a repository actually needs. See `docs/ADOPTION.md` and `docs/CONTRACTS.md`.

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
        +--> permanent CI (exact SHA)
        +--> permanent Security (exact SHA)
        |
        v
workflow_dispatch(version, target_sha)
        |
        v
verify target_sha == current main
verify version manifest + notes + changelog
verify successful push CI/Security on target_sha
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

## Organization policy

`rulesets/org-main.json` and `rulesets/org-release-tags.json` are importable organization ruleset templates. The main ruleset expects the stable reusable-workflow checks `ci / CI Required` and `security / Security Required`. GitHub renders reusable workflow status names as `<caller job name> / <reusable job name>`, so do not rename the caller jobs without updating the ruleset.

Run `scripts/audit_org.py` (or the reusable organization audit) to detect repositories that copied release logic locally, float the central workflow ref, omit required wrappers, or point to an obsolete central SHA.

## Versioning

The API of this repository is the workflow-call interface plus the consumer contract schema. Breaking workflow inputs, output semantics, required adapter contracts, or release manifest semantics require a major version. Consumer repositories should always pin an immutable commit SHA even when a semantic tag exists.
