# backend/auth.py

"""
Supabase JWT verification.

Every protected route depends on `get_current_user_id`, which:
  1. Reads the `Authorization: Bearer <jwt>` header
  2. Verifies the JWT against Supabase's signing keys
  3. Returns the user's UUID (from the `sub` claim)

Supabase issues ES256-signed tokens via asymmetric signing keys. We fetch the
public keys from the project's JWKS endpoint
(`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`), pick the one matching the
JWT's `kid` header, and verify. PyJWT's PyJWKClient caches the JWKS in-memory
so we don't hit Supabase on every request.

For older projects still on the symmetric legacy secret, set
SUPABASE_JWT_SECRET and we fall back to HS256.
"""

import logging
import os
import uuid
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

# Load .env before reading any SUPABASE_* vars below. This module is imported
# (via the routers) BEFORE main.py calls load_dotenv(), so without this the
# vars would be read as None and every request would 401 with
# "Server is missing SUPABASE_URL". database.py loads .env the same way.
load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_JWT_SECRET: Optional[str] = os.environ.get("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUDIENCE: str = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")

_jwks_client: Optional[PyJWKClient] = None
if SUPABASE_URL:
    _jwks_client = PyJWKClient(
        f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
    )

_bearer = HTTPBearer(auto_error=False)


def _credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _verify(token: str) -> dict:
    """
    Decode and verify a Supabase access token. Tries the asymmetric (ES256
    via JWKS) path first if SUPABASE_URL is set; falls back to HS256 with
    SUPABASE_JWT_SECRET for legacy projects.
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg in ("ES256", "RS256") and _jwks_client is not None:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=SUPABASE_JWT_AUDIENCE,
        )

    if alg == "HS256" and SUPABASE_JWT_SECRET:
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=SUPABASE_JWT_AUDIENCE,
        )

    raise jwt.InvalidTokenError(
        f"No verification key configured for alg={alg!r}. "
        "Set SUPABASE_URL for asymmetric keys or SUPABASE_JWT_SECRET for HS256."
    )


async def get_current_user_id(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> uuid.UUID:
    """
    Validate the Supabase JWT and return the user's UUID.
    Raises 401 if the header is missing, malformed, expired, or signed wrong.
    """
    if _jwks_client is None and not SUPABASE_JWT_SECRET:
        # Fail loudly in dev if neither auth source is configured. Silently
        # allowing requests would be a security hole.
        raise _credentials_exception(
            "Server is missing SUPABASE_URL / SUPABASE_JWT_SECRET; "
            "auth cannot be verified."
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise _credentials_exception("Missing or malformed Authorization header.")

    try:
        payload = _verify(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise _credentials_exception("Token expired.")
    except jwt.InvalidTokenError as exc:
        logger.warning("Rejected token: %s", exc)
        raise _credentials_exception("Invalid token.")

    sub = payload.get("sub")
    if not sub:
        raise _credentials_exception("Token has no subject claim.")
    try:
        return uuid.UUID(sub)
    except ValueError:
        raise _credentials_exception("Token subject is not a UUID.")
