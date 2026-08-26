"""Deterministic enrichment for RSS news; no LLM guesses are involved."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re


@dataclass(frozen=True)
class NewsEnrichment:
    assets: tuple[str, ...]
    event_type: str
    sentiment: str
    impact: str
    confidence: float


_ASSETS = {"BTC": "BTC", "BITCOIN": "BTC", "ETH": "ETH", "ETHEREUM": "ETH", "SOL": "SOL", "SOLANA": "SOL", "BNB": "BNB", "XRP": "XRP"}
_EVENT_TERMS = {"approval": ("ETF", "regulatory"), "hack": ("SECURITY", "security"), "lawsuit": ("REGULATION", "regulatory"), "upgrade": ("PROTOCOL", "technology"), "listing": ("LISTING", "market")}


def enrich_news(title: str, summary: str = "", published_at: datetime | None = None) -> NewsEnrichment:
    text = f"{title} {summary}".lower()
    assets = tuple(sorted({asset for token, asset in _ASSETS.items() if re.search(rf"\b{re.escape(token.lower())}\b", text)}))
    event_type, _ = next(((value[0], value[1]) for term, value in _EVENT_TERMS.items() if term in text), ("GENERAL", "market"))
    positive = sum(word in text for word in ("surge", "gain", "approval", "rally", "growth"))
    negative = sum(word in text for word in ("fall", "hack", "lawsuit", "loss", "ban"))
    sentiment = "POSITIVE" if positive > negative else "NEGATIVE" if negative > positive else "NEUTRAL"
    impact = "HIGH" if event_type != "GENERAL" or max(positive, negative) >= 2 else "MEDIUM" if positive or negative else "LOW"
    confidence = 0.9 if assets and event_type != "GENERAL" else 0.7 if assets or event_type != "GENERAL" else 0.5
    return NewsEnrichment(assets, event_type, sentiment, impact, confidence)
