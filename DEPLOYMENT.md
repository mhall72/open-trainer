# Open-Trainer — Deployment Runbook

Everything needed to take this repo live. The code is deploy-ready; these steps
provision the external services and supply credentials. Nothing here was run
during the build session (no live GCP/Stripe/Telegram credentials were
available), so treat this as the checklist for go-live.

## 0. Prerequisites

- `gcloud` CLI authed to your GCP project
- `supabase` CLI (or `psql`) for migrations
- A Stripe account (test keys to start), a Telegram bot from **@BotFather**, and
  a **DeepSeek** API key

## 1. Database (Supabase)

```bash
# CLI
scripts/apply_supabase.sh --cli
# or psql
SUPABASE_DB_URL='postgresql://postgres:...@db.lhquhastwnurmvyrzdeh.supabase.co:5432/postgres' \
  scripts/apply_supabase.sh
```

Verify (see `supabase/README.md`): 8 tables, ~44 exercise_library rows, RLS on,
and run the security advisor. Grab the **service-role key** and **anon key** from
Project Settings → API.

## 2. Telegram bot

1. `@BotFather` → `/newbot` → note the **token** and the **username**.
2. Recommended privacy: `/setprivacy` → Disabled (so it sees direct messages),
   and set a description / about text.

## 3. Stripe

1. Create a **Product** with a recurring **Price**; note the `price_…` id.
2. Create a webhook endpoint → `https://<web-service-url>/api/stripe/webhook`
   subscribed to `checkout.session.completed`,
   `customer.subscription.updated/deleted/created`. Note the signing secret.

## 4. Secrets (Secret Manager)

The Cloud Run manifests reference these secrets — create them:

```bash
for s in deepseek-api-key telegram-bot-token supabase-service-role-key \
         stripe-secret-key stripe-price-id stripe-webhook-secret; do
  gcloud secrets create "$s" --replication-policy=automatic 2>/dev/null || true
done
printf '%s' "$DEEPSEEK_API_KEY"        | gcloud secrets versions add deepseek-api-key --data-file=-
printf '%s' "$TELEGRAM_BOT_TOKEN"      | gcloud secrets versions add telegram-bot-token --data-file=-
printf '%s' "$SUPABASE_SERVICE_ROLE"   | gcloud secrets versions add supabase-service-role-key --data-file=-
printf '%s' "$STRIPE_SECRET_KEY"       | gcloud secrets versions add stripe-secret-key --data-file=-
printf '%s' "$STRIPE_PRICE_ID"         | gcloud secrets versions add stripe-price-id --data-file=-
printf '%s' "$STRIPE_WEBHOOK_SECRET"   | gcloud secrets versions add stripe-webhook-secret --data-file=-
```

Grant the Cloud Run runtime service account `roles/secretmanager.secretAccessor`.

## 5. Artifact Registry

```bash
gcloud artifacts repositories create open-trainer \
  --repository-format=docker --location="$REGION"
```

## 6. Build & deploy

```bash
REGION=us-central1 scripts/deploy.sh
```

This (via `docker/cloudbuild.yaml`):
1. builds the pinned Hermes base from GitHub,
2. builds the **bot** overlay and the **web** image,
3. pushes both,
4. `gcloud run services replace` for both manifests.

Edit non-secret env (URLs, `TELEGRAM_BOT_USERNAME`) directly in
`docker/cloud-run-*.yaml` before deploying.

### Post-deploy wiring

- Point your domain / `OPEN_TRAINER_PUBLIC_URL` at the **web** service.
- Set the Stripe webhook URL to the web service (step 3).
- The bot uses long-poll by default (min=max=1 instance keeps it warm). If you
  prefer webhooks, set the Telegram webhook to the bot service URL.

## 7. Reminders (optional)

Deploy `scripts/send_reminders.py` as a Cloud Run **Job** and trigger it every
~15 min with Cloud Scheduler:

```bash
gcloud run jobs create open-trainer-reminders \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/open-trainer/web:latest" \
  --command python --args /app/scripts/send_reminders.py \
  --set-secrets SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest \
  --set-env-vars SUPABASE_URL=https://lhquhastwnurmvyrzdeh.supabase.co --region "$REGION"
gcloud scheduler jobs create http reminders-cron \
  --schedule "*/15 * * * *" --uri "<run-job-trigger>" --http-method POST
```

(Bundle `scripts/` into the web image, or build a tiny dedicated image — the
script only needs `httpx` + stdlib.)

## 8. Smoke test

1. Subscribe on the landing page (Stripe test card `4242 4242 4242 4242`).
2. Copy the code from the success page → message the bot → it links and onboards.
3. "let's work out" → start → log a couple of sets → it confirms and progresses.

## Local development

```bash
scripts/run_tests.sh                      # all offline tests
cd server && uvicorn app:app --port 8080  # web service (needs env)
# bot: build the base + overlay (scripts/build_base.sh) and run with env set
```
