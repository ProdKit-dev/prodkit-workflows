#!/usr/bin/env bash
set -euo pipefail
corepack enable
corepack prepare pnpm@11.21.0 --activate
pnpm install --frozen-lockfile
pnpm check
