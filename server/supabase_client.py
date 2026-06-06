"""Minimal Supabase (PostgREST) access for the web/subscription service.

Service-role key (bypasses RLS). Used by the Stripe webhook + checkout flow to
manage users and verification codes.
"""
from __future__ import annotations

import os
import secrets

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
        self._client = httpx.Client(timeout=timeout, headers={
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        })

    def _post(self, table: str, row: dict, params: dict | None = None, prefer: str = "return=representation"):
        r = self._client.post(f"{self._rest}/{table}", json=row, params=params or {},
                              headers={"Prefer": prefer})
        if r.status_code >= 300:
            raise SupabaseError(f"POST {table} -> {r.status_code}: {r.text}")
        data = r.json()
        return data[0] if isinstance(data, list) and data else data

    def _patch(self, table: str, params: dict, patch: dict):
        r = self._client.patch(f"{self._rest}/{table}", params=params, json=patch,
                               headers={"Prefer": "return=representation"})
        if r.status_code >= 300:
            raise SupabaseError(f"PATCH {table} -> {r.status_code}: {r.text}")
        return r.json()

    def _get(self, table: str, params: dict):
        r = self._client.get(f"{self._rest}/{table}", params=params)
        if r.status_code >= 300:
            raise SupabaseError(f"GET {table} -> {r.status_code}: {r.text}")
        return r.json()

    # -- verification codes --------------------------------------------------
    def existing_unconsumed_code(self, stripe_customer_id: str) -> dict | None:
        rows = self._get("verification_codes", {
            "stripe_customer_id": f"eq.{stripe_customer_id}",
            "consumed": "eq.false", "order": "created_at.desc", "limit": 1,
        })
        return rows[0] if rows else None

    def create_verification_code(self, *, stripe_customer_id=None, stripe_subscription_id=None,
                                 email=None) -> dict:
        # Reuse an outstanding code for this customer so reloads don't pile up.
        if stripe_customer_id:
            existing = self.existing_unconsumed_code(stripe_customer_id)
            if existing:
                return existing
        code = secrets.token_hex(3).upper()
        return self._post("verification_codes", {
            "code": code, "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id, "email": email,
        })

    # -- users ---------------------------------------------------------------
    def upsert_user_by_customer(self, stripe_customer_id: str, **fields) -> dict:
        fields = {k: v for k, v in fields.items() if v is not None}
        fields["stripe_customer_id"] = stripe_customer_id
        return self._post("users", fields, params={"on_conflict": "stripe_customer_id"},
                          prefer="return=representation,resolution=merge-duplicates")

    def set_subscription_status(self, stripe_customer_id: str, status: str) -> list:
        return self._patch("users", {"stripe_customer_id": f"eq.{stripe_customer_id}"},
                           {"subscription_status": status})
