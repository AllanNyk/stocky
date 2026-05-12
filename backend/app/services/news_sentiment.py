"""News sentiment ingestion: yfinance per-ticker headlines -> VADER -> daily aggregate.

yfinance.Ticker.news returns ~10 recent items per ticker, each with `content.title`
and `content.pubDate` (ISO timestamp). VADER (https://github.com/cjhutto/vaderSentiment)
is a lexicon-based sentiment model — no ML download, no API key, no per-request cost —
that returns a `compound` score in [-1, +1]. Negative = bearish tone, positive = bullish.

For each stock we keep only the items published in the last `WINDOW_HOURS` window,
score each headline, average them, and persist mean + sample_size + the most extreme
headline (so the UI can show "what's driving this number").
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from logging import getLogger
from typing import Any

import yfinance as yf
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.models import NewsSentimentScore, Stock

log = getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()

WINDOW_HOURS = 36  # forgiving: covers weekends + Nordic low-volume tickers


def _parse_pubdate(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _score_stock(stock: Stock, cutoff: datetime) -> dict | None:
    try:
        raw_news = yf.Ticker(stock.ticker).news or []
    except Exception as e:
        log.warning("news fetch failed for %s: %s", stock.ticker, e)
        return None

    headlines: list[tuple[str, float, datetime]] = []
    for item in raw_news:
        content = item.get("content") if isinstance(item, dict) else None
        content = content if isinstance(content, dict) else item if isinstance(item, dict) else {}
        title = (content.get("title") or "").strip()
        if not title:
            continue
        pub = _parse_pubdate(content.get("pubDate") or content.get("providerPublishTime") or content.get("displayTime"))
        if pub is None or pub < cutoff:
            continue
        compound = _analyzer.polarity_scores(title)["compound"]
        headlines.append((title, compound, pub))

    if not headlines:
        return {"mean_compound": 0.0, "sample_size": 0, "top_headline": None, "top_headline_score": None}

    scores = [h[1] for h in headlines]
    mean = sum(scores) / len(scores)
    top = max(headlines, key=lambda h: abs(h[1]))  # most extreme regardless of sign
    return {
        "mean_compound": mean,
        "sample_size": len(headlines),
        "top_headline": top[0][:400],
        "top_headline_score": top[1],
    }


def refresh_news_sentiment(db: Session, score_date: date | None = None) -> dict:
    """Pull last `WINDOW_HOURS` of headlines per non-benchmark stock; persist daily aggregate."""
    today = score_date or date.today()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()

    nonzero = 0
    total_headlines = 0
    failures = 0
    for stock in stocks:
        agg = _score_stock(stock, cutoff)
        if agg is None:
            failures += 1
            continue
        if agg["sample_size"] > 0:
            nonzero += 1
            total_headlines += agg["sample_size"]
        existing = (
            db.query(NewsSentimentScore)
            .filter(NewsSentimentScore.stock_id == stock.id, NewsSentimentScore.score_date == today)
            .one_or_none()
        )
        if existing is None:
            db.add(NewsSentimentScore(
                stock_id=stock.id,
                score_date=today,
                mean_compound=agg["mean_compound"],
                sample_size=agg["sample_size"],
                top_headline=agg["top_headline"],
                top_headline_score=agg["top_headline_score"],
            ))
        else:
            existing.mean_compound = agg["mean_compound"]
            existing.sample_size = agg["sample_size"]
            existing.top_headline = agg["top_headline"]
            existing.top_headline_score = agg["top_headline_score"]
    db.commit()

    return {
        "score_date": today.isoformat(),
        "stocks_scanned": len(stocks),
        "stocks_with_news": nonzero,
        "total_headlines": total_headlines,
        "fetch_failures": failures,
    }
