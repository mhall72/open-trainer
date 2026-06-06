# Open-Trainer — CLAUDE.md

## Project Overview

AI personal trainer accessible via Telegram. Users subscribe, onboard to set their profile, then text a bot for guided workouts with rep/weight tracking, history, and adaptive recommendations.

## Current State (2026-06-06)

- **Discovery:** Complete (3-phase discovery done with Mike Hall)
- **Status:** Ready for implementation
- **Repo:** https://github.com/mhall72/open-trainer

## Key Decisions (do not change without asking Mike)

1. **Multi-tenancy:** One Hermes Agent Docker container per user (Cloud Run)
2. **Infrastructure:** Claude Code has full authority over Cloud Run, Docker, and deployment decisions
3. **Database:** Supabase (project: `lhquhastwnurmvyrzdeh`) with Row Level Security for user data isolation
4. **UI:** Telegram only (no web app beyond the landing/subscription page)
5. **Payments:** Stripe (test keys in README)
6. **Personalities:** Motivational Coach, No-Nonsense Trainer, Science-Based
7. **Onboarding flow:** In-Telegram after signup — goal, equipment, duration, personality
8. **License:** MIT (forking Hermes Agent is clean for commercial use)

## Architecture

- Cloud Run hosts per-user containerized Hermes Agent instances
- Supabase stores: users, profiles, workout history, preferences
- Telegram is the user-facing interface
- Landing page + Stripe checkout for subscriptions

## Onboarding Flow

1. Website subscribe → Stripe → enter Telegram handle
2. Bot sends verification code → verified on website → linked
3. First message starts flow:
   - Goal (build muscle / lose weight / general fitness / endurance)
   - Location (home / gym / both)
   - Equipment (dumbbells / barbell / machines / bodyweight / etc)
   - Duration (30 / 45 / 60 / flexible)
   - Personality (Motivational / No-Nonsense / Science-Based)
4. Profile saved to Supabase → ready for workouts

## Agent Workflow

User says "let's work out" → agent:
1. Checks workout history in Supabase
2. Recommends today's session based on history + goals
3. Walks through exercises: user reports weight/reps per set
4. Logs everything to Supabase
5. Adjusts subsequent recommendations

## MCP Servers Configured

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

## Project Structure Desired

```
open-trainer/
├── README.md              # Project overview + setup
├── SPEC.md                # Full spec
├── CLAUDE.md              # This file
├── docker/                # Container setup
├── agent/                 # Forked Hermes customizations
├── website/               # Landing page + Stripe
├── supabase/              # Schema + migrations
```

## Contact

Mike Hall — questions about scope, priorities, or anything outside this document → ask him directly.
