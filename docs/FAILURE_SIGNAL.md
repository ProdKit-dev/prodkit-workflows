# Failure Signal Contract

ProdKit workflows are fail-closed, but they must not multiply one defect into unrelated red checks.

## Ownership

- **CI Required** owns repository hygiene, language/runtime compatibility, database, container, and consumer custom CI adapters.
- **Security Required** owns secret scanning, dependency audits, container vulnerability policy, SBOM generation, and consumer custom security adapters.
- **CodeQL (`language`)** owns only CodeQL analysis and SARIF policy for that matrix language.
- **CodeQL Required** owns only the aggregate success of the language-scoped CodeQL matrix.

A repository-global hygiene command must never be invoked from a per-language CodeQL adapter. Otherwise one global failure is repeated once per language and then repeated again by the aggregate gate.

## Signal rules

1. Preserve exhaustive execution where it provides useful evidence; do not fail fast merely to make a PR look quieter.
2. Preserve stable required-check names used by organization rulesets.
3. Localize failures to the authority that can explain them.
4. Aggregate gates summarize; they do not invent additional policy.
5. A consumer CodeQL adapter receives `PRODKIT_CODEQL_SCOPE=language-sarif-v1`, `PRODKIT_CODEQL_LANGUAGE`, and `PRODKIT_CODEQL_OUTPUT_DIR` and inspects only that language's SARIF output.
6. Repository hygiene runs once through CI.
7. Security scanners retain their own evidence artifacts even when their aggregate gate fails.

The goal is not fewer checks at the expense of coverage. The goal is one defect producing the smallest truthful set of red signals.
