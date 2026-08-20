# Adoption Guide

## 1. Publish the control plane

Create `ProdKit-dev/prodkit-workflows`, push this repository, protect `main`, and run CI/Security once. Create a protected `release` environment for the release workflow.

## 2. Pin the workflow implementation

Choose the exact commit SHA of the reviewed `prodkit-workflows` revision. Do not use `@main`, `@v0`, or another movable reference.

## 3. Generate a consumer integration

```bash
python3 scripts/bootstrap_consumer.py   --workflows-repository ProdKit-dev/prodkit-workflows   --workflows-sha <sha>   --destination ../consumer
```

Edit the generated adapters and disable unused capabilities in caller workflows. If a repository does not have both `package.json` and `pyproject.toml`, remove the irrelevant version source from `.prodkit/release.json`.

## 4. Stabilize required status names

The supplied caller jobs are named `ci` and `security`. GitHub therefore exposes the final reusable checks as `ci / CI Required` and `security / Security Required`. Run both workflows once before configuring them as required checks.

## 5. Apply organization rulesets

Import `rulesets/org-main.json` and `rulesets/org-release-tags.json` at the organization level, review repository targeting, bypass actors, approval count, and status-check sources, then enable them. The templates target all organization repositories; narrow them if not every repository follows this control plane.

## 6. Migrate releases

Replace old release implementations only after the new CI/Security push runs are permanent on `main`. Preserve historical tags/releases. Do not rewrite old release commits. New releases use exactly one path: `workflow_dispatch(version, target_sha)`.

## 7. Audit drift

Configure a fine-grained PAT or GitHub App token with read access to the organization repositories as `ORG_AUDIT_TOKEN` in the control-plane repository, then run `Organization Audit`. The auditor fails on floating pins, missing wrappers, local release implementation patterns, or obsolete central SHAs.
