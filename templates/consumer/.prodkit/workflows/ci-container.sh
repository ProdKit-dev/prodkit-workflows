#!/usr/bin/env bash
set -euo pipefail
docker build --pull -t "consumer-ci:${GITHUB_SHA}" .
docker run --rm "consumer-ci:${GITHUB_SHA}" --help >/dev/null || true
docker image rm -f "consumer-ci:${GITHUB_SHA}" >/dev/null 2>&1 || true
