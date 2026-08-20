"""
Test script to populate candles in database for feature testing
"""
import asyncio
from datetime import datetime, timedelta
from app.db.engine import AsyncSession, engine
from app.db.models import Candle, Base
import numpy as np


async def populate_test_candles():
    """Generate synthetic candle data for testing"""
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession() as session:
        # Generate synthetic BTCUSDT data
        symbol = "BTCUSDT"
        timeframe = "1h"
        now = datetime.utcnow()
        
        # Create 200 candles with realistic price movement
        price = 45000.0  # Starting price
        candles = []
        
        for i in range(200):
            timestamp = now - timedelta(hours=200-i)
            # Convert to milliseconds since epoch for storage
            timestamp_ms = int(timestamp.timestamp() * 1000)
            close_time_ms = int((timestamp + timedelta(hours=1)).timestamp() * 1000)
            
            # Realistic price movement (trend + noise)
            trend = (i / 200) * 2000  # Slight uptrend
            noise = np.random.normal(0, 100)
            open_price = price
            close_price = price + trend + noise
            high_price = max(open_price, close_price) + abs(np.random.normal(0, 50))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, 50))
            volume = np.random.uniform(50, 500)
            
            price = close_price
            
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=timestamp_ms,
                open=float(open_price),
                high=float(high_price),
                low=float(low_price),
                close=float(close_price),
                volume=float(volume),
                close_time=close_time_ms
            )
            candles.append(candle)
        
        session.add_all(candles)
        await session.commit()
        print(f"✓ Generated {len(candles)} synthetic candles for {symbol}")


if __name__ == "__main__":
    asyncio.run(populate_test_candles())
