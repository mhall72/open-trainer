"""Subscription gating — decide whether a Telegram user may use the bot."""
from __future__ import annotations

ACTIVE_STATUSES = {"active", "trial"}

SUBSCRIBE_PROMPT = (
    "👋 You're not subscribed yet. Grab Open-Trainer here: {url}\n"
    "After checkout you'll get a 6-character code — send it to me and we'll get started."
)
LINK_PROMPT = (
    "Almost there! Send me the 6-character code from your checkout page to link "
    "your subscription (looks like `9F3A2C`)."
)


def access_state(user: dict | None) -> str:
    """One of: 'unlinked' (no account yet), 'inactive' (linked but not paying),
    'ok' (active/trial)."""
    if not user:
        return "unlinked"
    if user.get("subscription_status") in ACTIVE_STATUSES:
        return "ok"
    return "inactive"


def gate_message(state: str, subscribe_url: str = "https://open-trainer.app") -> str | None:
    """Message to send when access is denied, or None when allowed."""
    if state == "ok":
        return None
    if state == "unlinked":
        return SUBSCRIBE_PROMPT.format(url=subscribe_url)
    return (
        "Your subscription isn't active right now. Renew at "
        f"{subscribe_url} and you'll be back in action."
    )
