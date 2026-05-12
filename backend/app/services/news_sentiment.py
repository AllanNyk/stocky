"""News sentiment ingestion: yfinance per-ticker headlines -> filter -> VADER -> persist.

Filter step: yfinance.Ticker.news tags articles loosely — a story can be returned
under "AAPL" even when AAPL only appears as a sidebar mention. We drop any
headline whose title doesn't contain the ticker or one of its WSB aliases
(word-boundary, case-insensitive). This is the same alias system the WSB scraper
uses, defined per-stock in seeds/universe.py.

VADER (https://github.com/cjhutto/vaderSentiment) is a lexicon-based model with
no ML download or API cost — compound score in [-1, +1] per headline. We
persist each filtered headline (NewsHeadline) and a daily aggregate
(NewsSentimentScore).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from logging import getLogger
from typing import Any

import yfinance as yf
from sqlalchemy.orm import Session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.models import NewsHeadline, NewsSentimentScore, Stock

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


def _alias_pattern(stock: Stock) -> re.Pattern[str]:
    """Word-boundary regex that matches the ticker or any WSB alias."""
    aliases = (stock.wsb_aliases or stock.ticker).split("|")
    aliases = sorted({a.strip() for a in aliases if a.strip()}, key=len, reverse=True)
    escaped = [re.escape(a) for a in aliases]
    return re.compile(
        r"(?<![A-Za-z0-9_])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )


def _score_stock(db: Session, stock: Stock, cutoff: datetime) -> dict | None:
    try:
        raw_news = yf.Ticker(stock.ticker).news or []
    except Exception as e:
        log.warning("news fetch failed for %s: %s", stock.ticker, e)
        return None

    pattern = _alias_pattern(stock)
    kept: list[tuple[str, str, float, datetime]] = []  # (title, link, compound, pub)
    dropped_loose = 0

    for item in raw_news:
        content = item.get("content") if isinstance(item, dict) else None
        content = content if isinstance(content, dict) else item if isinstance(item, dict) else {}
        title = (content.get("title") or "").strip()
        if not title:
            continue
        pub = _parse_pubdate(content.get("pubDate") or content.get("providerPublishTime") or content.get("displayTime"))
        if pub is None or pub < cutoff:
            continue
        if not pattern.search(title):
            dropped_loose += 1
            continue
        link = ""
        cp = content.get("clickThroughUrl") or content.get("canonicalUrl") or {}
        if isinstance(cp, dict):
            link = cp.get("url") or ""
        link = (link or content.get("link") or "")[:800]
        if not link:
            # Synthesize a unique-ish placeholder so the dedup constraint still works.
            link = f"stocky://{stock.ticker}/{pub.isoformat()}"

        compound = _analyzer.polarity_scores(title)["compound"]
        kept.append((title[:500], link, compound, pub))

    for title, link, compound, pub in kept:
        existing = (
            db.query(NewsHeadline)
            .filter(NewsHeadline.stock_id == stock.id, NewsHeadline.link == link)
            .one_or_none()
        )
        if existing is None:
            db.add(NewsHeadline(
                stock_id=stock.id,
                published_at=pub.astimezone(timezone.utc).replace(tzinfo=None),
                title=title,
                link=link,
                compound_score=compound,
            ))
        else:
            existing.compound_score = compound
            existing.title = title

    if not kept:
        return {
            "mean_compound": 0.0,
            "sample_size": 0,
            "top_headline": None,
            "top_headline_score": None,
            "dropped_loose": dropped_loose,
        }

    scores = [k[2] for k in kept]
    mean = sum(scores) / len(scores)
    top = max(kept, key=lambda k: abs(k[2]))
    return {
        "mean_compound": mean,
        "sample_size": len(kept),
        "top_headline": top[0],
        "top_headline_score": top[2],
        "dropped_loose": dropped_loose,
    }


def refresh_news_sentiment(db: Session, score_date: date | None = None) -> dict:
    """Pull last `WINDOW_HOURS` of headlines per non-benchmark stock; persist headlines + daily aggregate."""
    today = score_date or date.today()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()

    nonzero = 0
    total_headlines = 0
    total_dropped = 0
    failures = 0
    for stock in stocks:
        agg = _score_stock(db, stock, cutoff)
        if agg is None:
            failures += 1
            continue
        if agg["sample_size"] > 0:
            nonzero += 1
            total_headlines += agg["sample_size"]
        total_dropped += agg.get("dropped_loose", 0)
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
        "total_headlines_kept": total_headlines,
        "total_dropped_loose_match": total_dropped,
        "fetch_failures": failures,
    }
