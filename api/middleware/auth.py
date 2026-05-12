"""
API Authentication Middleware for ORION Architekt AT
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Create auth router
router = APIRouter()

_raw_secret = os.getenv("JWT_SECRET_KEY", "")
SECRET_KEY = _raw_secret if _raw_secret else secrets.token_hex(64)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class User(BaseModel):
    user_id: str
    username: str
    email: str
    roles: List[str] = []
    is_active: bool = True


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return User(
            user_id=payload.get("user_id"),
            username=payload.get("username"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role"""
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_premium(current_user: User = Depends(get_current_active_user)) -> User:
    """Require premium subscription"""
    if "premium" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Premium subscription required")
    return current_user


# ---------------------------------------------------------------------------
# Auth router endpoints
# ---------------------------------------------------------------------------


@router.get("/me", tags=["auth"], summary="Aktuelle Benutzerinfo")
async def get_me(current_user: User = Depends(get_current_active_user)) -> dict:
    """
    🔐 **Aktuelle Benutzerinformation**

    Gibt die Profildaten des aktuell eingeloggten Benutzers zurück.
    Erfordert einen gültigen JWT Bearer Token.

    Wird für Sicherheitstests (OWASP API2) und Token-Validierung verwendet.
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "is_active": current_user.is_active,
    }


@router.get("/status", tags=["auth"], summary="Auth-Status prüfen")
async def auth_status() -> dict:
    """
    🔍 **Auth-System Status**

    Gibt den Status des Authentifizierungssystems zurück (öffentlich).
    """
    return {
        "auth_required": True,
        "algorithm": ALGORITHM,
        "token_type": "Bearer (JWT)",
        "hinweis": "Token über POST /auth/token beziehen.",
    }
