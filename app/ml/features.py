"""
Feature Engineering Module for Technical Indicators
Calculates RSI, MACD, Bollinger Bands, SMA, EMA, ATR from OHLCV data
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from sqlalchemy import select, desc
from app.db.engine import AsyncSession
from app.db.models import Candle


FEATURE_NAMES = [
    "sma_20", "sma_50", "ema_12", "ema_26", "rsi_14",
    "macd", "macd_signal", "macd_histogram",
    "bb_upper", "bb_middle", "bb_lower", "atr_14",
]


def build_model_vector(indicators: Dict[str, Any], close: float) -> np.ndarray:
    """Convert raw indicators into price-relative, model-friendly features."""
    safe_close = max(abs(float(close)), 1e-12)
    return np.array([
        float(indicators["sma_20"]) / safe_close - 1.0,
        float(indicators["sma_50"]) / safe_close - 1.0,
        float(indicators["ema_12"]) / safe_close - 1.0,
        float(indicators["ema_26"]) / safe_close - 1.0,
        float(indicators["rsi_14"]) / 100.0,
        float(indicators["macd"]) / safe_close,
        float(indicators["macd_signal"]) / safe_close,
        float(indicators["macd_histogram"]) / safe_close,
        float(indicators["bb_upper"]) / safe_close - 1.0,
        float(indicators["bb_middle"]) / safe_close - 1.0,
        float(indicators["bb_lower"]) / safe_close - 1.0,
        float(indicators["atr_14"]) / safe_close,
    ], dtype=np.float32)


async def get_recent_candles(db: AsyncSession, symbol: str, timeframe: str = "1h", limit: int = 200):
    """Fetch recent candles from DB for feature calculation"""
    stmt = select(Candle).where(
        (Candle.symbol == symbol) & (Candle.timeframe == timeframe)
    ).order_by(desc(Candle.open_time)).limit(limit)
    result = await db.execute(stmt)
    candles = result.scalars().all()
    return sorted(candles, key=lambda c: c.open_time)  # ascending


def calculate_sma(closes: np.ndarray, period: int = 20) -> np.ndarray:
    """Simple Moving Average"""
    return np.convolve(closes, np.ones(period) / period, mode='valid')


def calculate_ema(closes: np.ndarray, period: int = 20) -> np.ndarray:
    """Exponential Moving Average"""
    ema = np.zeros_like(closes)
    ema[0] = closes[0]
    multiplier = 2.0 / (period + 1)
    for i in range(1, len(closes)):
        ema[i] = closes[i] * multiplier + ema[i - 1] * (1 - multiplier)
    return ema


def calculate_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index"""
    deltas = np.diff(closes)
    seed = deltas[:period + 1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(closes)
    rsi[:period] = 100.0 - 100.0 / (1.0 + rs)
    
    for i in range(period, len(closes)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.0
        else:
            upval = 0.0
            downval = -delta
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100.0 - 100.0 / (1.0 + rs)
    
    return rsi


def calculate_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)
    
    # Align lengths
    min_len = min(len(ema_fast), len(ema_slow))
    macd_line = ema_fast[-min_len:] - ema_slow[-min_len:]
    
    # Signal line (EMA of MACD)
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line[len(macd_line) - len(signal_line):] - signal_line
    
    return macd_line[-len(signal_line):], signal_line, histogram


def calculate_bollinger_bands(closes: np.ndarray, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands"""
    sma = calculate_sma(closes, period)
    std = np.std(closes[-period:])
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    return upper, sma, lower


def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14):
    """Average True Range"""
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.zeros_like(tr)
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


async def calculate_features(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 200
) -> Optional[Dict[str, Any]]:
    """Calculate all technical indicators for a symbol"""
    
    candles = await get_recent_candles(db, symbol, timeframe, limit)
    if not candles:
        return None
    
    # Convert to arrays
    opens = np.array([c.open for c in candles], dtype=np.float64)
    highs = np.array([c.high for c in candles], dtype=np.float64)
    lows = np.array([c.low for c in candles], dtype=np.float64)
    closes = np.array([c.close for c in candles], dtype=np.float64)
    volumes = np.array([c.volume for c in candles], dtype=np.float64)
    
    # Calculate indicators
    sma20 = calculate_sma(closes, 20)
    sma50 = calculate_sma(closes, 50)
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    rsi = calculate_rsi(closes, 14)
    macd, signal, histogram = calculate_macd(closes)
    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(closes, 20)
    atr = calculate_atr(highs, lows, closes, 14)
    
    # Get latest values
    latest_close = closes[-1]
    latest_volume = volumes[-1]
    
    # Convert numpy types to Python native types for JSON serialization
    def to_python(val):
        """Convert numpy/pandas types to Python native types"""
        if val is None:
            return None
        if isinstance(val, (np.integer, np.floating)):
            return float(val)
        if isinstance(val, (np.bool_, bool)):
            return bool(val)
        return val
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": candles[-1].close_time,
        "close": float(latest_close),
        "volume": float(latest_volume),
        "indicators": {
            "sma_20": to_python(sma20[-1]) if len(sma20) > 0 else None,
            "sma_50": to_python(sma50[-1]) if len(sma50) > 0 else None,
            "ema_12": to_python(ema12[-1]) if len(ema12) > 0 else None,
            "ema_26": to_python(ema26[-1]) if len(ema26) > 0 else None,
            "rsi_14": to_python(rsi[-1]) if len(rsi) > 0 else None,
            "macd": to_python(macd[-1]) if len(macd) > 0 else None,
            "macd_signal": to_python(signal[-1]) if len(signal) > 0 else None,
            "macd_histogram": to_python(histogram[-1]) if len(histogram) > 0 else None,
            "bb_upper": to_python(bb_upper[-1]) if len(bb_upper) > 0 else None,
            "bb_middle": to_python(bb_mid[-1]) if len(bb_mid) > 0 else None,
            "bb_lower": to_python(bb_lower[-1]) if len(bb_lower) > 0 else None,
            "atr_14": to_python(atr[-1]) if len(atr) > 0 else None,
        },
        "summary": {
            "is_overbought": to_python(float(rsi[-1]) > 70) if len(rsi) > 0 else None,
            "is_oversold": to_python(float(rsi[-1]) < 30) if len(rsi) > 0 else None,
            "price_above_bb_upper": to_python(latest_close > bb_upper[-1]) if len(bb_upper) > 0 else None,
            "price_below_bb_lower": to_python(latest_close < bb_lower[-1]) if len(bb_lower) > 0 else None,
            "macd_positive": to_python(macd[-1] > signal[-1]) if (len(macd) > 0 and len(signal) > 0) else None,
        }
    }
