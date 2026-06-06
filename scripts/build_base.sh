#!/usr/bin/env bash
# Build the pinned upstream Hermes base image locally.
# Usage: scripts/build_base.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1090
source <(grep -E '^HERMES_(REPO|COMMIT)=' "$ROOT/agent/hermes.commit")

: "${HERMES_REPO:?missing HERMES_REPO in agent/hermes.commit}"
: "${HERMES_COMMIT:?missing HERMES_COMMIT in agent/hermes.commit}"

TAG="open-trainer/hermes-base:${HERMES_COMMIT:0:8}"
echo "Building $TAG from ${HERMES_REPO}#${HERMES_COMMIT} ..."
docker build -t "$TAG" "${HERMES_REPO%.git}.git#${HERMES_COMMIT}"

echo "Done: $TAG"
echo "Now build the bot overlay:"
echo "  docker build -f docker/Dockerfile --build-arg HERMES_IMAGE=$TAG -t open-trainer/bot:latest ."
