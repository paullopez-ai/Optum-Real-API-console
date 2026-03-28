"""
OAuth 2.0 token management for Optum Real APIs.
Port of: patient-cost-clarity-starter/lib/optum-auth.ts
"""

import os
import time

import httpx


class TokenCache:
    def __init__(self, token: str, expires_at: float):
        self.token = token
        self.expires_at = expires_at


_cached_token: TokenCache | None = None


def get_optum_bearer_token() -> str:
    """
    OAuth 2.0 client credentials flow.
    Caches token with 60-second safety buffer before expiry.
    """
    global _cached_token

    if _cached_token and time.time() < _cached_token.expires_at - 60:
        return _cached_token.token

    client_id = os.environ.get("OPTUM_CLIENT_ID")
    client_secret = os.environ.get("OPTUM_CLIENT_SECRET")
    auth_url = os.environ.get("OPTUM_AUTH_URL")

    if not client_id or not client_secret or not auth_url:
        raise RuntimeError(
            "Optum API credentials not configured. "
            "Set OPTUM_CLIENT_ID, OPTUM_CLIENT_SECRET, and OPTUM_AUTH_URL in .env"
        )

    response = httpx.post(
        auth_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Optum auth failed ({response.status_code}): {response.text}"
        )

    data = response.json()

    if "access_token" not in data or "expires_in" not in data:
        raise RuntimeError("Optum auth response missing access_token or expires_in")

    _cached_token = TokenCache(
        token=data["access_token"],
        expires_at=time.time() + data["expires_in"],
    )

    return _cached_token.token
