# Open-Trainer

An AI-powered personal trainer accessible via Telegram. Users subscribe, choose a trainer personality, and get guided through workouts — all by texting a bot.

Built on **Hermes Agent** (MIT licensed) with **Supabase** for data storage and **Cloud Run** for hosting.

## Architecture Overview

```
User → Website (subscription/signup) → Stripe → Supabase Auth
                                                         |
User → Telegram → [Cloud Run] → Per-user Hermes Agent instance
                                                         |
                                              Supabase DB (profiles, workouts, history)
```

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Agent framework | Hermes Agent (fork) | MIT license — commercial use allowed |
| Hosting | Cloud Run | Infra decisions delegated to Claude Code |
| Database | Supabase | Free tier, RLS for user data isolation |
| Messaging | Telegram | Primary user interface |
| Payments | Stripe | Subscription-based access |
| Deployment | Cloud Run + Supabase | Claude Code handles infra setup |

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

## Project Structure

```
open-trainer/
├── README.md              # This file
├── SPEC.md                # Full spec — outcomes, data model, flows
├── CLAUDE.md              # Instructions for Claude Code
├── docker/                # Container setup for Cloud Run
├── agent/                 # Forked Hermes Agent customizations
├── website/               # Landing page + Stripe integration
├── supabase/              # Schema migrations
└── .env.template          # Environment variable template
```

## License

MIT (inherited from Hermes Agent)
