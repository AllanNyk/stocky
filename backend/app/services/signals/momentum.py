"""50-day momentum: price vs its 50-trading-day moving average."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import PriceHistory, Stock
from app.services.signals.base import Signal, SignalResult, clip, empty_result

LOOKBACK_DAYS = 50


class Momentum50dSignal:
    name = "momentum_50d"

    def compute(self, db: Session, stock: Stock) -> SignalResult:
        rows = (
            db.query(PriceHistory)
            .filter(PriceHistory.stock_id == stock.id)
            .order_by(desc(PriceHistory.trade_date))
            .limit(LOOKBACK_DAYS)
            .all()
        )
        if len(rows) < LOOKBACK_DAYS:
            return empty_result(f"only {len(rows)} days of history (need {LOOKBACK_DAYS})")

        closes = [r.close for r in rows]
        latest = closes[0]
        sma = sum(closes) / len(closes)
        deviation = (latest - sma) / sma  # +0.10 = price 10% above MA

        # Map deviation in [-0.20, +0.20] to score in [0, 100]; clip outside.
        score = clip(50.0 + (deviation / 0.20) * 50.0)

        return SignalResult(
            score=score,
            confidence=1.0,
            evidence={
                "latest_close": round(latest, 2),
                "sma_50d": round(sma, 2),
                "deviation_pct": round(deviation * 100, 2),
                "narrative": (
                    f"Price {latest:.2f} is {deviation * 100:+.1f}% vs 50-day SMA "
                    f"({sma:.2f}). Positive = upward trend."
                ),
            },
        )
