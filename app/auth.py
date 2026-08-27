from fastapi import Security, HTTPException, status
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

import jwt
from jwt import PyJWTError

from app.core.config import settings
from app.security.token_store import load_tokens

security = HTTPBearer(auto_error=False)


async def require_bearer_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    # assume JWT mode only: decode and return payload
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing JWT secret")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_alg],
            issuer=settings.jwt_issuer or None,
            audience=settings.jwt_audience if settings.jwt_audience else None,
        )
        return payload
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: invalid JWT token")


async def require_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    # JWT mode: decode and require role or admin subject
    if settings.api_auth_mode and settings.api_auth_mode.lower() == "jwt":
        if not settings.jwt_secret:
            raise HTTPException(status_code=500, detail="Server misconfiguration: missing JWT secret")
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_alg],
                issuer=settings.jwt_issuer or None,
                audience=settings.jwt_audience if settings.jwt_audience else None,
            )
            # allow if subject equals admin username or role claim contains admin
            if payload.get("sub") == settings.admin_username or payload.get("role") == "admin":
                return payload
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin role required")
        except PyJWTError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: invalid JWT token")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin token required")


async def require_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing JWT secret")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_alg],
            issuer=settings.jwt_issuer or None,
            audience=settings.jwt_audience if settings.jwt_audience else None,
        )
        if payload.get("role") in ("user", "admin"):
            return payload
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: user role required")
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: invalid JWT token")
