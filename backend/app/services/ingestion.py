"""Price + fundamentals ingestion via yfinance.

`refresh_all_prices` is idempotent — safe to run repeatedly. Pulls OHLCV for the last N
trading days and upserts into PriceHistory, then updates the Stock row's fundamentals.
Each row's `close_dkk` is computed at ingest time using the latest FX rate so historical
FX moves don't retroactively change past portfolio values.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger

import yfinance as yf
from sqlalchemy.orm import Session

from app.models import PriceHistory, Stock
from app.services.fx import latest_rate, refresh_fx_rates

log = getLogger(__name__)


def _upsert_price_row(db: Session, stock: Stock, row, fx_to_dkk: float) -> bool:
    trade_date = row.name.date()
    close = float(row["Close"])
    existing = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock.id, PriceHistory.trade_date == trade_date)
        .one_or_none()
    )
    if existing is None:
        db.add(PriceHistory(
            stock_id=stock.id,
            trade_date=trade_date,
            open=float(row["Open"]) if row["Open"] == row["Open"] else None,
            high=float(row["High"]) if row["High"] == row["High"] else None,
            low=float(row["Low"]) if row["Low"] == row["Low"] else None,
            close=close,
            volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
            close_dkk=close * fx_to_dkk,
        ))
        return True
    return False


def refresh_prices_for_stock(db: Session, stock: Stock, period: str = "1y") -> int:
    """Pull `period` of daily OHLCV for one stock, upsert new rows, update fundamentals."""
    ticker = yf.Ticker(stock.ticker)
    hist = ticker.history(period=period, auto_adjust=False)
    if hist.empty:
        log.warning("no yfinance data for %s", stock.ticker)
        return 0

    try:
        fx = latest_rate(db, stock.currency)
    except ValueError:
        refresh_fx_rates(db)
        fx = latest_rate(db, stock.currency)

    new_rows = 0
    for _, row in hist.iterrows():
        if _upsert_price_row(db, stock, row, fx):
            new_rows += 1

    if not stock.is_benchmark:
        try:
            info = ticker.info or {}
            stock.pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            stock.market_cap = info.get("marketCap")
            stock.fundamentals_updated_at = datetime.utcnow()
        except Exception as e:
            log.warning("fundamentals fetch failed for %s: %s", stock.ticker, e)

    db.commit()
    return new_rows


def refresh_all_prices(db: Session, period: str = "1y") -> dict[str, int]:
    """Refresh every stock in the universe. Returns per-ticker count of newly inserted rows."""
    refresh_fx_rates(db)
    results: dict[str, int] = {}
    stocks = db.query(Stock).all()
    for stock in stocks:
        try:
            results[stock.ticker] = refresh_prices_for_stock(db, stock, period=period)
        except Exception as e:
            log.error("price refresh failed for %s: %s", stock.ticker, e)
            results[stock.ticker] = -1
    return results
