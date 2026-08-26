from __future__ import annotations

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
import time
from sqlalchemy import select
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.db.engine import AsyncSession
from app.db.models import NewsItem
from app.quant.news import enrich_news
from app.observability.metrics import inc_news_enriched


COINGECKO_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin",
    "TRXUSDT": "tron",
    "AVAXUSDT": "avalanche-2",
    "LINKUSDT": "chainlink",
    "TONUSDT": "the-open-network",
    "SHIBUSDT": "shiba-inu",
    "DOTUSDT": "polkadot",
    "BCHUSDT": "bitcoin-cash",
    "LTCUSDT": "litecoin",
    "UNIUSDT": "uniswap",
    "XLMUSDT": "stellar",
    "NEARUSDT": "near",
    "ATOMUSDT": "cosmos",
    "APTUSDT": "aptos",
}

NEWS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}


class MarketIntelligenceService:
    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def get_context(self, symbols: list[str]) -> dict[str, object]:
        normalized = [symbol.upper() for symbol in symbols]
        result: dict[str, object] = {"sources": [], "assets": {}}
        uncached: list[str] = []

        for symbol in normalized:
            try:
                cached = await self.redis.get(f"market:intelligence:{symbol}")
            except RedisError:
                cached = None
            if cached:
                result["assets"][symbol] = json.loads(cached)
            else:
                uncached.append(symbol)

        if uncached:
            snapshots = await self._fetch_coingecko(uncached)
            for symbol, snapshot in snapshots.items():
                result["assets"][symbol] = snapshot
                try:
                    await self.redis.setex(f"market:intelligence:{symbol}", 60, json.dumps(snapshot))
                except RedisError:
                    pass

        if result["assets"]:
            result["sources"].append("CoinGecko public API")
        result["news"] = await self.get_news(normalized)
        if result["news"]:
            result["sources"].append("CoinDesk/Cointelegraph/Decrypt RSS")
        result["cache_ttl_seconds"] = 60
        return result

    async def get_news(self, symbols: list[str], limit: int = 8) -> list[dict[str, str]]:
        normalized = [symbol.upper().replace("USDT", "") for symbol in symbols]
        cache_key = "market:news:" + (":".join(sorted(normalized)) or "general")
        try:
            cached = await self.redis.get(cache_key)
        except RedisError:
            cached = None
        if cached:
            return json.loads(cached)

        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            responses = await asyncio.gather(
                *(client.get(url) for url in NEWS_FEEDS.values()), return_exceptions=True
            )
        items: list[dict[str, str]] = []
        seen: set[str] = set()
        aliases = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binance", "XRP": "xrp", "ADA": "cardano", "DOGE": "dogecoin"}
        keywords = [aliases.get(symbol, symbol.lower()) for symbol in normalized]
        for source, response in zip(NEWS_FEEDS, responses):
            if not isinstance(response, httpx.Response) or not response.is_success:
                continue
            try:
                root = ET.fromstring(response.text)
            except ET.ParseError:
                continue
            for item in root.findall(".//item")[:20]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                published = (item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
                haystack = re.sub(r"\s+", " ", title.lower())
                if not title or not link or (keywords and not any(keyword in haystack for keyword in keywords)):
                    continue
                dedupe_key = title.casefold()
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                enrichment = enrich_news(title)
                inc_news_enriched(source)
                news_item = {
                    "source": source, "title": title, "published_at": published, "url": link,
                    "assets": list(enrichment.assets), "event_type": enrichment.event_type,
                    "sentiment": enrichment.sentiment, "impact": enrichment.impact,
                    "confidence": enrichment.confidence,
                }
                items.append(news_item)
                await self._persist_news(news_item)
        items = items[:limit]
        try:
            await self.redis.setex(cache_key, 300, json.dumps(items, ensure_ascii=False))
        except (RedisError, RuntimeError):
            pass
        return items

    async def _persist_news(self, item: dict[str, object]) -> None:
        async with AsyncSession() as session:
            existing = await session.execute(select(NewsItem.id).where(NewsItem.url == item["url"]))
            if existing.scalar_one_or_none() is not None:
                return
            session.add(NewsItem(
                source=str(item["source"]), title=str(item["title"]),
                published_at=str(item["published_at"]), url=str(item["url"]),
                assets=item["assets"], event_type=str(item["event_type"]),
                sentiment=str(item["sentiment"]), impact=str(item["impact"]),
                confidence=float(item["confidence"]), first_seen_at=int(time.time() * 1000),
            ))
            try:
                await session.commit()
            except Exception:
                await session.rollback()

    async def _fetch_coingecko(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        ids = [COINGECKO_IDS[symbol] for symbol in symbols if symbol in COINGECKO_IDS]
        if not ids:
            return {}
        try:
            async with httpx.AsyncClient(base_url="https://api.coingecko.com", timeout=8) as client:
                response = await client.get(
                    "/api/v3/simple/price",
                    params={
                        "ids": ",".join(ids),
                        "vs_currencies": "usd",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true",
                        "include_24hr_change": "true",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            return {}

        return {
            symbol: {
                "source": "CoinGecko public API",
                "price_usd": payload.get(coin_id, {}).get("usd"),
                "market_cap_usd": payload.get(coin_id, {}).get("usd_market_cap"),
                "volume_24h_usd": payload.get(coin_id, {}).get("usd_24h_vol"),
                "change_24h_percent": payload.get(coin_id, {}).get("usd_24h_change"),
            }
            for symbol, coin_id in COINGECKO_IDS.items()
            if symbol in symbols and coin_id in payload
        }

    async def close(self) -> None:
        try:
            await self.redis.aclose()
        except (RedisError, RuntimeError):
            pass