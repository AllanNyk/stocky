"""Daily score snapshot + virtual model portfolio + forward-return computation.

The snapshot job runs once per day after prices ingest. For every tradeable stock it:
  1. Computes the composite score using TODAY's signals.
  2. Persists score + components + price-at-snapshot to `daily_score_snapshots`.
  3. Selects picks under two strategies (top-5 equal weight, threshold>70) and
     persists them to `model_portfolio_picks` so each pick's entry price is locked.

Forward returns are computed on read by joining historical snapshots with later
price history. We never recompute past scores from current data (would leak future info).
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import (
    DailyScoreSnapshot,
    ModelPortfolioPick,
    PickStrategy,
    PriceHistory,
    Stock,
)
from app.services.scoring import score_stock

log = getLogger(__name__)

TOP_N_FOR_TOP5 = 5
THRESHOLD = 70.0


def _latest_close(db: Session, stock_id: int) -> PriceHistory | None:
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock_id)
        .order_by(desc(PriceHistory.trade_date))
        .first()
    )


def _close_as_of(db: Session, stock_id: int, as_of: date) -> PriceHistory | None:
    """Most recent trade at or before `as_of`."""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock_id, PriceHistory.trade_date <= as_of)
        .order_by(desc(PriceHistory.trade_date))
        .first()
    )


def _run_snapshot_for_date(db: Session, snap_date: date, *, historical: bool) -> dict:
    """Core snapshot logic, shared by live (today) and backtest (historical) paths.

    When `historical=True`, signals see only data <= snap_date (via `as_of` plumbing)
    and the entry price comes from the close on or before snap_date. When False,
    signals use latest available data and entry price is the latest close.
    """
    # Wipe any previous run for the same date so re-runs are clean.
    db.query(DailyScoreSnapshot).filter(DailyScoreSnapshot.snapshot_date == snap_date).delete()
    db.query(ModelPortfolioPick).filter(ModelPortfolioPick.snapshot_date == snap_date).delete()
    db.flush()

    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()
    snapshots: list[tuple[Stock, float, dict, float]] = []
    skipped = 0
    as_of = snap_date if historical else None

    for stock in stocks:
        price_row = _close_as_of(db, stock.id, snap_date) if historical else _latest_close(db, stock.id)
        if price_row is None:
            skipped += 1
            continue
        scored = score_stock(db, stock, as_of=as_of)
        composite = scored["composite_score"]
        components = scored["components"]
        db.add(DailyScoreSnapshot(
            stock_id=stock.id,
            snapshot_date=snap_date,
            composite_score=composite,
            component_scores=components,
            price_at_snapshot_dkk=price_row.close_dkk,
        ))
        snapshots.append((stock, composite, components, price_row.close_dkk))

    # Strategy A: top-5 equal weight
    top5 = sorted(snapshots, key=lambda x: x[1], reverse=True)[:TOP_N_FOR_TOP5]
    for stock, score, _comp, price in top5:
        db.add(ModelPortfolioPick(
            snapshot_date=snap_date,
            pick_strategy=PickStrategy.TOP5_EQUAL_WEIGHT.value,
            stock_id=stock.id,
            composite_score=score,
            weight=1.0 / len(top5) if top5 else 0.0,
            entry_price_dkk=price,
        ))

    # Strategy B: every stock above threshold, equal weight
    above = [s for s in snapshots if s[1] >= THRESHOLD]
    weight = (1.0 / len(above)) if above else 0.0
    for stock, score, _comp, price in above:
        db.add(ModelPortfolioPick(
            snapshot_date=snap_date,
            pick_strategy=PickStrategy.THRESHOLD_70.value,
            stock_id=stock.id,
            composite_score=score,
            weight=weight,
            entry_price_dkk=price,
        ))

    db.commit()
    return {
        "snapshot_date": snap_date.isoformat(),
        "scored": len(snapshots),
        "skipped_no_price": skipped,
        "top5_picks": [s[0].ticker for s in top5],
        "threshold_70_picks": [s[0].ticker for s in above],
    }


def run_daily_snapshot(db: Session, snapshot_date: date | None = None) -> dict:
    """Compute + persist today's snapshot using live signals. Idempotent."""
    return _run_snapshot_for_date(db, snapshot_date or date.today(), historical=False)


def run_backtest(db: Session, days: int = 90) -> dict:
    """Replay the last `days` trading days, computing what the score WOULD have been.

    Only signals with historical backdata contribute (currently momentum_50d). P/E and
    WSB signals return confidence=0 for past dates, so the composite is honest about
    what could actually have been known. Useful to populate the validation dashboard
    with realistic-looking history instead of waiting weeks for it to fill in.
    """
    today = date.today()
    start = today - timedelta(days=days)
    log.info("backtest start: %s -> %s (%d days)", start, today, days)

    # Iterate over the actual trading days we have prices for any stock. Easiest:
    # take the union of dates from PriceHistory in the window.
    trading_days = sorted({
        row.trade_date
        for row in db.query(PriceHistory.trade_date)
        .filter(PriceHistory.trade_date >= start, PriceHistory.trade_date <= today)
        .distinct()
        .all()
    })

    results: list[dict] = []
    for d in trading_days:
        try:
            results.append(_run_snapshot_for_date(db, d, historical=True))
        except Exception as e:
            log.exception("backtest day %s failed: %s", d, e)

    return {
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "trading_days_processed": len(results),
        "total_picks_top5": sum(len(r["top5_picks"]) for r in results),
        "total_picks_threshold_70": sum(len(r["threshold_70_picks"]) for r in results),
    }


def _price_on_or_after(db: Session, stock_id: int, target: date) -> PriceHistory | None:
    """Closest trading-day close on or after `target`. None if target is in the future."""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.stock_id == stock_id, PriceHistory.trade_date >= target)
        .order_by(PriceHistory.trade_date.asc())
        .first()
    )


def forward_returns_for_strategy(db: Session, strategy: str, horizons_days: list[int]) -> dict:
    """Aggregate stats per horizon across every historical pick of `strategy`.

    For each pick: compare entry_price_dkk vs close on or after (snapshot_date + horizon).
    Returns hit rate and average return per horizon.
    """
    picks = (
        db.query(ModelPortfolioPick)
        .filter(ModelPortfolioPick.pick_strategy == strategy)
        .order_by(ModelPortfolioPick.snapshot_date)
        .all()
    )
    per_horizon: dict[int, dict] = {}
    for h in horizons_days:
        returns: list[float] = []
        hits = 0
        for pick in picks:
            future_price = _price_on_or_after(db, pick.stock_id, pick.snapshot_date + timedelta(days=h))
            if future_price is None or future_price.trade_date <= pick.snapshot_date:
                continue
            r = (future_price.close_dkk - pick.entry_price_dkk) / pick.entry_price_dkk
            returns.append(r)
            if r > 0:
                hits += 1
        per_horizon[h] = {
            "horizon_days": h,
            "sample_size": len(returns),
            "avg_return_pct": round((sum(returns) / len(returns) * 100), 2) if returns else None,
            "hit_rate": round(hits / len(returns), 3) if returns else None,
        }
    return {"strategy": strategy, "total_picks": len(picks), "per_horizon": per_horizon}


def latest_top_picks(db: Session, strategy: str) -> list[dict]:
    """Most-recent snapshot's picks with their realized return so far."""
    latest_pick = (
        db.query(ModelPortfolioPick)
        .filter(ModelPortfolioPick.pick_strategy == strategy)
        .order_by(desc(ModelPortfolioPick.snapshot_date))
        .first()
    )
    if latest_pick is None:
        return []
    latest_date = latest_pick.snapshot_date
    picks = (
        db.query(ModelPortfolioPick)
        .filter(
            ModelPortfolioPick.pick_strategy == strategy,
            ModelPortfolioPick.snapshot_date == latest_date,
        )
        .all()
    )
    out: list[dict] = []
    for pick in picks:
        stock = db.query(Stock).get(pick.stock_id)
        current = _latest_close(db, pick.stock_id)
        current_return = None
        if current is not None and pick.entry_price_dkk:
            current_return = (current.close_dkk - pick.entry_price_dkk) / pick.entry_price_dkk * 100
        out.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "snapshot_date": pick.snapshot_date.isoformat(),
            "composite_score": pick.composite_score,
            "weight": pick.weight,
            "entry_price_dkk": pick.entry_price_dkk,
            "current_price_dkk": current.close_dkk if current else None,
            "return_pct": round(current_return, 2) if current_return is not None else None,
        })
    return out
