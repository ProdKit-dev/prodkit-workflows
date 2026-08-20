# Runner Requirements

Default runner labels are `self-hosted`, `linux`, `x64`. Consumers can pass another JSON array, including `["ubuntu-24.04"]`.

Self-hosted runners used for CI/Security/Release should provide Git, Bash, Python 3, Docker Engine/CLI, and outbound HTTPS to GitHub plus required package registries. Release runners should be isolated from untrusted workloads. Keep self-hosted GitHub Actions Runner at **v2.327.1 or newer**; current `actions/attest` Node 24 releases require at least that runner generation.

Avoid permanent host ports for test databases. The reusable PostgreSQL job binds a random localhost port and cleans its run-scoped container.
