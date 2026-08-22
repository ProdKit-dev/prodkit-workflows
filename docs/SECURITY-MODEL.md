# Security Model

## Trust anchors

1. The reviewed immutable commit SHA of `prodkit-workflows`.
2. The exact consumer `main` SHA selected for release.
3. Successful permanent `CI` and `Security` push workflow runs on that SHA.
4. A successful exact-SHA `Trusted Release Proof` identified by workflow-file identity.
5. The version metadata and release notes committed at that SHA.
6. The sealed release payload and SHA-256 digests produced by the successful build job.
7. When explicitly enabled and supported, GitHub Artifact Attestations generated with short-lived OIDC identity.
8. Organization rulesets preventing main/tag history rewriting.

## Threats addressed

- **Workflow drift:** thin caller wrappers and the organization auditor detect copied or obsolete release implementations; proof authorization is central rather than copied into each caller.
- **Tag substitution:** an existing release tag on another SHA is a hard failure; tag update/deletion is additionally blocked by rulesets.
- **Release from unreviewed source:** target SHA must equal current `origin/main` and already have successful push CI/Security plus exact-SHA proof evidence.
- **Artifact substitution:** the build job seals one payload with `SHA256SUMS`; downstream attest/publish jobs download and verify that same workflow artifact before use.
- **Partial publication:** publication stays draft until the exact asset set verifies. Retry recovery preserves matching draft assets and replaces only missing or mismatched assets.
- **Retry drift:** late failures do not rerun a successful build by default. GitHub Re-run failed jobs resumes from successful job boundaries, reducing unnecessary regeneration of already-sealed evidence.
- **Post-publication mutation:** an independent read-only Release Verification workflow checks immutable tag/source/metadata/assets/checksums after publication.
- **Self-hosted cross-run contamination:** service containers use run-specific names and cleanup; checkout credentials are disabled for read-only jobs.

## Residual risks

GitHub, runner hosts, third-party action commits, workflow-artifact storage, container image tags, and upstream package ecosystems remain supply-chain dependencies. GitHub Artifact Attestations are an optional additional trust signal rather than a baseline release requirement because availability depends on repository visibility and organization plan. For higher assurance, enable attestations where supported, override container image inputs with digest-pinned references, isolate release runners, use egress controls, and configure GitHub environments with required reviewers.
