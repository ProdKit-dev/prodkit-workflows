# Organization Governance

Use organization rulesets as the enforcement layer and `prodkit-workflows` as the execution layer. Rulesets can target multiple repositories and aggregate with repository rules; repository administrators can make policy stricter but cannot weaken an applicable organization rule.

Recommended controls:

- default branch: pull request required, stale approvals dismissed, last-push approval, required `ci / CI Required` and `security / Security Required`, force-push and deletion blocked;
- release tags: `vMAJOR.MINOR.PATCH` semantic format, deletion blocked, non-fast-forward updates blocked;
- release environment: required reviewer for high-risk repositories, no untrusted deployment branches;
- workflow permissions: default organization `GITHUB_TOKEN` to read-only; reusable Release explicitly requests only publication/provenance permissions;
- drift audit: run after central workflow upgrades and periodically across repositories.

The supplied JSON files are templates. Review bypass actors and repository targeting before activating them.
