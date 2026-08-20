# Contributing

Changes to reusable workflow behavior are treated as platform changes.

1. Change one contract intentionally and document the compatibility impact.
2. Run `python3 scripts/check_repository.py` and `python3 scripts/test_contracts.py`.
3. Validate GitHub workflow syntax with `actionlint`.
4. Preserve full-SHA pins for third-party actions.
5. Update `CHANGELOG.md` and, for a release, `docs/V<version>.md`.
6. Do not introduce repository-specific package names or product-domain assumptions into reusable workflows.

Consumer-specific behavior belongs in `.prodkit/workflows/*.sh` adapters in the consumer repository.
