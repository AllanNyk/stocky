"""Daily FX rates to DKK. Pulled from yfinance currency pairs."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import yfinance as yf
from sqlalchemy.orm import Session

from app.models import FxRate

YF_PAIRS = {
    "USD": "USDDKK=X",
    "EUR": "EURDKK=X",
    "SEK": "SEKDKK=X",
    "NOK": "NOKDKK=X",
}


def _latest_close(yf_ticker: str) -> tuple[date, float] | None:
    hist = yf.Ticker(yf_ticker).history(period="5d", auto_adjust=False)
    if hist.empty:
        return None
    last = hist.iloc[-1]
    return last.name.date(), float(last["Close"])


def refresh_fx_rates(db: Session) -> dict[str, float]:
    """Upsert today's DKK rate for each supported currency. Returns {currency: rate}.

    DKK is always 1.0 and stored as a sentinel so portfolio code can look it up uniformly.
    """
    today = date.today()
    rates: dict[str, float] = {"DKK": 1.0}

    dkk_row = db.query(FxRate).filter(FxRate.currency == "DKK", FxRate.rate_date == today).one_or_none()
    if dkk_row is None:
        db.add(FxRate(currency="DKK", rate_date=today, to_dkk=1.0))
    else:
        dkk_row.to_dkk = 1.0

    for currency, pair in YF_PAIRS.items():
        result = _latest_close(pair)
        if result is None:
            continue
        rate_date, rate = result
        existing = db.query(FxRate).filter(FxRate.currency == currency, FxRate.rate_date == rate_date).one_or_none()
        if existing is None:
            db.add(FxRate(currency=currency, rate_date=rate_date, to_dkk=rate))
        else:
            existing.to_dkk = rate
        rates[currency] = rate

    db.commit()
    return rates


def latest_rate(db: Session, currency: str) -> float:
    """Most recent known DKK rate for `currency`. Raises if none in DB."""
    if currency == "DKK":
        return 1.0
    row = (
        db.query(FxRate)
        .filter(FxRate.currency == currency)
        .order_by(FxRate.rate_date.desc())
        .first()
    )
    if row is None:
        raise ValueError(f"no FX rate for {currency} — run refresh_fx_rates first")
    return row.to_dkk
