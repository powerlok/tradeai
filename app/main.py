from fastapi import FastAPI, Depends
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
from fastapi.responses import RedirectResponse

app = FastAPI(title="Trading AI", version="0.1.0")

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
app.include_router(login_router, prefix="/api/auth")


@app.get("/")
async def root():
    return RedirectResponse(url="http://localhost:5173/", status_code=307)
