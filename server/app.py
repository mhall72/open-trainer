"""Open-Trainer web/subscription service (FastAPI, runs on Cloud Run).

Responsibilities Hermes doesn't cover:
  * create Stripe Checkout sessions for the landing page
  * issue the Telegram verification code after a paid checkout
  * handle Stripe webhooks to keep users.subscription_status in sync
  * serve the static landing page

The bot itself runs separately (see ../agent + ../docker). Both talk to Supabase.
"""
from __future__ import annotations

import os
from pathlib import Path

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from linking import (build_deep_link, subscription_status_from_stripe,
                     verification_message)
from supabase_client import SupabaseClient, SupabaseError

# --- config -----------------------------------------------------------------
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PUBLIC_URL = os.environ.get("OPEN_TRAINER_PUBLIC_URL", "http://localhost:8080").rstrip("/")
BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
WEBSITE_DIR = Path(os.environ.get("WEBSITE_DIR", Path(__file__).resolve().parent.parent / "website"))

app = FastAPI(title="Open-Trainer", version="1.0.0")

_db: SupabaseClient | None = None


def get_db() -> SupabaseClient:
    global _db
    if _db is None:
        _db = SupabaseClient()
    return _db


# --- health -----------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# --- checkout ---------------------------------------------------------------
@app.post("/api/create-checkout-session")
def create_checkout_session():
    if not (stripe.api_key and STRIPE_PRICE_ID):
        raise HTTPException(500, "Stripe is not configured (STRIPE_SECRET_KEY / STRIPE_PRICE_ID).")
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{PUBLIC_URL}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{PUBLIC_URL}/?canceled=1",
            allow_promotion_codes=True,
        )
    except Exception as e:
        raise HTTPException(502, f"Stripe error: {e}")
    return {"id": session.id, "url": session.url}


@app.get("/api/checkout-status")
def checkout_status(session_id: str):
    """Called by success.html. Confirms payment and returns the link code."""
    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured.")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        raise HTTPException(502, f"Stripe error: {e}")

    paid = session.get("payment_status") == "paid" or session.get("status") == "complete"
    if not paid:
        return {"paid": False}

    customer = session.get("customer")
    subscription = session.get("subscription")
    email = (session.get("customer_details") or {}).get("email")
    try:
        db = get_db()
        db.upsert_user_by_customer(customer, email=email,
                                   stripe_subscription_id=subscription,
                                   subscription_status="active")
        vc = db.create_verification_code(stripe_customer_id=customer,
                                         stripe_subscription_id=subscription, email=email)
    except SupabaseError as e:
        raise HTTPException(502, f"Database error: {e}")

    code = vc["code"]
    return {
        "paid": True, "code": code,
        "deep_link": build_deep_link(BOT_USERNAME, code),
        "message": verification_message(code, BOT_USERNAME),
    }


# --- webhook ----------------------------------------------------------------
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "STRIPE_WEBHOOK_SECRET not configured.")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, f"Invalid webhook signature: {e}")

    etype = event["type"]
    obj = event["data"]["object"]
    try:
        db = get_db()
        if etype == "checkout.session.completed":
            customer = obj.get("customer")
            subscription = obj.get("subscription")
            email = (obj.get("customer_details") or {}).get("email")
            if customer:
                db.upsert_user_by_customer(customer, email=email,
                                           stripe_subscription_id=subscription,
                                           subscription_status="active")
                db.create_verification_code(stripe_customer_id=customer,
                                            stripe_subscription_id=subscription, email=email)
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted",
                       "customer.subscription.created"):
            customer = obj.get("customer")
            status = subscription_status_from_stripe(obj.get("status"))
            if customer:
                db.set_subscription_status(customer, status)
    except SupabaseError as e:
        # Tell Stripe to retry on transient DB issues.
        return JSONResponse({"error": str(e)}, status_code=503)

    return {"received": True}


# --- static landing page (optional single-service deploy) -------------------
if WEBSITE_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEBSITE_DIR), html=True), name="website")
