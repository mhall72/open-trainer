#!/usr/bin/env bash
# Build + push + deploy both Cloud Run services via Cloud Build.
# Prereqs: gcloud authed, Artifact Registry repo "open-trainer" created, and the
# secrets referenced in docker/cloud-run-*.yaml present in Secret Manager.
# See DEPLOYMENT.md for the one-time setup.
#
# Usage: REGION=us-central1 scripts/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${REGION:-us-central1}"

echo "Submitting Cloud Build (region: $REGION)..."
gcloud builds submit "$ROOT" \
  --config "$ROOT/docker/cloudbuild.yaml" \
  --substitutions "_REGION=${REGION}"

echo "Deployed. Set the Telegram webhook/secret and Stripe webhook per DEPLOYMENT.md."
