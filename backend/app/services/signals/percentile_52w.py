"""52-week price percentile: where today's close sits between the 52w low and high.

Score interpretation: 0 = at 52w low, 100 = at 52w high. We use the
momentum/breakout convention — stocks near their 52w highs score high. This
agrees in direction with momentum_50d (so it reinforces rather than fights it)
but uses a much longer reference window, so it catches stocks breaking out of
a multi-year range that 50d momentum alone would miss.

Has full historical backdata since it only needs the trailing-year price window
from PriceHistory. Confidence is 1.0 once we have a year of data.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import PriceHistory, Stock
from app.services.signals.base import SignalResult, clip, empty_result

WINDOW_TRADING_DAYS = 252  # ~1 calendar year of trading days
MIN_DAYS = 60  # below this, signal is unreliable


class Percentile52wSignal:
    name = "percentile_52w"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        q = db.query(PriceHistory).filter(PriceHistory.stock_id == stock.id)
        if as_of is not None:
            q = q.filter(PriceHistory.trade_date <= as_of)
        rows = q.order_by(desc(PriceHistory.trade_date)).limit(WINDOW_TRADING_DAYS).all()

        if len(rows) < MIN_DAYS:
            return empty_result(f"only {len(rows)} days of history (need {MIN_DAYS}+)")

        closes = [r.close for r in rows]
        latest = closes[0]
        lo, hi = min(closes), max(closes)
        if hi <= lo:
            return empty_result("flat-range 52w window (hi == lo)")

        percentile = (latest - lo) / (hi - lo)
        score = clip(percentile * 100.0)
        # Confidence ramps from MIN_DAYS to full WINDOW_TRADING_DAYS.
        confidence = min(1.0, (len(rows) - MIN_DAYS) / (WINDOW_TRADING_DAYS - MIN_DAYS))
        confidence = max(confidence, 0.5)  # floor; with 60+ days we trust the read

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "latest_close": round(latest, 2),
                "low_52w": round(lo, 2),
                "high_52w": round(hi, 2),
                "percentile": round(percentile, 2),
                "narrative": (
                    f"Price {latest:.2f} sits at the {int(percentile * 100)}th percentile "
                    f"of its 52w range [{lo:.2f}, {hi:.2f}]. Higher = closer to 52w high = stronger."
                ),
            },
        )
