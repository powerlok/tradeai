from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from app.db.engine import AsyncSession
from app.ml.dataset import build_dataset
from typing import Optional

router = APIRouter()


async def get_db():
    from app.db.engine import AsyncSession as AS
    async with AS() as session:
        yield session


class DatasetRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    lookback_period: int = 20
    target_horizon: int = 5
    train_ratio: float = 0.8


class DatasetResponse(BaseModel):
    symbol: str
    timeframe: str
    status: str
    n_train: int
    n_test: int
    n_features: int
    target_horizon: int
    lookback_period: int
    train_ratio: float
    feature_names: list
    total_candles: int
    summary: dict


@router.post("/create")
async def create_dataset(
    request: DatasetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create ML dataset with temporal train/test split
    
    Parameters:
    - symbol: Trading symbol (e.g., BTCUSDT)
    - timeframe: Candle timeframe (e.g., 1h, 4h, 1d)
    - lookback_period: Minimum bars for feature calculation (default 20)
    - target_horizon: Bars ahead to predict (default 5)
    - train_ratio: Train/test split ratio (default 0.8 for 80/20)
    
    Returns:
    - Dataset metadata with train/test split info
    - Train samples: {n_train}
    - Test samples: {n_test}
    - Features: {n_features} technical indicators
    """
    
    try:
        dataset = await build_dataset(
            db,
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            lookback_period=request.lookback_period,
            target_horizon=request.target_horizon,
            train_ratio=request.train_ratio
        )
        
        # Calculate summary statistics
        import numpy as np
        train_features = np.array(dataset['train_features'])
        test_features = np.array(dataset['test_features'])
        
        summary = {
            "train_label_distribution": {
                "class_0": int((dataset['train_labels'] == 0).sum()),
                "class_1": int((dataset['train_labels'] == 1).sum()),
            },
            "test_label_distribution": {
                "class_0": int((dataset['test_labels'] == 0).sum()),
                "class_1": int((dataset['test_labels'] == 1).sum()),
            },
            "feature_stats": {
                "train_mean": [float(train_features[:, i].mean()) for i in range(train_features.shape[1])],
                "train_std": [float(train_features[:, i].std()) for i in range(train_features.shape[1])],
            }
        }
        
        return DatasetResponse(
            symbol=dataset['symbol'],
            timeframe=dataset['timeframe'],
            status=dataset['status'],
            n_train=dataset['n_train'],
            n_test=dataset['n_test'],
            n_features=dataset['n_features'],
            target_horizon=dataset['target_horizon'],
            lookback_period=dataset['lookback_period'],
            train_ratio=dataset['train_ratio'],
            feature_names=dataset['feature_names'],
            total_candles=dataset['total_candles'],
            summary=summary
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset creation failed: {str(e)}")


@router.get("/info")
async def dataset_info():
    """Get dataset builder information and parameters"""
    return {
        "description": "ML Dataset Builder with temporal train/test split",
        "endpoints": {
            "POST /api/ml/dataset/create": "Create dataset with features and labels",
            "GET /api/ml/dataset/info": "Get dataset info (this endpoint)"
        },
        "parameters": {
            "symbol": "Trading symbol (e.g., BTCUSDT)",
            "timeframe": "Candle timeframe: 1h, 4h, 1d (default: 1h)",
            "lookback_period": "Min bars for features (default: 20)",
            "target_horizon": "Bars ahead to predict (default: 5)",
            "train_ratio": "Train/test split 0-1 (default: 0.8)"
        },
        "features": [
            "sma_20", "sma_50", "ema_12", "ema_26", "rsi_14",
            "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "atr_14"
        ],
        "label": "Binary: 1 (price up), 0 (price down in next target_horizon bars)"
    }
