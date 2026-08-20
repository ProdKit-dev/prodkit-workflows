# AGENTS.md

## Scope

This repository is shared CI/CD infrastructure. Optimize for deterministic, auditable, fail-closed behavior over convenience.

## Invariants

- Never replace a third-party action SHA pin with a floating tag or branch.
- Never add a second production release path.
- Never move an existing semantic release tag.
- Keep consumer-specific commands behind `.prodkit/workflows/*.sh` contracts.
- Keep the stable final check names `CI Required` and `Security Required` unless a coordinated organization ruleset migration is included.
- Release artifacts must be built from the exact requested current `main` SHA.
- Do not add long-lived package-registry secrets to the core release workflow.

## Verification

Run `make check`. If Docker is available, also run actionlint as described in `Makefile`.
