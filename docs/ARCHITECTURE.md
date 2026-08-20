# Architecture

## Control-plane boundary

```text
Consumer repository                         prodkit-workflows
-------------------                         -----------------
thin caller CI ---------------------------> reusable-ci
  .prodkit/workflows/ci-*.sh <-------------- fixed adapter contract

thin caller Security ---------------------> reusable-security
  .prodkit/workflows/security-*.sh <-------- fixed adapter contract

thin caller Release ----------------------> reusable-release
  .prodkit/release.json <------------------- versioned manifest contract
  .prodkit/workflows/release-build.sh <----- deterministic build contract

Organization -----------------------------> reusable-org-audit
  repository wrappers <--------------------- drift/pin policy
```

The central repository owns *policy and orchestration*. Consumer repositories own *domain implementation*. A consumer can add databases, browsers, migration tests, protocol fixtures, or package-specific build logic without inventing a new release state machine.

## Release transaction

The workflow deliberately separates proof from publication. It validates the exact source and permanent evidence before any tag is created. It builds and seals artifacts before tag creation. GitHub Release publication is draft-first; assets are uploaded and downloaded again for digest verification before the draft becomes public.

Cross-registry publication is intentionally outside the core transaction because npm/PyPI/container registries cannot participate in an atomic GitHub transaction. Add trusted-publishing workflows as separate, idempotent stages anchored to the already-published immutable GitHub release.
