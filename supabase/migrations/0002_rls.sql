-- =============================================================================
-- Open-Trainer — 0002_rls.sql
-- Row Level Security.
--
-- Isolation model
--  Open-Trainer identifies users by Telegram ID, not Supabase Auth, so the
--  SPEC's `user_id = auth.uid()` policy does not map cleanly. Instead we use a
--  DEFAULT-DENY posture:
--    * RLS is ENABLED on every table and NO permissive policy is granted to the
--      `anon` / `authenticated` roles for user data. With the publishable
--      (anon) key, clients therefore see nothing.
--    * The bot and web backend connect with the SERVICE-ROLE key, which bypasses
--      RLS. Per-user isolation is enforced in application code, which always
--      scopes queries by the user_id resolved from the caller's telegram_id.
--    * `exercise_library` is non-sensitive reference data and is world-readable.
--
--  If you later adopt Supabase Auth for a web client, add per-row policies such
--  as `using (user_id = auth.uid())` alongside the default-deny baseline.
-- =============================================================================

alter table public.users               enable row level security;
alter table public.profiles            enable row level security;
alter table public.workouts            enable row level security;
alter table public.exercises           enable row level security;
alter table public.sets                enable row level security;
alter table public.reminders           enable row level security;
alter table public.verification_codes  enable row level security;
alter table public.exercise_library    enable row level security;

-- No policies are defined for user-data tables → anon/authenticated are denied
-- all access. The service-role key bypasses RLS for the backend.

-- exercise_library: public read-only reference data.
drop policy if exists exercise_library_read on public.exercise_library;
create policy exercise_library_read
  on public.exercise_library
  for select
  to anon, authenticated
  using (true);
