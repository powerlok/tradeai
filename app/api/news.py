from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.auth import require_user
from app.services.market_intelligence import MarketIntelligenceService
from app.db.engine import AsyncSession
from app.db.models import NewsItem

router = APIRouter()


@router.get("/news")
async def get_news(
    limit: int = Query(24, ge=1, le=50),
    symbols: str | None = Query(None, description="Comma-separated symbols; omit for general crypto news"),
    user: dict = Depends(require_user),
) -> dict[str, object]:
    requested_symbols = [item.strip().upper() for item in (symbols or "").split(",") if item.strip()]
    service = MarketIntelligenceService()
    try:
        items = await service.get_news(requested_symbols, limit=limit)
    finally:
        await service.close()
    return {"news": items, "source": "CoinDesk, Cointelegraph e Decrypt RSS", "limit": limit}


@router.get("/news/history")
async def get_news_history(
    limit: int = Query(50, ge=1, le=100),
    source: str | None = Query(None),
    user: dict = Depends(require_user),
) -> dict[str, object]:
    async with AsyncSession() as session:
        query = select(NewsItem).order_by(NewsItem.first_seen_at.desc()).limit(limit)
        if source:
            query = query.where(NewsItem.source == source)
        result = await session.execute(query)
        items = []
        for item in result.scalars().all():
            items.append({
                "id": item.id, "source": item.source, "title": item.title,
                "published_at": item.published_at, "url": item.url,
                "assets": item.assets, "event_type": item.event_type,
                "sentiment": item.sentiment, "impact": item.impact,
                "confidence": item.confidence, "first_seen_at": item.first_seen_at,
            })
    return {"news": items, "limit": limit, "source": source}
