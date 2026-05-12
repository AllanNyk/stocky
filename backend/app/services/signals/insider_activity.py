"""Insider-activity signal: 30-day net insider buying vs selling.

Conventional reading: net insider buying = bullish ("they know something good
coming"), net selling = neutral-to-bearish (could be just diversification or
liquidity, so weaker signal in the negative direction). Score map:

- net_value_usd > 0 (net buying)  -> map to [50, 100] by log of $ amount
- net_value_usd < 0 (net selling) -> map to [25, 50]
- exactly 0 (no signed activity) -> 50

Confidence ramps with txn_count up to a cap. Finnhub only covers US filings
well, so country_code != 'US' returns confidence 0.
"""

from __future__ import annotations

import math
from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import InsiderActivityScore, Stock
from app.services.signals.base import SignalResult, clip, empty_result


class InsiderActivitySignal:
    name = "insider_activity"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        if stock.country_code != "US":
            return empty_result("Finnhub insider data is US-only; confidence 0 elsewhere")

        q = db.query(InsiderActivityScore).filter(InsiderActivityScore.stock_id == stock.id)
        if as_of is not None:
            q = q.filter(InsiderActivityScore.score_date <= as_of)
        row = q.order_by(desc(InsiderActivityScore.score_date)).first()
        if row is None:
            return empty_result("no insider data — run /api/admin/refresh-insider")
        if row.txn_count == 0:
            return SignalResult(
                score=50.0,
                confidence=0.0,
                evidence={"txn_count": 0, "narrative": "No insider transactions in the last 30 days."},
            )

        val = row.net_value_usd
        if val == 0:
            score = 50.0
        elif val > 0:
            # 50 -> 100 as net buying scales from $0 to ~$10M (log scale).
            score = clip(50.0 + 50.0 * min(1.0, math.log10(val + 1) / 7.0))
        else:
            # 50 -> 25 as net selling scales from $0 to ~$10M. Half-strength vs buying.
            score = clip(50.0 - 25.0 * min(1.0, math.log10(-val + 1) / 7.0))

        confidence = min(1.0, row.txn_count / 5.0)
        direction = "buying" if val > 0 else ("selling" if val < 0 else "balanced")
        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "score_date": row.score_date.isoformat(),
                "window_days": row.window_days,
                "txn_count": row.txn_count,
                "net_share_change": round(row.net_share_change, 0),
                "net_value_usd": round(val, 0),
                "narrative": (
                    f"{row.txn_count} insider filing(s) in the last {row.window_days}d, "
                    f"net {direction} {abs(val):,.0f} USD."
                ),
            },
        )
