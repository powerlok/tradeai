from collections import deque
from threading import Lock
from contextvars import ContextVar
import time
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.auth import require_user

router = APIRouter()
_events: deque[dict[str, Any]] = deque(maxlen=500)
_events_lock = Lock()
_correlation_id: ContextVar[str] = ContextVar("observability_correlation_id", default="")
application_logger = logging.getLogger("tradeai.application")
application_logger.setLevel(logging.INFO)
if not application_logger.handlers:
    application_logger.addHandler(logging.StreamHandler())
application_logger.propagate = False


def record_request_event(event: dict[str, Any]) -> None:
    with _events_lock:
        _events.appendleft(event)


def set_correlation_id(value: str):
    return _correlation_id.set(value)


def reset_correlation_id(token) -> None:
    _correlation_id.reset(token)


def record_application_event(event: str, component: str, message: str, correlation_id: str | None = None, **data: Any) -> None:
    payload = {
        "event": event,
        "timestamp": time.time(),
        "correlation_id": correlation_id or _correlation_id.get(),
        "component": component,
        "message": message,
        **data,
    }
    record_request_event(payload)
    application_logger.info(json.dumps(payload, ensure_ascii=True))


@router.get("/observability/events", dependencies=[Depends(require_user)])
async def get_observability_events(limit: int = Query(default=100, ge=1, le=500)):
    with _events_lock:
        events = list(_events)[:limit]
    return {"events": events, "buffer_size": len(events), "capacity": _events.maxlen}
