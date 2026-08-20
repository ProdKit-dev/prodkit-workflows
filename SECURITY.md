# Security Policy

`prodkit-workflows` is security-sensitive infrastructure: changing it can change the execution policy of every consuming repository.

## Reporting

Report suspected workflow, supply-chain, credential, provenance, or release-integrity vulnerabilities privately through the repository's GitHub Security Advisory interface. Do not include secrets in issues, pull requests, or workflow logs.

## Security invariants

- Third-party GitHub Actions are pinned to full commit SHAs in production workflow implementations.
- Consumer repositories must pin reusable workflows to a full commit SHA.
- Release publication accepts only the current `main` SHA and requires successful exact-SHA permanent workflows.
- Release tags are immutable; a pre-existing tag on another commit is a hard failure.
- Release artifacts are regular files in a flat release directory; symlinks and path escapes are rejected.
- Public release publication is draft-first and follows remote asset checksum verification.
- OIDC is used only for provenance and future trusted-publishing extensions; long-lived publication credentials are not part of the core release contract.
- Reusable workflows declare least-privilege permissions. Callers must not grant less than required, and should not grant more than necessary.

See `docs/SECURITY-MODEL.md`.
