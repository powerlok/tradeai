from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.engine import Base

class Candle(Base):
    __tablename__ = "candles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    timeframe = Column(String(8), index=True, nullable=False)
    open_time = Column(BigInteger, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    close_time = Column(BigInteger, nullable=False)

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint('symbol', 'trade_id', name='uq_trade_symbol_tradeid'),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    trade_id = Column(BigInteger, index=True, nullable=False)
    price = Column(Float, nullable=False)
    qty = Column(Float, nullable=False)
    buyer_maker = Column(String(8))
    event_time = Column(BigInteger, index=True)

class OrderBookSnapshot(Base):
    __tablename__ = "order_book_snapshots"
    __table_args__ = (
        UniqueConstraint('symbol', 'event_time', name='uq_snapshot_symbol_event_time'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    event_time = Column(BigInteger, index=True, nullable=False)
    bids = Column(JSONB, nullable=False)
    asks = Column(JSONB, nullable=False)
    bids_count = Column(Integer, nullable=False, default=0)
    asks_count = Column(Integer, nullable=False, default=0)

class OrderBookUpdate(Base):
    __tablename__ = "order_book_updates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    event_time = Column(BigInteger, index=True, nullable=False)
    bids = Column(JSON)
    asks = Column(JSON)

# Optionally add indices
Index("ix_candle_symbol_timeframe_time", Candle.symbol, Candle.timeframe, Candle.open_time)
Index("ix_trade_symbol_event", Trade.symbol, Trade.event_time)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default="user")
