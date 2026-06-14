# backend/auth.py

"""
Supabase JWT verification.

Every protected route depends on `get_current_user_id`, which:
  1. Reads the `Authorization: Bearer <jwt>` header
  2. Verifies the JWT against SUPABASE_JWT_SECRET (HS256)
  3. Returns the user's UUID (from the `sub` claim)

Tokens are issued by Supabase Auth on the client. The backend never sees
the user's password — it only ever verifies tokens.
"""

import logging
import os
import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET: Optional[str] = os.environ.get("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUDIENCE: str = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")

# auto_error=False so we can return a clearer 401 below instead of FastAPI's default.
_bearer = HTTPBearer(auto_error=False)


def _credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> uuid.UUID:
    """
    Validate the Supabase JWT and return the user's UUID.
    Raise 401 if the header is missing, malformed, expired, or signed wrong.
    """
    if SUPABASE_JWT_SECRET is None:
        # Fail loudly in dev if the secret isn't configured — silently allowing
        # unauthenticated requests would be a security hole.
        raise _credentials_exception(
            "Server is missing SUPABASE_JWT_SECRET; auth cannot be verified."
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise _credentials_exception("Missing or malformed Authorization header.")

    try:
        payload = jwt.decode(
            creds.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=SUPABASE_JWT_AUDIENCE,
        )
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
