# Trusted self-hosted workspace preflight

The reusable runner policy owns workspace preparation for the trusted self-hosted lane.

When runner resolution selects `self-hosted`, the resolver clears the caller repository workspace before downstream reusable jobs invoke `actions/checkout`. This prevents a stale, partially deleted, or otherwise non-repository worktree from causing checkout to fail while removing prior local authentication configuration.

The preflight is intentionally fail-closed:

- it runs only when the resolved lane is `self-hosted`;
- it refuses workspace paths outside the expected GitHub Actions `_work/<repository>/<repository>` shape;
- it removes only entries inside `GITHUB_WORKSPACE`, never the workspace directory or its parent;
- it verifies the workspace is empty before publishing runner resolution to downstream jobs.

Repository-specific adapters remain responsible for avoiding privileged build artifacts in bind-mounted workspaces. In particular, Docker-backed Python acceptance should set `PYTHONDONTWRITEBYTECODE=1` or otherwise avoid producing root-owned bytecode in the host worktree.
