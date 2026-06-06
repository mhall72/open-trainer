"""Pure helpers for Stripe → Telegram account linking.

Stdlib only so it is unit-testable without FastAPI/Stripe/network.
"""
from __future__ import annotations

import re

_CODE_RE = re.compile(r"^[0-9A-F]{6}$")

# Stripe subscription.status → Open-Trainer users.subscription_status
_STATUS_MAP = {
    "active": "active",
    "trialing": "trial",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete_expired": "canceled",
    "incomplete": "inactive",
    "paused": "inactive",
}


def normalize_code(raw: str) -> str:
    """Uppercase + strip; also tolerates a `/start <code>` deep-link payload."""
    s = (raw or "").strip()
    if s.lower().startswith("/start"):
        s = s[len("/start"):].strip()
    return s.upper()


def is_valid_code(raw: str) -> bool:
    return bool(_CODE_RE.match(normalize_code(raw)))


def subscription_status_from_stripe(stripe_status: str) -> str:
    return _STATUS_MAP.get((stripe_status or "").lower(), "inactive")


def build_deep_link(bot_username: str, code: str) -> str:
    bot = (bot_username or "").lstrip("@")
    return f"https://t.me/{bot}?start={code}" if bot else ""


def verification_message(code: str, bot_username: str) -> str:
    """The instructions shown on the success page after checkout."""
    link = build_deep_link(bot_username, code)
    opener = f"Open {('@' + bot_username.lstrip('@')) if bot_username else 'the Open-Trainer bot'} in Telegram"
    lines = [
        "✅ Payment received!",
        f"Your verification code is: {code}",
        "",
        f"1. {opener}",
        f"2. Send this code: {code}",
        "3. I'll link your account and we'll set up your profile.",
    ]
    if link:
        lines.append("")
        lines.append(f"Or just tap: {link}")
    return "\n".join(lines)
