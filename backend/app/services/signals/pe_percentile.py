"""P/E percentile vs sector: low P/E relative to peers -> high score (cheap = bullish).

Historical caveat: the Stock table stores only current P/E, not historical. So when
`as_of` is in the past, we'd be using *today's* P/E ratios to score a past date —
that's lookahead. To stay honest, this signal returns confidence=0 for historical
scoring; the composite then falls back to whatever signals do have backdata.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Stock
from app.services.signals.base import SignalResult, clip, empty_result


class PEPercentileSignal:
    name = "pe_percentile"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        if as_of is not None:
            return empty_result("no historical P/E backdata — confidence 0 for backtests")

        if stock.pe_ratio is None or stock.pe_ratio <= 0:
            return empty_result("no positive P/E available")

        peers = (
            db.query(Stock)
            .filter(
                Stock.sector == stock.sector,
                Stock.is_benchmark.is_(False),
                Stock.pe_ratio.isnot(None),
                Stock.pe_ratio > 0,
            )
            .all()
        )
        peer_pes = sorted([p.pe_ratio for p in peers])
        if len(peer_pes) < 3:
            return empty_result(f"only {len(peer_pes)} peers in sector {stock.sector!r}")

        below = sum(1 for p in peer_pes if p < stock.pe_ratio)
        percentile = below / len(peer_pes)  # 0.0 = cheapest, 1.0 = most expensive
        score = clip(100.0 * (1.0 - percentile))
        confidence = min(1.0, len(peer_pes) / 8.0)

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "stock_pe": round(stock.pe_ratio, 2),
                "sector": stock.sector,
                "sector_peer_count": len(peer_pes),
                "sector_median_pe": round(peer_pes[len(peer_pes) // 2], 2),
                "percentile": round(percentile, 2),
                "narrative": (
                    f"P/E {stock.pe_ratio:.1f} is at the {int(percentile * 100)}th "
                    f"percentile of {len(peer_pes)} {stock.sector} peers "
                    f"(lower = cheaper = bullish)."
                ),
            },
        )
