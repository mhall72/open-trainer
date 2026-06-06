# Open-Trainer

An AI-powered personal trainer accessible via Telegram. Users subscribe, choose a trainer personality, and get guided through workouts — all by texting a bot.

Built on **Hermes Agent** (MIT licensed) with **Supabase** for data storage and **Cloud Run** for hosting.

## Architecture Overview

```
User → Website (landing + Stripe checkout) → open-trainer-web (Cloud Run, FastAPI)
                                                  │  issues a 6-char link code
                                                  ▼
User → Telegram → open-trainer-bot (Cloud Run, Hermes + DeepSeek) ──▶ Supabase
                     │  personal-trainer skill                          (profiles,
                     │  → trainer_cli.py (workout engine + data)         workouts,
                     └────────────────────────────────────────────────  history)
```

A single shared bot serves all users (multi-tenant; isolation by `user_id`).
Full details in **[ARCHITECTURE.md](ARCHITECTURE.md)**; go-live steps in
**[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Agent framework | Hermes Agent (pinned overlay) | MIT — built `FROM` upstream, see `agent/hermes.commit` |
| LLM | DeepSeek `v4-flash` | Hermes' bundled `deepseek` provider; env-configurable |
| Hosting | Cloud Run (2 services) | `open-trainer-bot` + `open-trainer-web` |
| Database | Supabase | Default-deny RLS; backend uses service role |
| Messaging | Telegram | One shared bot, multi-tenant |
| Payments | Stripe | Subscription; bot-initiated account link |
| Deployment | Cloud Build → Cloud Run | `scripts/deploy.sh`, `docker/cloudbuild.yaml` |

## Features

1. **Subscription website** — Stripe checkout → Telegram bot access
2. **Onboarding** (in-Telegram) — Goal, equipment, duration, trainer personality
3. **Workout engine** — Guided sessions with rep/weight tracking, history, adaptive recommendations
4. **Reminders** — Scheduled workout notifications
5. **Progress tracking** — Historical view of sessions

## Personas

Three pre-built trainer personalities:
- **Motivational Coach** — high energy, encouraging
- **No-Nonsense Trainer** — direct, efficient
- **Science-Based** — evidence-driven, explains the "why"

## Setup for Development

### Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) (for the fork base)
- Supabase project: `lhquhastwnurmvyrzdeh`
- Stripe account (test mode keys below)

### MCP Configuration (for Claude Code)

```json
{
  "mcpServers": {
    "supabase": {
      "transport": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=lhquhastwnurmvyrzdeh"
    }
  }
}
```

### Stripe Keys

Get your test keys from [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys) and add them to `.env` (see `.env.template`).

### Local .env template

```env
SUPABASE_URL=https://lhquhastwnurmvyrzdeh.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
STRIPE_SECRET_KEY=sk_test_...
TELEGRAM_BOT_TOKEN=...
HERMES_HOME=./hermes_home
```

## Getting Started

```bash
# Run all offline tests (pure stdlib — no network, no deps)
scripts/run_tests.sh

# Try the agent tool directly
cd agent/skills/personal-trainer
python3 scripts/trainer_cli.py persona --key science
python3 scripts/trainer_cli.py parse-onboarding --step goal --text "build muscle"
```

To deploy, follow **[DEPLOYMENT.md](DEPLOYMENT.md)** (Supabase migrations →
Telegram/Stripe/DeepSeek credentials → `scripts/deploy.sh`).

## Project Structure

```
open-trainer/
├── README.md / SPEC.md / CLAUDE.md     # overview, spec, project instructions
├── ARCHITECTURE.md / DEPLOYMENT.md     # how it fits together / how to ship it
├── agent/                              # Hermes fork (the "brain")
│   ├── hermes.commit                   # pinned upstream commit
│   ├── config/                         # SOUL.md, cli-config.yaml, personalities
│   ├── skills/personal-trainer/        # SKILL.md + scripts (engine, data, CLI)
│   └── tests/                          # engine + onboarding unit tests
├── server/                            # FastAPI web/subscription service
│   ├── app.py  linking.py  supabase_client.py
│   └── tests/
├── website/                           # landing + success pages (Stripe)
├── supabase/migrations/               # 0001 schema, 0002 RLS, 0003 seed
├── docker/                            # Dockerfiles, Cloud Run YAML, cloudbuild
├── scripts/                           # build / deploy / migrate / reminders / tests
└── .env.template
```

## What's implemented

- ✅ Forked agent overlay (skill + DeepSeek config) with a deterministic,
  unit-tested workout engine (split rotation, progression, deload)
- ✅ Supabase schema + RLS + exercise-library seed (migration files)
- ✅ Stripe subscription + signup/linking flow (web service + website)
- ✅ Telegram integration via Hermes' gateway + onboarding flow
- ✅ Cloud Run deployment (Dockerfiles, service manifests, Cloud Build)
- ✅ Reminders worker (timezone-aware, tested)

See [ARCHITECTURE.md](ARCHITECTURE.md) for deviations from the original SPEC and why.

## License

MIT (inherited from Hermes Agent)
