"""Stock browse + score endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DailyScoreSnapshot, NewsSentimentScore, PriceHistory, Stock
from app.services.scoring import score_stock

router = APIRouter(prefix="/api", tags=["stocks"])


def _last_close_payload(db: Session, stock: Stock) -> dict:
    last = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock.id)
        .order_by(desc(PriceHistory.trade_date))
        .first()
    )
    prev = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock.id)
        .order_by(desc(PriceHistory.trade_date))
        .offset(1)
        .first()
    )
    change_pct = None
    if last and prev and prev.close:
        change_pct = (last.close - prev.close) / prev.close * 100.0
    return {
        "last_close": last.close if last else None,
        "last_close_dkk": last.close_dkk if last else None,
        "last_trade_date": last.trade_date.isoformat() if last else None,
        "day_change_pct": round(change_pct, 2) if change_pct is not None else None,
    }


@router.get("/stocks")
def list_stocks(include_benchmarks: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    q = db.query(Stock)
    if not include_benchmarks:
        q = q.filter(Stock.is_benchmark.is_(False))
    stocks = q.order_by(Stock.ticker).all()
    payload = []
    for s in stocks:
        last = _last_close_payload(db, s)
        payload.append({
            "ticker": s.ticker,
            "name": s.name,
            "exchange": s.exchange,
            "currency": s.currency,
            "sector": s.sector,
            "country_code": s.country_code,
            "pluto_tier": s.pluto_tier,
            "is_benchmark": s.is_benchmark,
            "pe_ratio": s.pe_ratio,
            "market_cap": s.market_cap,
            **last,
        })
    return payload


@router.get("/stocks/{ticker}")
def stock_detail(ticker: str, db: Session = Depends(get_db)) -> dict:
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    last = _last_close_payload(db, stock)
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "exchange": stock.exchange,
        "currency": stock.currency,
        "sector": stock.sector,
        "country_code": stock.country_code,
        "pluto_tier": stock.pluto_tier,
        "is_benchmark": stock.is_benchmark,
        "pe_ratio": stock.pe_ratio,
        "market_cap": stock.market_cap,
        **last,
    }


@router.get("/stocks/{ticker}/history")
def stock_history(ticker: str, days: int = 180, db: Session = Depends(get_db)) -> list[dict]:
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    cutoff = date.today() - timedelta(days=days + 5)
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock.id, PriceHistory.trade_date >= cutoff)
        .order_by(PriceHistory.trade_date)
        .all()
    )
    return [
        {
            "date": r.trade_date.isoformat(),
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "close_dkk": r.close_dkk,
            "volume": r.volume,
        }
        for r in rows
    ]


@router.get("/stocks/{ticker}/score")
def stock_score(ticker: str, db: Session = Depends(get_db)) -> dict:
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    return score_stock(db, stock)


@router.get("/stocks/{ticker}/score-history")
def stock_score_history(ticker: str, days: int = 90, db: Session = Depends(get_db)) -> list[dict]:
    """Composite score per snapshot date for this stock — used for the detail-page sparkline."""
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    cutoff = date.today() - timedelta(days=days + 1)
    rows = (
        db.query(DailyScoreSnapshot)
        .filter(
            DailyScoreSnapshot.stock_id == stock.id,
            DailyScoreSnapshot.snapshot_date >= cutoff,
        )
        .order_by(DailyScoreSnapshot.snapshot_date)
        .all()
    )
    return [
        {
            "date": r.snapshot_date.isoformat(),
            "composite_score": round(r.composite_score, 2),
            "price_at_snapshot_dkk": r.price_at_snapshot_dkk,
        }
        for r in rows
    ]


@router.get("/stocks/{ticker}/news-timeline")
def stock_news_timeline(ticker: str, days: int = 90, db: Session = Depends(get_db)) -> list[dict]:
    """Daily news-sentiment aggregates with the day's top (most-extreme) headline.

    Used by the stock-detail page to overlay news markers on the price chart so the
    user can see whether sentiment moved before / with / after price changes.
    """
    stock = db.query(Stock).filter(Stock.ticker == ticker).one_or_none()
    if stock is None:
        raise HTTPException(404, f"unknown ticker {ticker!r}")
    cutoff = date.today() - timedelta(days=days + 1)
    rows = (
        db.query(NewsSentimentScore)
        .filter(
            NewsSentimentScore.stock_id == stock.id,
            NewsSentimentScore.score_date >= cutoff,
            NewsSentimentScore.sample_size > 0,
        )
        .order_by(NewsSentimentScore.score_date)
        .all()
    )
    return [
        {
            "date": r.score_date.isoformat(),
            "mean_compound": round(r.mean_compound, 3),
            "sample_size": r.sample_size,
            "top_headline": r.top_headline,
            "top_headline_score": (
                round(r.top_headline_score, 3) if r.top_headline_score is not None else None
            ),
        }
        for r in rows
    ]


@router.get("/scores")
def all_scores(db: Session = Depends(get_db)) -> list[dict]:
    """Composite score for every non-benchmark stock. Used for sorting the market list."""
    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).order_by(Stock.ticker).all()
    return [score_stock(db, s) for s in stocks]
