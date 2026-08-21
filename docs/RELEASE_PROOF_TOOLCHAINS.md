# Release-proof toolchains

`reusable-release-proof.yml` owns deterministic baseline toolchain provisioning for release-candidate proofs.

Consumers may enable pinned Python/uv and Node/pnpm provisioning through workflow-call inputs. pnpm is activated through Corepack rather than a global npm installation so hosted and trusted self-hosted runners behave consistently.

Repository-owned `.prodkit/workflows/release-proof.sh` adapters may install additional compatibility runtimes (for example Python 3.13/3.14) when their product contract requires them, but must not depend on mutable runner-global package-manager state.
