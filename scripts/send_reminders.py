#!/usr/bin/env python3
"""Workout reminder worker.

Runs periodically (e.g. Cloud Scheduler → Cloud Run Job every ~15 min). Finds
reminders whose scheduled local time just passed and that haven't fired for that
slot yet, then sends a Telegram nudge and stamps `last_sent_at`.

The slot-matching logic (`due_reminders`) is pure and unit-tested; the I/O
(Supabase + Telegram Bot API) only runs under `main()`.

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TELEGRAM_BOT_TOKEN
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

REMINDER_TEXT = (
    "⏰ Reminder: you've got a workout scheduled.\n"
    "Ready? Reply 'go' to start, or 'snooze 1h'."
)


def _tz(name: str):
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(name or "UTC")
    except Exception:
        return timezone.utc


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def due_reminders(reminders: list[dict], now_utc: datetime, window_minutes: int = 20) -> list[dict]:
    """Return reminders whose slot falls within [scheduled, scheduled+window)
    today (local tz) and that haven't already fired for that slot."""
    due = []
    for r in reminders:
        if not r.get("enabled", True):
            continue
        tz = _tz(r.get("timezone", "UTC"))
        local = now_utc.astimezone(tz)
        if WEEKDAYS[local.weekday()] not in (r.get("days") or []):
            continue
        try:
            hh, mm = (int(x) for x in str(r["time"]).split(":")[:2])
        except Exception:
            continue
        scheduled = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        delta = (local - scheduled).total_seconds()
        if not (0 <= delta < window_minutes * 60):
            continue
        last = _parse_dt(r.get("last_sent_at"))
        if last and last >= scheduled.astimezone(timezone.utc):
            continue  # already sent for this slot
        due.append(r)
    return due


def main() -> int:  # pragma: no cover - I/O path
    import httpx

    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    bot = os.environ["TELEGRAM_BOT_TOKEN"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    with httpx.Client(timeout=20, headers=headers) as c:
        resp = c.get(f"{url}/rest/v1/reminders",
                     params={"enabled": "eq.true", "select": "*,users(telegram_id)"})
        resp.raise_for_status()
        reminders = resp.json()

        now = datetime.now(timezone.utc)
        fired = 0
        for r in due_reminders(reminders, now):
            chat_id = (r.get("users") or {}).get("telegram_id")
            if not chat_id:
                continue
            tg = httpx.post(f"https://api.telegram.org/bot{bot}/sendMessage",
                            json={"chat_id": chat_id, "text": REMINDER_TEXT}, timeout=20)
            if tg.status_code < 300:
                c.patch(f"{url}/rest/v1/reminders", params={"id": f"eq.{r['id']}"},
                        json={"last_sent_at": now.isoformat()})
                fired += 1
        print(f"reminders checked={len(reminders)} fired={fired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
