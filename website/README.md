# Open-Trainer Website

Static landing page + Stripe checkout + post-checkout linking screen.

- `index.html` — landing page; the **Subscribe** buttons call
  `POST /api/create-checkout-session` and redirect to Stripe.
- `success.html` — Stripe redirect target; polls `GET /api/checkout-status`
  and shows the verification code + Telegram deep link.
- `styles.css`, `app.js` — styling and client logic (vanilla, no build step).

## Serving

The static files are served by the FastAPI service in `../server` (mounted at
`/`), so a single Cloud Run service can host both the API and the page. To host
the page elsewhere (e.g. a CDN), point the client at the API with a query param:

```
https://your-cdn/index.html?api=https://api.open-trainer.app
```

`app.js` reads `?api=` and prefixes all requests with it; default is same-origin.

## Config it depends on (set on the server)

`STRIPE_PRICE_ID`, `OPEN_TRAINER_PUBLIC_URL` (used to build Stripe success/cancel
URLs), and `TELEGRAM_BOT_USERNAME` (for the deep link).
