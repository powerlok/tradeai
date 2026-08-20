import json
from urllib.request import Request, urlopen
from app.core.config import settings

base = "http://localhost:8000"
login = Request(base + "/api/auth/login", data=json.dumps({"username": settings.admin_username, "password": settings.admin_password}).encode(), headers={"Content-Type": "application/json"})
token = json.load(urlopen(login))["access_token"]
for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    for timeframe in ("4h", "1d"):
        for model_type in ("logistic", "rf"):
            request = Request(base + "/api/ml/models/train", data=json.dumps({"symbol": symbol, "timeframe": timeframe, "model_type": model_type, "cv_folds": 5}).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
            try:
                result = json.load(urlopen(request)); metrics = result["metrics"]
                print(json.dumps({"symbol": symbol, "timeframe": timeframe, "model": model_type, "auc": metrics.get("test_auc"), "accuracy": metrics.get("test_accuracy"), "version": result.get("version")}))
            except Exception as error:
                print(json.dumps({"symbol": symbol, "timeframe": timeframe, "model": model_type, "error": str(error)}))
