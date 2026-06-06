"""Thin Supabase (PostgREST) data-access layer for the trainer skill.

Uses the SERVICE-ROLE key (bypasses RLS) and always scopes queries by the
user_id resolved from the caller's telegram_id — that scoping IS the per-user
isolation (see supabase/migrations/0002_rls.sql).

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

import httpx


class SupabaseError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, url: str | None = None, key: str | None = None, timeout: float = 15.0):
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.url or not self.key:
            raise SupabaseError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        self._rest = f"{self.url}/rest/v1"
        self._headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(timeout=timeout, headers=self._headers)

    # -- low-level helpers ---------------------------------------------------
    def _get(self, table: str, params: dict) -> list:
        r = self._client.get(f"{self._rest}/{table}", params=params)
        if r.status_code >= 300:
            raise SupabaseError(f"GET {table} -> {r.status_code}: {r.text}")
        return r.json()

    def _insert(self, table: str, row: dict) -> dict:
        r = self._client.post(
            f"{self._rest}/{table}", json=row,
            headers={"Prefer": "return=representation"},
        )
        if r.status_code >= 300:
            raise SupabaseError(f"INSERT {table} -> {r.status_code}: {r.text}")
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    def _patch(self, table: str, params: dict, patch: dict) -> list:
        r = self._client.patch(
            f"{self._rest}/{table}", params=params, json=patch,
            headers={"Prefer": "return=representation"},
        )
        if r.status_code >= 300:
            raise SupabaseError(f"PATCH {table} -> {r.status_code}: {r.text}")
        return r.json()

    def _upsert(self, table: str, row: dict, on_conflict: str) -> dict:
        r = self._client.post(
            f"{self._rest}/{table}", json=row, params={"on_conflict": on_conflict},
            headers={"Prefer": "return=representation,resolution=merge-duplicates"},
        )
        if r.status_code >= 300:
            raise SupabaseError(f"UPSERT {table} -> {r.status_code}: {r.text}")
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    # -- users / linking -----------------------------------------------------
    def get_user_by_telegram(self, telegram_id: int) -> dict | None:
        rows = self._get("users", {"telegram_id": f"eq.{telegram_id}", "limit": 1})
        return rows[0] if rows else None

    def link_telegram(self, code: str, telegram_id: int, telegram_username: str | None) -> dict:
        """Consume a verification code and link/activate the Telegram user.

        Returns the linked user row. Raises if the code is missing/expired/used.
        """
        now = datetime.now(timezone.utc).isoformat()
        codes = self._get("verification_codes", {
            "code": f"eq.{code}", "consumed": "eq.false",
            "expires_at": f"gt.{now}", "limit": 1,
        })
        if not codes:
            raise SupabaseError("Invalid, expired, or already-used verification code.")
        vc = codes[0]

        # Reuse an existing user for this Stripe customer if present, else create.
        user = None
        if vc.get("stripe_customer_id"):
            existing = self._get("users", {
                "stripe_customer_id": f"eq.{vc['stripe_customer_id']}", "limit": 1})
            user = existing[0] if existing else None

        fields = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "stripe_customer_id": vc.get("stripe_customer_id"),
            "stripe_subscription_id": vc.get("stripe_subscription_id"),
            "email": vc.get("email"),
            "subscription_status": "active",
        }
        if user:
            user = self._patch("users", {"id": f"eq.{user['id']}"}, fields)[0]
        else:
            user = self._insert("users", fields)

        self._patch("verification_codes", {"id": f"eq.{vc['id']}"}, {"consumed": True})
        return user

    def create_verification_code(self, *, stripe_customer_id=None, stripe_subscription_id=None,
                                 email=None, telegram_username=None) -> dict:
        code = secrets.token_hex(3).upper()  # 6 hex chars, e.g. "9F3A2C"
        return self._insert("verification_codes", {
            "code": code,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "email": email,
            "telegram_username": telegram_username,
        })

    def set_subscription_status(self, stripe_customer_id: str, status: str) -> None:
        self._patch("users", {"stripe_customer_id": f"eq.{stripe_customer_id}"},
                    {"subscription_status": status})

    # -- profiles ------------------------------------------------------------
    def get_profile(self, user_id: str) -> dict | None:
        rows = self._get("profiles", {"user_id": f"eq.{user_id}", "limit": 1})
        return rows[0] if rows else None

    def upsert_profile(self, user_id: str, **fields) -> dict:
        fields = {k: v for k, v in fields.items() if v is not None}
        fields["user_id"] = user_id
        return self._upsert("profiles", fields, on_conflict="user_id")

    # -- workouts / exercises / sets ----------------------------------------
    def list_history(self, user_id: str, limit: int = 10) -> list:
        """Recent workouts with nested exercises + sets (most recent first)."""
        return self._get("workouts", {
            "user_id": f"eq.{user_id}",
            "select": "*,exercises(*,sets(*))",
            "order": "date.desc,started_at.desc",
            "limit": limit,
        })

    def active_workout(self, user_id: str) -> dict | None:
        rows = self._get("workouts", {
            "user_id": f"eq.{user_id}", "status": "eq.in_progress",
            "select": "*,exercises(*,sets(*))",
            "order": "started_at.desc", "limit": 1,
        })
        return rows[0] if rows else None

    def create_workout(self, user_id: str, name: str, focus: str, planned: list) -> dict:
        workout = self._insert("workouts", {
            "user_id": user_id, "name": name, "focus": focus, "status": "in_progress",
        })
        for pe in planned:
            self._insert("exercises", {
                "workout_id": workout["id"], "name": pe["name"],
                "exercise_type": pe.get("exercise_type", "strength"),
                "target_muscle_group": pe.get("target_muscle_group"),
                "target_sets": pe.get("target_sets"), "target_reps": pe.get("target_reps"),
                "notes": pe.get("notes"), "sort_order": pe.get("sort_order", 0),
            })
        return self.active_workout(user_id) or workout

    def log_set(self, exercise_id: str, set_number: int, reps: int,
                weight_kg: float | None, rpe: float | None = None) -> dict:
        return self._insert("sets", {
            "exercise_id": exercise_id, "set_number": set_number,
            "reps": reps, "weight_kg": weight_kg, "rpe": rpe, "completed": True,
        })

    def complete_workout(self, workout_id: str, notes: str | None = None) -> dict:
        patch = {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
        if notes:
            patch["notes"] = notes
        return self._patch("workouts", {"id": f"eq.{workout_id}"}, patch)[0]

    # -- exercise library ----------------------------------------------------
    def exercise_library(self) -> list:
        return self._get("exercise_library", {"select": "*"})

    # -- reminders -----------------------------------------------------------
    def list_reminders(self, user_id: str) -> list:
        return self._get("reminders", {"user_id": f"eq.{user_id}"})

    def add_reminder(self, user_id: str, days: list, time: str, timezone_name: str = "UTC") -> dict:
        return self._insert("reminders", {
            "user_id": user_id, "days": days, "time": time, "timezone": timezone_name,
        })

    def set_reminder_enabled(self, reminder_id: str, enabled: bool) -> dict:
        return self._patch("reminders", {"id": f"eq.{reminder_id}"}, {"enabled": enabled})[0]
