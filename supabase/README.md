# Supabase — Open-Trainer schema

Project ref: `lhquhastwnurmvyrzdeh`

## Migrations

| File | Purpose |
|------|---------|
| `migrations/0001_init.sql` | Tables, indexes, `updated_at` triggers |
| `migrations/0002_rls.sql`  | Row Level Security (default-deny + public exercise library) |
| `migrations/0003_seed_exercises.sql` | Seed the exercise library (idempotent) |

## Applying

### Option A — Supabase CLI (recommended)

```bash
supabase link --project-ref lhquhastwnurmvyrzdeh
supabase db push          # applies everything in migrations/ in order
```

### Option B — psql / SQL editor

Run the three files **in order** in the Supabase SQL editor, or:

```bash
psql "$SUPABASE_DB_URL" -f migrations/0001_init.sql
psql "$SUPABASE_DB_URL" -f migrations/0002_rls.sql
psql "$SUPABASE_DB_URL" -f migrations/0003_seed_exercises.sql
```

### Option C — MCP

If you have a Supabase MCP with write access, apply each file with
`apply_migration` (DDL) in order. The migrations are idempotent
(`create ... if not exists`, `on conflict do nothing`).

> Note: during the build session the MCP available to Claude Code was
> permission-restricted (read/write denied), so the schema was delivered as
> files rather than applied live. Apply with one of the options above.

## Isolation model (important)

Identity is **Telegram-based**, not Supabase Auth. RLS is enabled on every
table with **no permissive policies** for `anon`/`authenticated` (default-deny),
so the publishable/anon key exposes nothing. The bot and web backend use the
**service-role key** (bypasses RLS) and enforce per-user isolation in
application code by always scoping queries to the `user_id` resolved from the
caller's `telegram_id`. `exercise_library` is the one world-readable table.

## Verifying

```sql
select table_name from information_schema.tables where table_schema = 'public';
select count(*) from public.exercise_library;        -- expect ~44
select * from pg_policies where schemaname = 'public';
```

After applying, run the security advisor (`get_advisors type=security`) to
confirm there are no unexpected RLS gaps.
