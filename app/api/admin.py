from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
import jwt

from app.core.config import settings
from app.auth import require_admin
from app.security.token_store import load_tokens, add_token, remove_token

router = APIRouter()


class TokenData(BaseModel):
    token: str


class JWTRequest(BaseModel):
    sub: str
    exp_seconds: int | None = 3600


@router.get("/admin/tokens", response_model=List[str], dependencies=[Depends(require_admin)])
async def list_tokens():
    return load_tokens()


@router.post("/admin/tokens", status_code=201, dependencies=[Depends(require_admin)])
async def create_token(data: TokenData):
    ok = add_token(data.token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token already exists")
    return {"ok": True}


@router.delete("/admin/tokens", dependencies=[Depends(require_admin)])
async def delete_token(data: TokenData):
    ok = remove_token(data.token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return {"ok": True}


@router.post("/admin/jwt", dependencies=[Depends(require_admin)])
async def issue_jwt(req: JWTRequest):
    if not settings.api_auth_mode or settings.api_auth_mode.lower() != 'jwt':
        raise HTTPException(status_code=400, detail="JWT mode is not enabled on server")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    payload = {"sub": req.sub}
    import time
    now = int(time.time())
    payload["iat"] = now
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if req.exp_seconds:
        payload["exp"] = now + int(req.exp_seconds)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return {"token": token}
