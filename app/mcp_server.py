from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from app.api.chat import extract_requested_symbols, fetch_live_market_context
from app.services.market_intelligence import MarketIntelligenceService


mcp = FastMCP("trade-market-intelligence", stateless_http=True, json_response=True)


@mcp.tool()
async def get_market_overview(symbols: list[str]) -> str:
    """Return CoinGecko overview data for up to four USDT symbols."""
    normalized = [symbol.upper() for symbol in symbols[:4]]
    service = MarketIntelligenceService()
    try:
        result = await service.get_context(normalized)
    finally:
        await service.close()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_multi_timeframe_analysis(symbol: str, timeframe: str = "1h") -> str:
    """Return Binance price, order book, and 15m/1h/4h/1d analysis."""
    result = await fetch_live_market_context(symbol.upper(), timeframe)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_market_news(symbols: list[str], limit: int = 8) -> str:
    """Return recent asset-matched news from public CoinDesk, Cointelegraph, and Decrypt RSS feeds."""
    service = MarketIntelligenceService()
    try:
        result = await service.get_news([symbol.upper() for symbol in symbols[:4]], min(limit, 12))
    finally:
        await service.close()
    return json.dumps({"sources": ["CoinDesk", "Cointelegraph", "Decrypt"], "items": result}, ensure_ascii=False)


@mcp.tool()
async def research_assets(question: str, timeframe: str = "1h") -> str:
    """Resolve assets from a market question and return their live Binance and CoinGecko data."""
    symbols = extract_requested_symbols(question, "AUTO")
    if not symbols:
        return json.dumps({"status": "asset_not_identified", "message": "Informe pelo menos um ativo ou par de mercado."}, ensure_ascii=False)

    binance = await asyncio.gather(*(
        fetch_live_market_context(symbol, timeframe) for symbol in symbols
    ))
    service = MarketIntelligenceService()
    try:
        overview = await service.get_context(symbols)
    finally:
        await service.close()
    return json.dumps({
        "question": question,
        "symbols": symbols,
        "binance": dict(zip(symbols, binance)),
        "market_overview": overview,
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 9000
    mcp.run(transport="streamable-http")