from __future__ import annotations

import json
import time
import uuid

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class NotificationService:
    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _key(self, user_id: str) -> str:
        return f"notifications:user:{user_id}"

    async def publish(self, user_id: str, notification_type: str, title: str, message: str, metadata: dict | None = None) -> dict:
        notification = {
            "id": str(uuid.uuid4()),
            "type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "created_at": int(time.time() * 1000),
        }
        try:
            await self.redis.lpush(self._key(user_id), json.dumps(notification, ensure_ascii=False))
            await self.redis.ltrim(self._key(user_id), 0, 49)
        except RedisError:
            pass
        finally:
            await self.close()
        return notification

    async def list_for_user(self, user_id: str, limit: int = 30) -> list[dict]:
        try:
            values = await self.redis.lrange(self._key(user_id), 0, max(0, min(limit, 50) - 1))
            return [json.loads(value) for value in values]
        except (RedisError, ValueError):
            return []

    async def delete(self, user_id: str, notification_id: str) -> None:
        try:
            values = await self.redis.lrange(self._key(user_id), 0, 49)
            for value in values:
                notification = json.loads(value)
                if notification.get("id") == notification_id:
                    await self.redis.lrem(self._key(user_id), 1, value)
                    break
        except (RedisError, ValueError):
            pass
        finally:
            await self.close()

    async def clear(self, user_id: str) -> None:
        try:
            await self.redis.delete(self._key(user_id))
        except RedisError:
            pass
        finally:
            await self.close()

    async def close(self) -> None:
        try:
            await self.redis.aclose()
        except (RedisError, RuntimeError):
            pass