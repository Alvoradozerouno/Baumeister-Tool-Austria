"""
API Authentication Middleware for ORION Architekt AT
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


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


@router.post("/token", response_model=TokenResponse, tags=["auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    🔑 **Obtain JWT access token**

    Authenticate with username and password to receive a Bearer token.
    Use the returned token in the `Authorization: Bearer <token>` header for protected endpoints.

    **Demo credentials** (development only):
    - username: `demo`, password: `demo`
    - username: `admin`, password: `admin`
    """
    # Demo user store — replace with real database lookup in production
    demo_users = {
        "demo": {
            "password": "demo",
            "user_id": "usr_demo",
            "email": "demo@orion-architekt.at",
            "roles": [],
        },
        "admin": {
            "password": "admin",
            "user_id": "usr_admin",
            "email": "admin@orion-architekt.at",
            "roles": ["admin", "premium"],
        },
    }

    user_record = demo_users.get(form_data.username)
    if not user_record or not secrets.compare_digest(user_record["password"], form_data.password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "user_id": user_record["user_id"],
        "username": form_data.username,
        "email": user_record["email"],
        "roles": user_record["roles"],
    }
    access_token = create_access_token(token_data)
    logger.info(f"Token issued for user: {form_data.username}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", tags=["auth"])
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    👤 **Get current authenticated user info**

    Returns information about the currently authenticated user.
    Requires a valid Bearer token.
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "is_active": current_user.is_active,
    }
