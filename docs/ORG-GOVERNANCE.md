# Organization Governance

Use organization rulesets as the enforcement layer and `prodkit-workflows` as the execution layer. Rulesets can target multiple repositories and aggregate with repository rules; repository administrators can make policy stricter but cannot weaken an applicable organization rule.

Recommended controls:

- default branch: pull request required, stale approvals dismissed, last-push approval, required `ci / CI Required` and `security / Security Required`, force-push and deletion blocked;
- release tags: `vMAJOR.MINOR.PATCH` semantic format, deletion blocked, non-fast-forward updates blocked;
- release environment: required reviewer for high-risk repositories, no untrusted deployment branches;
- workflow permissions: default organization `GITHUB_TOKEN` to read-only; reusable Release explicitly requests only publication/provenance permissions;
- drift audit: run after central workflow upgrades and periodically across repositories.

The supplied JSON files are import recipes, not activation commands. They deliberately ship with `"enforcement": "disabled"` so an import cannot immediately lock unmigrated repositories. Their repository condition remains `~ALL` to make the intended eventual organization-wide policy explicit.

Safe activation sequence:

1. import the ruleset while disabled;
2. replace `~ALL` with a selected set of already-migrated repositories;
3. verify the centralized required checks exist and are green on those repositories;
4. review bypass actors and approval policy;
5. activate the ruleset;
6. expand targeting incrementally after each repository migration.

Never activate the branch ruleset against an unmigrated repository that does not yet emit `ci / CI Required` and `security / Security Required`.
