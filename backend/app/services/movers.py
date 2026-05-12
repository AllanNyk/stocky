"""'Biggest score movers' service.

Surfaces what the model is saying *right now* by comparing each stock's most
recent composite score to its score N days ago. Pure read over existing
DailyScoreSnapshot rows — no new ingestion or computation.

Caveat: as the snapshot history matures from backtest-only (momentum-dominated)
to daily-snapshot accumulation (full 7-signal), score changes will reflect
real model dynamics. In the meantime, large 'movers' values may partly reflect
new signals coming online rather than market dynamics.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import DailyScoreSnapshot, PriceHistory, Stock


def _latest_snapshot_on_or_before(
    db: Session, stock_id: int, on_or_before: date
) -> DailyScoreSnapshot | None:
    return (
        db.query(DailyScoreSnapshot)
        .filter(
            DailyScoreSnapshot.stock_id == stock_id,
            DailyScoreSnapshot.snapshot_date <= on_or_before,
        )
        .order_by(desc(DailyScoreSnapshot.snapshot_date))
        .first()
    )


def _latest_close_dkk(db: Session, stock_id: int) -> float | None:
    last = (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock_id)
        .order_by(desc(PriceHistory.trade_date))
        .first()
    )
    return last.close_dkk if last else None


def movers(db: Session, lookback_days: int = 1, limit: int = 10) -> dict:
    today = date.today()
    target = today - timedelta(days=lookback_days)

    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()

    rows: list[dict] = []
    for s in stocks:
        now = _latest_snapshot_on_or_before(db, s.id, today)
        if now is None:
            continue
        then = _latest_snapshot_on_or_before(db, s.id, target)
        # If `then` is None or the same snapshot as `now`, we have no usable comparison.
        change: float | None
        score_then: float | None
        if then is None or then.id == now.id:
            change = None
            score_then = None
        else:
            change = now.composite_score - then.composite_score
            score_then = then.composite_score
        rows.append({
            "ticker": s.ticker,
            "name": s.name,
            "sector": s.sector,
            "pluto_tier": s.pluto_tier,
            "country_code": s.country_code,
            "score_now": round(now.composite_score, 2),
            "score_then": round(score_then, 2) if score_then is not None else None,
            "change": round(change, 2) if change is not None else None,
            "snapshot_date_now": now.snapshot_date.isoformat(),
            "snapshot_date_then": then.snapshot_date.isoformat() if then is not None and then.id != now.id else None,
            "last_close_dkk": _latest_close_dkk(db, s.id),
        })

    top_picks = sorted(rows, key=lambda r: r["score_now"], reverse=True)[:limit]
    rows_with_change = [r for r in rows if r["change"] is not None]
    risers = sorted(rows_with_change, key=lambda r: r["change"], reverse=True)[:limit]
    fallers = sorted(rows_with_change, key=lambda r: r["change"])[:limit]

    return {
        "lookback_days": lookback_days,
        "to_date": today.isoformat(),
        "from_date": target.isoformat(),
        "comparable_count": len(rows_with_change),
        "total_count": len(rows),
        "top_picks": top_picks,
        "risers": risers,
        "fallers": fallers,
    }
