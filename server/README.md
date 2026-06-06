# Open-Trainer Web/Subscription Service

FastAPI service that powers the landing page's billing + the Stripe→Telegram
account link. Runs on Cloud Run, separate from the bot; both share Supabase.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/healthz` | Cloud Run health check |
| POST | `/api/create-checkout-session` | Start a Stripe subscription checkout → `{url}` |
| GET  | `/api/checkout-status?session_id=` | After redirect: confirm payment, return the verification `code` + Telegram deep link |
| POST | `/api/stripe/webhook` | Keep `users.subscription_status` in sync (active/past_due/canceled) |
| GET  | `/*` | Serves the static landing page from `../website` |

## Env

See `../.env.template`. Needs: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`,
`STRIPE_WEBHOOK_SECRET`, `OPEN_TRAINER_PUBLIC_URL`, `TELEGRAM_BOT_USERNAME`,
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Run locally

```bash
cd server
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)   # or set vars manually
uvicorn app:app --reload --port 8080
# Stripe webhooks: stripe listen --forward-to localhost:8080/api/stripe/webhook
```

## Tests (offline)

```bash
cd server
python3 -m unittest discover -s tests -v   # pure linking helpers, no deps
```

## Account-linking flow

1. Landing page → `create-checkout-session` → Stripe Checkout.
2. Stripe redirects to `success.html?session_id=…`.
3. `success.html` calls `checkout-status`, which marks the user active and
   issues a 6-char code (idempotent per customer).
4. User sends the code to the Telegram bot (or taps the deep link, which sends
   `/start <code>`). The bot's `personal-trainer` skill calls `link` to bind the
   Telegram id to the Stripe customer and begins onboarding.

This bot-initiated link is used because Telegram bots cannot DM a user by handle
until that user has messaged the bot first.
