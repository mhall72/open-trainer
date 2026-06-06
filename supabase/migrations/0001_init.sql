-- =============================================================================
-- Open-Trainer — 0001_init.sql
-- Core schema: users, profiles, workouts, exercises, sets, reminders,
-- exercise_library (reference data) and verification_codes (Stripe→Telegram link).
--
-- Design notes
--  * Weights are stored canonically in kilograms (weight_kg). The user's display
--    unit (kg/lbs) lives on profiles.unit_preference; conversion happens in the app.
--  * Identity is Telegram-based, not Supabase Auth — see 0002_rls.sql for the
--    isolation model (default-deny RLS; backend uses the service-role key).
-- =============================================================================

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- updated_at helper
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- users — one row per paying subscriber, linked to a Telegram account
-- ---------------------------------------------------------------------------
create table if not exists public.users (
  id                     uuid primary key default gen_random_uuid(),
  telegram_id            bigint unique,                       -- set once linked
  telegram_username      text,
  email                  text,
  stripe_customer_id     text unique,
  stripe_subscription_id text,
  subscription_status    text not null default 'inactive'
                           check (subscription_status in
                             ('active','inactive','trial','past_due','canceled')),
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create index if not exists users_telegram_id_idx on public.users (telegram_id);
create index if not exists users_stripe_customer_idx on public.users (stripe_customer_id);

create trigger users_set_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- profiles — fitness profile captured during onboarding (1:1 with users)
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null unique references public.users(id) on delete cascade,
  goal                text check (goal in ('build_muscle','lose_weight','general','endurance')),
  location            text check (location in ('home','gym','both')),
  equipment           text[] not null default '{}',
  session_duration    int default 45,                         -- minutes; 0 = flexible
  personality         text default 'motivational'
                        check (personality in ('motivational','nononsense','science')),
  unit_preference     text not null default 'lbs'
                        check (unit_preference in ('kg','lbs')),
  onboarding_complete boolean not null default false,
  onboarding_step     text,                                   -- null when complete
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create index if not exists profiles_user_id_idx on public.profiles (user_id);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- workouts — one session
-- ---------------------------------------------------------------------------
create table if not exists public.workouts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users(id) on delete cascade,
  date         date not null default current_date,
  name         text not null,
  focus        text,                                          -- push|pull|legs|upper|lower|full
  status       text not null default 'in_progress'
                 check (status in ('in_progress','completed','abandoned')),
  notes        text,
  started_at   timestamptz not null default now(),
  completed_at timestamptz,
  created_at   timestamptz not null default now()
);

create index if not exists workouts_user_id_idx on public.workouts (user_id);
create index if not exists workouts_user_date_idx on public.workouts (user_id, date desc);
create index if not exists workouts_status_idx on public.workouts (status);

-- ---------------------------------------------------------------------------
-- exercises — exercises within a workout
-- ---------------------------------------------------------------------------
create table if not exists public.exercises (
  id                  uuid primary key default gen_random_uuid(),
  workout_id          uuid not null references public.workouts(id) on delete cascade,
  name                text not null,
  exercise_type       text check (exercise_type in ('strength','cardio','bodyweight')),
  target_muscle_group text,
  target_sets         int,                                    -- planned
  target_reps         int,                                    -- planned
  notes               text,
  sort_order          int not null default 0,
  created_at          timestamptz not null default now()
);

create index if not exists exercises_workout_id_idx on public.exercises (workout_id);
create index if not exists exercises_name_idx on public.exercises (name);

-- ---------------------------------------------------------------------------
-- sets — completed sets per exercise
-- ---------------------------------------------------------------------------
create table if not exists public.sets (
  id           uuid primary key default gen_random_uuid(),
  exercise_id  uuid not null references public.exercises(id) on delete cascade,
  set_number   int not null,
  reps         int,
  weight_kg    numeric(6,2),
  rpe          numeric(3,1) check (rpe is null or (rpe >= 0 and rpe <= 10)),
  completed    boolean not null default true,
  completed_at timestamptz not null default now()
);

create index if not exists sets_exercise_id_idx on public.sets (exercise_id);

-- ---------------------------------------------------------------------------
-- reminders — scheduled workout nudges (sent by a cron worker)
-- ---------------------------------------------------------------------------
create table if not exists public.reminders (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users(id) on delete cascade,
  days         text[] not null default '{}',                 -- mon..sun
  time         time not null,
  timezone     text not null default 'UTC',
  enabled      boolean not null default true,
  last_sent_at timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists reminders_user_id_idx on public.reminders (user_id);
create index if not exists reminders_enabled_idx on public.reminders (enabled);

create trigger reminders_set_updated_at
  before update on public.reminders
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- exercise_library — reference catalogue used by the workout engine to build
-- sessions from a user's available equipment. Not user-specific.
-- ---------------------------------------------------------------------------
create table if not exists public.exercise_library (
  id                uuid primary key default gen_random_uuid(),
  name              text not null unique,
  exercise_type     text not null check (exercise_type in ('strength','cardio','bodyweight')),
  primary_muscle    text not null,                            -- chest|back|legs|shoulders|arms|core|full
  secondary_muscles text[] not null default '{}',
  equipment         text[] not null default '{}',             -- any-of: barbell|dumbbells|machines|cables|bodyweight|kettlebell|bands
  movement_pattern  text not null,                            -- squat|hinge|push_h|push_v|pull_h|pull_v|lunge|carry|core|cardio
  split             text not null,                            -- push|pull|legs|core|cardio
  is_compound       boolean not null default false,
  default_sets      int not null default 3,
  default_reps      int not null default 10,
  instructions      text
);

create index if not exists exercise_library_split_idx on public.exercise_library (split);
create index if not exists exercise_library_pattern_idx on public.exercise_library (movement_pattern);

-- ---------------------------------------------------------------------------
-- verification_codes — bridges a completed Stripe checkout to a Telegram user.
-- Created by the Stripe webhook; consumed when the user sends the code to the
-- bot (bots cannot DM a user by handle, so the user initiates the link).
-- ---------------------------------------------------------------------------
create table if not exists public.verification_codes (
  id                     uuid primary key default gen_random_uuid(),
  code                   text not null unique,
  stripe_customer_id     text,
  stripe_subscription_id text,
  email                  text,
  telegram_username      text,
  consumed               boolean not null default false,
  expires_at             timestamptz not null default (now() + interval '24 hours'),
  created_at             timestamptz not null default now()
);

create index if not exists verification_codes_code_idx on public.verification_codes (code);
