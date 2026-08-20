from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import numpy as np
from app.db.engine import AsyncSession
from app.ml.dataset import build_dataset
from app.ml.models import train_model, ModelTrainer
from app.auth import require_admin
from app.ml.registry import approve_version, list_versions

router = APIRouter()


async def get_db():
    from app.db.engine import AsyncSession as AS
    async with AS() as session:
        yield session


class TrainRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    model_type: str = "rf"
    lookback_period: int = 20
    target_horizon: int = 5
    train_ratio: float = 0.8
    cv_folds: int = 5
    approve: bool = False


class TrainResponse(BaseModel):
    symbol: str
    model_type: str
    status: str
    n_train: int
    n_test: int
    n_features: int
    metrics: dict
    feature_importance: dict
    model_path: str


@router.post("/train")
async def train_model_endpoint(
    request: TrainRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Train ML model on dataset
    
    Parameters:
    - symbol: Trading symbol (e.g., BTCUSDT)
    - timeframe: Candle timeframe (default: 1h)
    - model_type: "logistic", "rf" (default), "xgboost"
    - lookback_period: Bars for features (default: 20)
    - target_horizon: Bars ahead to predict (default: 5)
    - train_ratio: Train/test split (default: 0.8)
    - cv_folds: Cross-validation folds (default: 5)
    
    Returns:
    - Training metrics, feature importance, model path
    """
    
    try:
        # Build dataset
        dataset = await build_dataset(
            db,
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            lookback_period=request.lookback_period,
            target_horizon=request.target_horizon,
            train_ratio=request.train_ratio
        )
        
        # Train model
        result = await train_model(
            dataset,
            model_type=request.model_type,
            cv_folds=request.cv_folds,
            promote=request.approve,
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/registry")
async def model_registry(
    symbol: str = Query(None),
    timeframe: str = Query(None),
    model_type: str = Query(None),
):
    """List immutable candidates and active model versions."""
    return {"models": list_versions(symbol, timeframe, model_type)}


@router.post("/registry/{version}/approve", dependencies=[Depends(require_admin)])
async def approve_model_version(
    version: str,
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    model_type: str = Query("logistic"),
):
    """Promote a candidate version to active; admin only."""
    try:
        return approve_version(symbol.upper(), timeframe, model_type, version)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/predict")
async def predict_endpoint(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    model_type: str = Query("rf"),
    features: list = Query(...)
):
    """
    Make prediction using trained model
    
    Parameters:
    - symbol: Trading symbol
    - model_type: "logistic", "rf", "xgboost"
    - features: List of 12 feature values (must match training order)
    
    Returns:
    - prediction (0/1), probability
    """
    
    try:
        # Load model
        trainer = ModelTrainer.load(symbol.upper(), model_type, timeframe)
        
        # Prepare features
        X = np.array([features], dtype=np.float32)
        
        # Predict
        predictions, probabilities = trainer.predict(X)
        
        return {
            "symbol": symbol.upper(),
            "model_type": model_type,
            "prediction": int(predictions[0]),
            "probability": float(probabilities[0]),
            "signal": "BUY" if predictions[0] == 1 else "SELL"
        }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Model not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/info")
async def model_info():
    """Get model training information"""
    return {
        "description": "ML Model Training and Prediction",
        "endpoints": {
            "POST /api/ml/models/train": "Train model on dataset",
            "POST /api/ml/models/predict": "Make prediction with trained model",
            "GET /api/ml/models/info": "Get model info (this endpoint)"
        },
        "model_types": {
            "logistic": "Logistic Regression (fast, interpretable)",
            "rf": "Random Forest (default, balanced)",
            "xgboost": "XGBoost (powerful, requires installation)"
        },
        "metrics": {
            "accuracy": "Correct predictions / Total",
            "precision": "True positives / (True + False positives)",
            "recall": "True positives / (True positives + False negatives)",
            "f1": "Harmonic mean of precision and recall",
            "auc": "Area Under ROC Curve (0-1, higher is better)",
            "cv_*": "Cross-validation metrics (mean and std)"
        },
        "example_request": {
            "POST": "/api/ml/models/train",
            "body": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "model_type": "rf",
                "lookback_period": 20,
                "target_horizon": 5,
                "train_ratio": 0.8,
                "cv_folds": 5
            }
        }
    }
