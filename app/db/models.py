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
    received_time = Column(BigInteger, index=True, nullable=False)

class OrderBookSnapshot(Base):
    __tablename__ = "order_book_snapshots"
    __table_args__ = (
        UniqueConstraint('symbol', 'event_time', name='uq_snapshot_symbol_event_time'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    event_time = Column(BigInteger, index=True, nullable=False)
    received_time = Column(BigInteger, index=True, nullable=False)
    bids = Column(JSONB, nullable=False)
    asks = Column(JSONB, nullable=False)
    bids_count = Column(Integer, nullable=False, default=0)
    asks_count = Column(Integer, nullable=False, default=0)

class OrderBookUpdate(Base):
    __tablename__ = "order_book_updates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    event_time = Column(BigInteger, index=True, nullable=False)
    received_time = Column(BigInteger, index=True, nullable=False)
    bids = Column(JSON)
    asks = Column(JSON)


class BookTicker(Base):
    __tablename__ = "book_tickers"
    __table_args__ = (
        UniqueConstraint('symbol', 'event_time', name='uq_book_ticker_symbol_event_time'),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    event_time = Column(BigInteger, index=True, nullable=False)
    received_time = Column(BigInteger, index=True, nullable=False)
    bid_price = Column(Float, nullable=False)
    bid_qty = Column(Float, nullable=False)
    ask_price = Column(Float, nullable=False)
    ask_qty = Column(Float, nullable=False)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    direction = Column(String(8), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    stop = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    status = Column(String(16), index=True, nullable=False)
    opened_at = Column(BigInteger, nullable=False)
    closed_at = Column(BigInteger)
    pnl = Column(Float)
    fees = Column(Float, nullable=False, default=0.0)
    decision_snapshot = Column(JSONB)
    exit_reason = Column(String(32))
    
class PaperTradeEvent(Base):
    __tablename__ = "paper_trade_events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_trade_id = Column(BigInteger, nullable=False, index=True)
    symbol = Column(String(16), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    event_time = Column(BigInteger, nullable=False, index=True)
    payload = Column(JSONB, nullable=False, default=dict)


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint('url', name='uq_news_item_url'),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    published_at = Column(String(128), nullable=False, default="")
    url = Column(String(1024), nullable=False)
    assets = Column(JSONB, nullable=False, default=list)
    event_type = Column(String(32), nullable=False)
    sentiment = Column(String(16), nullable=False)
    impact = Column(String(16), nullable=False)
    confidence = Column(Float, nullable=False)
    first_seen_at = Column(BigInteger, nullable=False)

# Optionally add indices
Index("ix_candle_symbol_timeframe_time", Candle.symbol, Candle.timeframe, Candle.open_time)
Index("ix_trade_symbol_event", Trade.symbol, Trade.event_time)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default="user")
