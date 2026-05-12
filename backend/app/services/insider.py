"""Finnhub insider-transactions ingestion.

Finnhub's free tier covers SEC Form 4 filings well for US stocks; Nordic coverage is
thin (different regulatory regime). The signal will primarily contribute on US names.

For each stock we pull insider transactions in the trailing 30 days, sum
shares_bought - shares_sold, and persist net share count + signed dollar value +
transaction count. The signal in services/signals/insider_activity.py reads this and
maps net activity to a 0-100 score, scaled by stock float / market cap.

Free tier limits: 60 calls/minute, 30 calls/second. We sleep 1.2s between requests.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from logging import getLogger

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import InsiderActivityScore, Stock

log = getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
INTER_REQUEST_DELAY_SEC = 1.2
WINDOW_DAYS = 30


def _fetch_insider_transactions(symbol: str) -> list[dict] | None:
    """Returns Finnhub's `/stock/insider-transactions` payload data, or None on error."""
    end = date.today()
    start = end - timedelta(days=WINDOW_DAYS)
    try:
        r = httpx.get(
            f"{FINNHUB_BASE}/stock/insider-transactions",
            params={
                "symbol": symbol,
                "from": start.isoformat(),
                "to": end.isoformat(),
                "token": settings.finnhub_api_key,
            },
            timeout=20,
        )
    except httpx.HTTPError as e:
        log.warning("finnhub %s network error: %s", symbol, e)
        return None
    if r.status_code == 429:
        log.warning("finnhub %s rate-limited (429)", symbol)
        return None
    if r.status_code != 200:
        log.warning("finnhub %s -> %s: %s", symbol, r.status_code, r.text[:120])
        return None
    try:
        body = r.json()
    except Exception:
        return None
    return body.get("data") or []


def refresh_insider_activity(db: Session, score_date: date | None = None) -> dict:
    """Pull 30 days of insider txns per stock, persist daily aggregate. Skipped if no key."""
    if not settings.finnhub_enabled:
        return {"skipped": True, "reason": "FINNHUB_API_KEY not configured"}

    today = score_date or date.today()
    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()
    # Finnhub insider coverage is US-only in practice; skip the others to save quota.
    us_stocks = [s for s in stocks if s.country_code == "US"]

    inserted = 0
    updated = 0
    skipped_no_data = 0
    failures: list[str] = []

    for i, stock in enumerate(us_stocks):
        if i > 0:
            time.sleep(INTER_REQUEST_DELAY_SEC)
        txns = _fetch_insider_transactions(stock.ticker)
        if txns is None:
            failures.append(stock.ticker)
            continue
        if not txns:
            skipped_no_data += 1
            continue

        net_shares = 0.0
        net_value = 0.0
        for t in txns:
            # Finnhub returns `change` (signed shares) and `transactionPrice`.
            change = float(t.get("change") or 0)
            price = float(t.get("transactionPrice") or 0)
            net_shares += change
            net_value += change * price

        existing = (
            db.query(InsiderActivityScore)
            .filter(
                InsiderActivityScore.stock_id == stock.id,
                InsiderActivityScore.score_date == today,
            )
            .one_or_none()
        )
        if existing is None:
            db.add(InsiderActivityScore(
                stock_id=stock.id,
                score_date=today,
                window_days=WINDOW_DAYS,
                net_share_change=net_shares,
                net_value_usd=net_value,
                txn_count=len(txns),
            ))
            inserted += 1
        else:
            existing.window_days = WINDOW_DAYS
            existing.net_share_change = net_shares
            existing.net_value_usd = net_value
            existing.txn_count = len(txns)
            updated += 1
    db.commit()

    return {
        "score_date": today.isoformat(),
        "us_stocks_scanned": len(us_stocks),
        "inserted": inserted,
        "updated": updated,
        "skipped_no_data": skipped_no_data,
        "failures": failures,
    }
