"""Volume momentum: last-5d average volume vs last-50d average volume.

A volume spike usually precedes or accompanies meaningful price moves — institutions
re-positioning, news driving retail flow, breakouts on real interest. Quiet days don't
score either way (we sit near 50). We don't directionally interpret volume (a spike
could be a buying climax or a selling capitulation), so a 'high' score here just means
'something is happening', and the user should weigh it alongside the directional
signals (momentum_50d, percentile_52w).

Full historical backdata: PriceHistory carries volume, so this works in backtests.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import PriceHistory, Stock
from app.services.signals.base import SignalResult, clip, empty_result

RECENT_DAYS = 5
BASELINE_DAYS = 50


class VolumeMomentumSignal:
    name = "volume_momentum"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        q = db.query(PriceHistory).filter(PriceHistory.stock_id == stock.id)
        if as_of is not None:
            q = q.filter(PriceHistory.trade_date <= as_of)
        rows = q.order_by(desc(PriceHistory.trade_date)).limit(BASELINE_DAYS).all()
        if len(rows) < BASELINE_DAYS:
            return empty_result(f"only {len(rows)} days of history (need {BASELINE_DAYS})")

        volumes = [r.volume for r in rows if r.volume is not None]
        if len(volumes) < BASELINE_DAYS:
            return empty_result("missing volume data on too many days")

        recent_avg = sum(volumes[:RECENT_DAYS]) / RECENT_DAYS
        baseline_avg = sum(volumes) / BASELINE_DAYS
        if baseline_avg <= 0:
            return empty_result("zero baseline volume")

        ratio = recent_avg / baseline_avg  # 1.0 = normal, >1 = spike, <1 = quiet

        # Map ratio: 1.0 -> 50; 2.5x baseline -> 100; 0.5x -> 25.
        score = clip(50.0 + (ratio - 1.0) * 33.0)

        return SignalResult(
            score=score,
            confidence=1.0,
            evidence={
                "recent_5d_avg_volume": int(recent_avg),
                "baseline_50d_avg_volume": int(baseline_avg),
                "ratio": round(ratio, 2),
                "narrative": (
                    f"5d avg volume is {ratio:.1f}x the 50d baseline. "
                    f"Higher = unusual attention (direction-agnostic)."
                ),
            },
        )
