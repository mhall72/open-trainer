# Open-Trainer — Architecture

## Overview

Open-Trainer is an AI personal trainer delivered over Telegram. It is composed of
two stateless Cloud Run services plus Supabase for data, built on a pinned fork
of [Hermes Agent](https://github.com/NousResearch/hermes-agent).

```
                    ┌──────────────────────────────────────────────┐
   Website  ─POST─▶ │  open-trainer-web (FastAPI, Cloud Run)        │
 (landing+success)  │   • create Stripe Checkout session           │
        ▲           │   • /api/checkout-status → issue link code    │
        │           │   • /api/stripe/webhook → subscription sync   │
        │ serves     └───────────────┬──────────────────────────────┘
        └────────────────────────────┤
                                     ▼ (service role)
                          ┌─────────────────────┐
                          │   Supabase (Postgres)│
                          │  users, profiles,    │
                          │  workouts, exercises,│
                          │  sets, reminders,    │
                          │  exercise_library,   │
                          │  verification_codes  │
                          └─────────▲───────────┘
                                     │ (service role)
   Telegram ◀──messages──▶ ┌────────┴───────────────────────────────┐
                           │  open-trainer-bot (Hermes, Cloud Run)   │
                           │   • Hermes gateway (Telegram platform)  │
                           │   • DeepSeek v4-flash (the brain)       │
                           │   • personal-trainer skill →            │
                           │       trainer_cli.py (engine + data)    │
                           └─────────────────────────────────────────┘

   Cloud Scheduler ──▶ send_reminders.py (Cloud Run Job) ──▶ Telegram + Supabase
```

## The fork: Hermes + an overlay

We do **not** vendor Hermes' ~4,700 files. Instead the bot image is built
`FROM` the pinned upstream Hermes image and we overlay only our customizations —
the idiomatic Hermes extension model:

| Open-Trainer piece | Hermes mechanism | Lands at |
|--------------------|------------------|----------|
| `agent/skills/personal-trainer/` | **Skill** (SKILL.md + scripts) | `/opt/hermes/skills/personal-trainer` |
| `agent/config/SOUL.md` | **Identity** slot | `/opt/hermes/SOUL.md` |
| `agent/config/cli-config.yaml` | **Model** config (`deepseek-v4-flash`) | `/opt/hermes/cli-config.yaml` |
| DeepSeek | **Bundled provider plugin** (`plugins/model-providers/deepseek`) | upstream |
| Telegram | **Bundled platform** (`gateway/platforms/telegram.py`) | upstream |

Pinned commit lives in `agent/hermes.commit`.

## The brain vs. the engine

- **DeepSeek v4-flash** handles natural-language conversation, tone, and the
  three personalities. It never invents fitness data.
- **`trainer_cli.py`** is the deterministic tool surface the model calls. The
  fitness logic (split rotation, rep schemes, linear progression, deload, unit
  conversion) lives in `workout_engine.py` and is fully unit-tested with no LLM
  or network involved. This keeps programming decisions correct and reproducible
  regardless of the model.

Data flow for a set: user texts "8 at 135" → model calls
`trainer_cli.py log --exercise-id … --set 1 --reps 8 --weight 135` → CLI converts
135 lbs → 61.23 kg, writes a `sets` row, returns a confirmation the model relays.

## Multi-tenancy & isolation

One shared bot + one shared web service serve **all** users (confirmed decision,
2026-06-06 — supersedes the original "one container per user" idea for v1). The
bot runs as a single Cloud Run instance (min=max=1, concurrency 1) so there is
exactly one Telegram connection.

Identity is the **Telegram user id**. Both services connect to Supabase with the
**service-role key** (bypasses RLS) and scope every query to the `user_id`
resolved from the caller's `telegram_id`. RLS is enabled with a **default-deny**
posture so the publishable/anon key exposes nothing; `exercise_library` is the
only world-readable table. See `supabase/migrations/0002_rls.sql`.

## Subscription & linking

1. Landing page → Stripe Checkout (web service).
2. On success, `checkout-status` marks the customer active and mints a 6-char
   `verification_codes` row (idempotent per customer).
3. User sends the code to the bot (or taps `t.me/<bot>?start=<code>`); the skill
   calls `link`, binding `telegram_id` ↔ Stripe customer and activating access.
4. Stripe webhooks keep `subscription_status` in sync for renewals/cancellations.

Bot-initiated linking is required because a Telegram bot cannot DM a user by
handle until that user messages it first.

## Deviations from the original SPEC (and why)

- **Units:** weights stored canonically in **kg** (`sets.weight_kg`); each user
  has a `unit_preference` (lbs default) and sees their unit. The SPEC's example
  dialogs used lbs while the schema used kg — this reconciles both.
- **RLS:** default-deny + service-role rather than `user_id = auth.uid()`,
  because identity is Telegram-based, not Supabase Auth.
- **Linking table:** added `verification_codes` to bridge Stripe → Telegram.
- **Multi-tenancy:** shared service for v1 (cost/ops), not per-user containers.
