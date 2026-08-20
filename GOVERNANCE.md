# Governance

This repository defines organization release policy. Changes to release source identity, evidence requirements, tag semantics, permissions, attestation, or publication are high-risk changes and should receive explicit platform-owner review.

Compatibility is defined by workflow-call inputs, required status names, consumer adapter environment variables, and `contracts/release-manifest.schema.json`.

Emergency changes must remain auditable: use a pull request, preserve exact action pins, document the incident or rationale, and publish a new immutable `prodkit-workflows` commit SHA for consumers. Never move a workflow version tag to silently change consumer behavior.
