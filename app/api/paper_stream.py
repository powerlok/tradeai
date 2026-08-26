import asyncio
import json

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import settings

router = APIRouter()


@router.websocket("/paper/stream")
async def paper_stream(
    websocket: WebSocket,
    token: str = Query(...),
    symbols: str = Query(""),
):
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_alg],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience if settings.jwt_audience else None,
        )
        if payload.get("role") not in {"user", "admin"}:
            raise ValueError("invalid role")
    except (jwt.PyJWTError, ValueError, TypeError):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    selected_symbols = {item.strip().upper() for item in symbols.split(",") if item.strip()}
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await websocket.accept()
    await pubsub.subscribe("market:prices")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                event = json.loads(message["data"])
                if not selected_symbols or event.get("symbol") in selected_symbols:
                    await websocket.send_json(event)
            else:
                await websocket.send_json({"type": "heartbeat"})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await pubsub.unsubscribe("market:prices")
        await pubsub.close()
        await redis.close()
