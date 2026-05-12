"""StockTwits ingestion: per-symbol public message streams.

StockTwits (https://stocktwits.com) is a Twitter-like network where every post is
tagged with one or more $TICKER symbols. Users can mark a post as Bullish or
Bearish via a built-in toggle. That gives us a directly-labeled retail sentiment
stream — better than scraping Reddit, where we'd have to infer sentiment from text.

The public per-symbol endpoint returns ~30 recent messages. It's behind Cloudflare's
anti-bot challenge, so we go through curl_cffi (already a dep, used by yfinance 1.x)
which impersonates Chrome's TLS fingerprint. Free, no API key required.

For each US stock we record:
  - total messages in the response window
  - count of explicitly-Bullish messages
  - count of explicitly-Bearish messages
  - the most-recent tagged message (for the UI)

StockTwits coverage is heavily US-skewed (it's primarily a US retail platform),
so we only call it for US stocks. Nordic names skip out cleanly — the signal
returns confidence 0 there and the composite renormalizes.
"""

from __future__ import annotations

import time
from datetime import date
from logging import getLogger

from curl_cffi import requests as crequests
from sqlalchemy.orm import Session

from app.models import Stock, StockTwitsActivity

log = getLogger(__name__)

API_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
INTER_REQUEST_DELAY_SEC = 1.0  # 200 req/hour rate limit on the public endpoint


def _extract_sentiment(message: dict) -> str | None:
    """Returns 'Bullish', 'Bearish', or None."""
    entities = message.get("entities") or {}
    sentiment = entities.get("sentiment") or {}
    if isinstance(sentiment, dict):
        basic = sentiment.get("basic")
        if basic in ("Bullish", "Bearish"):
            return basic
    # Fallback: some older payloads put sentiment at the top level
    top_level = message.get("sentiment") or {}
    if isinstance(top_level, dict):
        basic = top_level.get("basic")
        if basic in ("Bullish", "Bearish"):
            return basic
    return None


def _fetch_symbol(symbol: str) -> list[dict] | None:
    try:
        r = crequests.get(
            API_URL.format(symbol=symbol),
            impersonate="chrome110",
            timeout=20,
        )
    except Exception as e:
        log.warning("stocktwits %s network error: %s", symbol, e)
        return None
    if r.status_code == 404:
        log.info("stocktwits %s: 404 (no coverage)", symbol)
        return []
    if r.status_code == 429:
        log.warning("stocktwits %s rate-limited (429)", symbol)
        return None
    if r.status_code != 200:
        log.warning("stocktwits %s -> %s", symbol, r.status_code)
        return None
    try:
        body = r.json()
    except Exception as e:
        log.warning("stocktwits %s parse failed: %s", symbol, e)
        return None
    return body.get("messages") or []


def refresh_stocktwits_activity(db: Session, score_date: date | None = None) -> dict:
    """Pull per-symbol streams for every US stock and persist a daily aggregate."""
    today = score_date or date.today()
    stocks = (
        db.query(Stock)
        .filter(Stock.is_benchmark.is_(False), Stock.country_code == "US")
        .all()
    )

    inserted = 0
    updated = 0
    skipped_no_coverage = 0
    failures: list[str] = []
    total_messages_summed = 0
    total_bull = 0
    total_bear = 0

    for i, stock in enumerate(stocks):
        if i > 0:
            time.sleep(INTER_REQUEST_DELAY_SEC)
        msgs = _fetch_symbol(stock.ticker)
        if msgs is None:
            failures.append(stock.ticker)
            continue
        if not msgs:
            skipped_no_coverage += 1
            continue

        bull = 0
        bear = 0
        top_tagged: tuple[str, str] | None = None  # (body, sentiment)
        for m in msgs:
            sentiment = _extract_sentiment(m)
            if sentiment == "Bullish":
                bull += 1
            elif sentiment == "Bearish":
                bear += 1
            if sentiment is not None and top_tagged is None:
                body = (m.get("body") or "").strip()[:400]
                if body:
                    top_tagged = (body, sentiment)

        total_messages_summed += len(msgs)
        total_bull += bull
        total_bear += bear

        existing = (
            db.query(StockTwitsActivity)
            .filter(
                StockTwitsActivity.stock_id == stock.id,
                StockTwitsActivity.score_date == today,
            )
            .one_or_none()
        )
        if existing is None:
            db.add(StockTwitsActivity(
                stock_id=stock.id,
                score_date=today,
                total_messages=len(msgs),
                bullish_count=bull,
                bearish_count=bear,
                top_message=top_tagged[0] if top_tagged else None,
                top_message_sentiment=top_tagged[1] if top_tagged else None,
            ))
            inserted += 1
        else:
            existing.total_messages = len(msgs)
            existing.bullish_count = bull
            existing.bearish_count = bear
            existing.top_message = top_tagged[0] if top_tagged else None
            existing.top_message_sentiment = top_tagged[1] if top_tagged else None
            updated += 1
    db.commit()

    return {
        "score_date": today.isoformat(),
        "us_stocks_scanned": len(stocks),
        "inserted": inserted,
        "updated": updated,
        "skipped_no_coverage": skipped_no_coverage,
        "failures": failures,
        "total_messages": total_messages_summed,
        "total_bullish_tagged": total_bull,
        "total_bearish_tagged": total_bear,
    }
