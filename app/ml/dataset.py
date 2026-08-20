"""
Dataset Builder for ML Training
Creates feature matrices with proper temporal train/test splits
"""
import numpy as np
from typing import Tuple, Dict, Any, List
from sqlalchemy import select, desc
from app.db.engine import AsyncSession
from app.db.models import Candle
from app.ml.features import calculate_features, build_model_vector, FEATURE_NAMES


async def get_candles_for_symbol(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 500
) -> List[Candle]:
    """Fetch candles in ascending order (oldest first)"""
    stmt = select(Candle).where(
        (Candle.symbol == symbol) & (Candle.timeframe == timeframe)
    ).order_by(desc(Candle.open_time)).limit(limit)
    result = await db.execute(stmt)
    candles = result.scalars().all()
    return sorted(candles, key=lambda c: c.open_time)  # ascending: oldest first


async def create_feature_sequence(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create feature sequences for all candles
    Returns: (features_matrix, timestamps)
    features_matrix shape: (n_candles, n_features)
    """
    candles = await get_candles_for_symbol(db, symbol, timeframe, limit=500)
    
    if len(candles) < 50:  # Need minimum candles for SMA50
        return None, None
    
    n_candles = len(candles)
    n_features = 12  # sma20, sma50, ema12, ema26, rsi14, macd, macd_signal, macd_hist, bb_upper, bb_mid, bb_lower, atr14
    
    features_matrix = np.zeros((n_candles, n_features), dtype=np.float32)
    timestamps = np.array([c.open_time for c in candles], dtype=np.int64)
    
    # Calculate features using rolling window approach
    closes = np.array([c.close for c in candles], dtype=np.float64)
    highs = np.array([c.high for c in candles], dtype=np.float64)
    lows = np.array([c.low for c in candles], dtype=np.float64)
    
    # Import indicator functions
    from app.ml.features import (
        calculate_sma, calculate_ema, calculate_rsi,
        calculate_macd, calculate_bollinger_bands, calculate_atr
    )
    
    # Calculate all indicators up to each point
    for i in range(50, n_candles):  # Start from index 50 (need min history)
        window_closes = closes[:i+1]
        window_highs = highs[:i+1]
        window_lows = lows[:i+1]
        
        # Calculate indicators
        sma20 = calculate_sma(window_closes, 20)
        sma50 = calculate_sma(window_closes, 50)
        ema12 = calculate_ema(window_closes, 12)
        ema26 = calculate_ema(window_closes, 26)
        rsi = calculate_rsi(window_closes, 14)
        macd, signal, histogram = calculate_macd(window_closes)
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(window_closes, 20)
        atr = calculate_atr(window_highs, window_lows, window_closes, 14)
        
        raw_indicators = dict(zip(FEATURE_NAMES, [
            sma20[-1], sma50[-1], ema12[-1], ema26[-1], rsi[-1],
            macd[-1], signal[-1], histogram[-1], bb_upper[-1], bb_mid[-1],
            bb_lower[-1], atr[-1],
        ]))
        features_matrix[i] = build_model_vector(raw_indicators, closes[i])
    
    return features_matrix, timestamps


def create_labels(
    candles: List[Candle],
    target_horizon: int = 5
) -> np.ndarray:
    """
    Create labels: 1 if price goes up in next target_horizon candles, 0 otherwise
    shape: (n_candles,)
    """
    closes = np.array([c.close for c in candles], dtype=np.float64)
    labels = np.zeros(len(candles), dtype=np.int32)
    
    for i in range(len(closes) - target_horizon):
        future_close = closes[i + target_horizon]
        current_close = closes[i]
        labels[i] = 1 if future_close > current_close else 0
    
    # Last horizon candles have no label (no future data)
    labels[-target_horizon:] = -1  # Mark as invalid
    
    return labels


def temporal_train_test_split(
    features_matrix: np.ndarray,
    labels: np.ndarray,
    train_ratio: float = 0.8,
    lookback_period: int = 20
) -> Dict[str, Any]:
    """
    Create temporal train/test split respecting time order
    Removes first lookback_period rows (insufficient history)
    
    Returns:
    {
        'train_features': (n_train, n_features),
        'train_labels': (n_train,),
        'test_features': (n_test, n_features),
        'test_labels': (n_test,),
        'train_indices': indices in original array,
        'test_indices': indices in original array,
        'lookback_period': int,
        'target_horizon': int
    }
    """
    # Remove first lookback_period rows (insufficient history)
    valid_start = max(50, lookback_period)  # 50 from feature calculation, lookback_period from labels
    valid_indices = np.arange(valid_start, len(features_matrix))
    
    # Only keep rows with valid labels (not -1)
    valid_mask = labels[valid_indices] != -1
    valid_indices = valid_indices[valid_mask]
    
    if len(valid_indices) == 0:
        raise ValueError("No valid training examples after removing initial window")
    
    # Calculate split point
    split_idx = int(len(valid_indices) * train_ratio)
    
    # Train indices: first 80% of valid indices
    train_indices = valid_indices[:split_idx]
    # Test indices: last 20% of valid indices (respects time order)
    test_indices = valid_indices[split_idx:]
    
    return {
        'train_features': features_matrix[train_indices].astype(np.float32),
        'train_labels': labels[train_indices].astype(np.int32),
        'test_features': features_matrix[test_indices].astype(np.float32),
        'test_labels': labels[test_indices].astype(np.int32),
        'train_indices': train_indices.tolist(),
        'test_indices': test_indices.tolist(),
        'n_features': features_matrix.shape[1],
        'n_train': len(train_indices),
        'n_test': len(test_indices),
        'lookback_period': lookback_period,
        'train_ratio': float(train_ratio),
        'feature_names': FEATURE_NAMES
    }


async def build_dataset(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
    lookback_period: int = 20,
    target_horizon: int = 5,
    train_ratio: float = 0.8
) -> Dict[str, Any]:
    """
    Build complete ML dataset with temporal split
    
    Args:
        db: AsyncSession
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Candle timeframe (e.g., '1h')
        lookback_period: Minimum bars required for features
        target_horizon: How many bars ahead to predict
        train_ratio: Fraction for training (e.g., 0.8 for 80/20 split)
    
    Returns:
        Dataset dict with train/test features and labels
    """
    # Get all candles
    candles = await get_candles_for_symbol(db, symbol, timeframe, limit=500)
    
    if not candles or len(candles) < 100:
        raise ValueError(f"Insufficient candles for {symbol} ({len(candles or [])}). Need at least 100.")
    
    # Create feature matrix
    features_matrix, timestamps = await create_feature_sequence(db, symbol, timeframe)
    
    if features_matrix is None:
        raise ValueError(f"Failed to create features for {symbol}")
    
    # Create labels (what we're trying to predict)
    labels = create_labels(candles, target_horizon=target_horizon)
    
    # Temporal split
    dataset = temporal_train_test_split(
        features_matrix,
        labels,
        train_ratio=train_ratio,
        lookback_period=lookback_period
    )
    
    # Add metadata
    dataset.update({
        'symbol': symbol,
        'timeframe': timeframe,
        'target_horizon': target_horizon,
        'total_candles': len(candles),
        'status': 'ready'
    })
    
    return dataset
