#!/usr/bin/env bash
# Apply the Open-Trainer migrations to Supabase, in order.
#
# Option A (CLI):  scripts/apply_supabase.sh --cli
# Option B (psql): SUPABASE_DB_URL=postgres://... scripts/apply_supabase.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIG="$ROOT/supabase/migrations"

if [[ "${1:-}" == "--cli" ]]; then
  command -v supabase >/dev/null || { echo "supabase CLI not found"; exit 1; }
  supabase link --project-ref lhquhastwnurmvyrzdeh
  supabase db push
  exit 0
fi

: "${SUPABASE_DB_URL:?Set SUPABASE_DB_URL (Project Settings → Database → Connection string) or pass --cli}"
for f in "$MIG"/0001_init.sql "$MIG"/0002_rls.sql "$MIG"/0003_seed_exercises.sql; do
  echo "==> applying $(basename "$f")"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$f"
done
echo "Migrations applied."
