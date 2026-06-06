# Open-Trainer Agent — Hermes customization layer

This directory is the **fork** of [Hermes Agent](https://github.com/NousResearch/hermes-agent):
the workout-coaching brain that runs on top of upstream Hermes.

## Why an overlay instead of a vendored copy

Hermes is ~4,700 files and ships its own Telegram gateway, conversation loop,
provider plugins, and skill system. Vendoring all of it would be unmaintainable
and would make upstream updates painful. Instead we layer Open-Trainer's
customizations onto a **pinned** upstream checkout (see `hermes.commit`). This is
exactly how Hermes is designed to be extended — via **skills**, **provider
plugins**, and the **identity (SOUL.md)** slot.

```
Hermes (pinned upstream)                Open-Trainer overlay (this dir)
├── gateway/  (Telegram, etc.)   +      ├── skills/personal-trainer/  → $HERMES_HOME/skills/
├── plugins/model-providers/     │      │     SKILL.md + scripts/      (the workout engine + tools)
│     deepseek/  (built-in)      │      ├── config/SOUL.md            → $HERMES_HOME/SOUL.md (identity)
├── agent/, providers/, ...      │      ├── config/cli-config.yaml    → Hermes root (model = deepseek-v4-flash)
└── run via `hermes` CLI         │      └── config/personalities.json (3 trainer personas)
```

The Docker build (`../docker/Dockerfile`) clones Hermes at the pinned commit and
copies this overlay into place.

## Components

| Path | Role |
|------|------|
| `skills/personal-trainer/SKILL.md` | Instructions the LLM follows to coach |
| `skills/personal-trainer/scripts/trainer_cli.py` | The single tool the agent calls (JSON I/O) |
| `skills/personal-trainer/scripts/workout_engine.py` | Deterministic split rotation, rep schemes, linear progression, deload |
| `skills/personal-trainer/scripts/exercises.py` | Exercise catalogue + equipment-aware selection |
| `skills/personal-trainer/scripts/onboarding.py` | Ordered steps + tolerant free-text parsing |
| `skills/personal-trainer/scripts/supabase_client.py` | PostgREST data access (service role) |
| `skills/personal-trainer/scripts/personalities.py` | Three trainer personality prompts |
| `skills/personal-trainer/scripts/access.py` | Subscription gating |
| `skills/personal-trainer/scripts/models.py` | Dataclasses + kg/lbs conversion |
| `config/` | `cli-config.yaml`, `SOUL.md`, `personalities.json`, `hermes.env.example` |

## Run the tests (no network needed)

The deterministic core is pure stdlib:

```bash
cd agent
python3 -m unittest discover -s tests -v
```

## Try the tool locally

```bash
cd agent/skills/personal-trainer
python3 scripts/trainer_cli.py persona --key science
python3 scripts/trainer_cli.py parse-onboarding --step goal --text "build muscle"
# DB-backed commands need SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY:
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  python3 scripts/trainer_cli.py whoami --telegram-id 12345
```

## Run the full bot

Build and run the agent container (see `../docker/` and `../DEPLOYMENT.md`). It
needs `DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`, and the Supabase service role
key. One bot serves all users; per-user data is isolated by the `user_id`
resolved from each sender's Telegram id.
