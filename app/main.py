import asyncio
import json
import logging
import time
import uuid

from fastapi import FastAPI, Depends, Request
# ensure .env is loaded into process env before settings are imported
from dotenv import load_dotenv
load_dotenv()

from app.api.health import router as health_router
from app.api.signals import router as signals_router
from app.auth import require_bearer_token, require_user
from app.api.admin import router as admin_router
from app.api.login import router as login_router
from app.api.ml import router as ml_router
from app.api.dataset import router as dataset_router
from app.api.models import router as models_router
from app.api.backtest import router as backtest_router
from app.api.market import router as market_router
from app.api.chat import router as chat_router
from app.api.notifications import router as notifications_router
from app.api.news import router as news_router
from app.api.quant import router as quant_router
from app.api.paper import router as paper_router
from app.api.paper_stream import router as paper_stream_router
from app.api.opportunities import router as opportunities_router
from app.api.validation import router as validation_router
from app.api.context_validation import router as context_validation_router
from app.api.operational import router as operational_router
from app.api.observability import record_request_event, reset_correlation_id, router as observability_router, set_correlation_id
from app.services.opportunity_alerts import monitor as opportunity_alert_monitor
from fastapi.responses import RedirectResponse

app = FastAPI(title="Trading AI", version="0.1.0")
request_logger = logging.getLogger("tradeai.request")
request_logger.setLevel(logging.INFO)
if not request_logger.handlers:
    request_logger.addHandler(logging.StreamHandler())
request_logger.propagate = False


@app.middleware("http")
async def request_trace(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    correlation_token = set_correlation_id(correlation_id)
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        event = {"event": "request_failed", "timestamp": time.time(), "correlation_id": correlation_id, "method": request.method, "path": request.url.path, "status_code": 500}
        record_request_event(event)
        request_logger.exception(json.dumps(event, ensure_ascii=True))
        reset_correlation_id(correlation_token)
        raise
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    event = {"event": "request_completed", "timestamp": time.time(), "correlation_id": correlation_id, "method": request.method, "path": request.url.path, "status_code": response.status_code, "duration_ms": duration_ms}
    record_request_event(event)
    response.headers["X-Correlation-ID"] = correlation_id
    request_logger.info(json.dumps(event, ensure_ascii=True))
    reset_correlation_id(correlation_token)
    return response

app.include_router(health_router, prefix="/api")
# protect signals endpoints with user role dependency
app.include_router(signals_router, prefix="/api", dependencies=[Depends(require_user)])
# ML features endpoint: protected by user role
app.include_router(ml_router, prefix="/api/ml", dependencies=[Depends(require_user)])
# ML dataset builder endpoint: protected by user role
app.include_router(dataset_router, prefix="/api/ml/dataset", dependencies=[Depends(require_user)])
# ML models endpoint: protected by user role
app.include_router(models_router, prefix="/api/ml/models", dependencies=[Depends(require_user)])
app.include_router(backtest_router, prefix="/api/ml/backtest", dependencies=[Depends(require_user)])
app.include_router(admin_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(chat_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(notifications_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(quant_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(paper_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(paper_stream_router, prefix="/api")
app.include_router(opportunities_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(validation_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(context_validation_router, prefix="/api")
app.include_router(operational_router, prefix="/api")
app.include_router(observability_router, prefix="/api")
app.include_router(login_router, prefix="/api/auth")


@app.on_event("startup")
async def start_opportunity_alert_monitor():
    app.state.opportunity_alert_task = asyncio.create_task(opportunity_alert_monitor())


@app.on_event("shutdown")
async def stop_opportunity_alert_monitor():
    task = getattr(app.state, "opportunity_alert_task", None)
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@app.get("/")
async def root():
    return RedirectResponse(url="http://localhost:5173/", status_code=307)
