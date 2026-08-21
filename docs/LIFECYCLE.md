# ProdKit workflow lifecycle

`prodkit-workflows` is the organization workflow control plane. Consumer repositories own product-specific adapters and release manifests; they do not own runner-routing expressions, matrix aggregation, release publication state machines, or mutable GitHub Release repair logic.

## Lifecycle

| Stage | Trigger | Required purpose | Normal evidence |
| --- | --- | --- | --- |
| Pull request | `pull_request` | Fast correctness and security feedback before merge | `CI`, `Security`, optional `CodeQL` |
| Main branch | `push` to `main` | Certify the actual merge SHA that can become a release source | successful exact-SHA `CI` and `Security`, optional `CodeQL` |
| Release candidate | explicit `workflow_dispatch` | Run release-grade, exact-source acceptance once for the intended current-main SHA | `Trusted Release Proof` |
| Publication | explicit `workflow_dispatch` | Verify prior evidence, build distributables, attest, tag, and publish | immutable tag + GitHub Release + checksums/SBOM/provenance |
| Metadata repair | canonical metadata push or explicit `workflow_dispatch` | Repair mutable GitHub Release presentation only | verified title/body repair with tag/assets/checksums unchanged |

`Trusted Release Proof` does not run on every pull-request commit, ordinary main push, or tag creation. It is an explicit release-candidate gate. The publication pipeline requires a successful `workflow_dispatch` proof for the exact current-main SHA in addition to successful main-branch `CI` and `Security` runs.

Creating the immutable tag does not rerun the proof. Publication consumes evidence that already certifies the same source SHA.

## Runner ownership

Consumer callers invoke `Reusable Runner Policy` and receive one resolved `runner_json` output. The low-level hosted probe, organization variable interpretation, fork safety, hosted/self-hosted labels, and failover logic live only in `prodkit-workflows`.

`PRODKIT_RUNNER_MODE` supports `auto`, `github-hosted`, and `self-hosted`; an unset organization/repository value is treated as `auto` when the caller uses `policy`. Explicit workflow-dispatch overrides remain available for operations.

Fork-originated pull requests are forced to the hosted lane when `fork_safe` is enabled. Trusted release operations set `fork_safe: false` because they are never fork-PR entry points.

## Consumer ownership

A consumer repository should contain only thin workflow callers plus `.prodkit/workflows/*` adapters. Examples include Python/Node/PostgreSQL/browser checks, repository-specific security checks, release-proof acceptance, CodeQL policy, and the release build contract.

Common orchestration remains centralized:

- runner resolution;
- CI matrix execution and required aggregation;
- Security execution and required aggregation;
- CodeQL matrix execution;
- exact-source Release Proof orchestration;
- release-candidate proof gating;
- immutable publication;
- current-release metadata reconciliation;
- optional published Release title normalization.

## Release presentation

ProdKit Quality is a release-presentation reference, not a runner-policy consumer. Its visible pattern is promoted as the organization release UX contract:

- tag: `vX.Y.Z`;
- GitHub Release name: `ProdKit <Repository Name> vX.Y.Z`;
- canonical note begins with `# vX.Y.Z — <milestone>`;
- GitHub Release body is the complete canonical version document.

Consumer manifests express that presentation through `.prodkit/release.json`; the shared publication and metadata workflows enforce it.
