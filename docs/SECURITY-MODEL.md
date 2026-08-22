# Security Model

## Trust anchors

1. The reviewed immutable commit SHA of `prodkit-workflows`.
2. The exact consumer `main` SHA selected for release.
3. Successful permanent `CI` and `Security` push workflow runs on that SHA.
4. The version metadata and release notes committed at that SHA.
5. SHA-256 artifact digests generated after the deterministic build.
6. When explicitly enabled and supported, GitHub Artifact Attestations generated with short-lived OIDC identity.
7. Organization rulesets preventing main/tag history rewriting.

## Threats addressed

- **Workflow drift:** thin caller wrappers and the organization auditor detect copied or obsolete release implementations.
- **Tag substitution:** an existing release tag on another SHA is a hard failure; tag update/deletion is additionally blocked by rulesets.
- **Release from unreviewed source:** target SHA must equal current `origin/main` and already have successful push CI/Security evidence.
- **Artifact substitution:** artifacts are checksummed, optionally attested when supported and explicitly enabled, uploaded to a draft release, downloaded again, and verified before publication.
- **Partial public release:** publication stays draft until the exact asset set verifies.
- **Self-hosted cross-run contamination:** service containers use run-specific names and cleanup; checkout credentials are disabled for read-only jobs.

## Residual risks

GitHub, runner hosts, third-party action commits, container image tags, and upstream package ecosystems remain supply-chain dependencies. GitHub Artifact Attestations are an optional additional trust signal rather than a baseline release requirement because availability depends on repository visibility and organization plan. For higher assurance, enable attestations where supported, override container image inputs with digest-pinned references, isolate release runners, use egress controls, and configure GitHub environments with required reviewers.
