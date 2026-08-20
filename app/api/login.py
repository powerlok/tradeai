from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel
import time
import jwt
from sqlalchemy import select

from app.core.config import settings
from app.db.engine import AsyncSession
from app.db.models import User
from app.security.password import verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    # if true, server will set an HttpOnly cookie with the JWT instead of returning it in JSON
    use_cookie: bool = False


async def get_db():
    async with AsyncSession() as session:
        yield session


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing JWT secret")

    stmt = select(User).where(User.username == req.username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {"sub": user.username, "iat": int(time.time()), "exp": int(time.time()) + settings.jwt_exp_seconds}
    payload["role"] = user.role
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    if req.use_cookie:
        resp = Response(content={"token_set": True})
        resp.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=settings.jwt_exp_seconds)
        return resp
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.jwt_exp_seconds}
