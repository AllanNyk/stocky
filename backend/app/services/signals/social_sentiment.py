"""Social-sentiment signal: StockTwits Bullish/Bearish user tags.

Score map: bullish_ratio (= bull / (bull + bear)) is in [0, 1]; we scale linearly
to [0, 100]. Confidence scales with the number of explicitly-tagged messages —
StockTwits's free tier returns ~30 recent messages and usually 5-15 are tagged.

Untagged messages don't influence direction but they do reflect attention, so
we'll factor total message volume in later; for v1 we keep it simple.

US-only by data design (StockTwits coverage). Non-US tickers return confidence 0.
Historical backdata: yes if we've been scraping for several days (the score reads
the most recent row at or before `as_of`).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Stock, StockTwitsActivity
from app.services.signals.base import SignalResult, clip, empty_result

MIN_TAGGED_FOR_CONFIDENCE = 3


class SocialSentimentSignal:
    name = "social_sentiment"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        if stock.country_code != "US":
            return empty_result("StockTwits coverage is US-only; confidence 0 elsewhere")

        q = db.query(StockTwitsActivity).filter(StockTwitsActivity.stock_id == stock.id)
        if as_of is not None:
            q = q.filter(StockTwitsActivity.score_date <= as_of)
        row = q.order_by(desc(StockTwitsActivity.score_date)).first()
        if row is None:
            return empty_result("no StockTwits data — run /api/admin/refresh-stocktwits")

        tagged = row.bullish_count + row.bearish_count
        if tagged < MIN_TAGGED_FOR_CONFIDENCE:
            return SignalResult(
                score=50.0,
                confidence=0.0,
                evidence={
                    "score_date": row.score_date.isoformat(),
                    "total_messages": row.total_messages,
                    "bullish": row.bullish_count,
                    "bearish": row.bearish_count,
                    "narrative": f"Only {tagged} tagged message(s) — not enough to score.",
                },
            )

        bullish_ratio = row.bullish_count / tagged
        score = clip(bullish_ratio * 100.0)
        confidence = min(1.0, tagged / 12.0)

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "score_date": row.score_date.isoformat(),
                "total_messages": row.total_messages,
                "bullish": row.bullish_count,
                "bearish": row.bearish_count,
                "bullish_ratio": round(bullish_ratio, 2),
                "top_message": row.top_message,
                "top_message_sentiment": row.top_message_sentiment,
                "narrative": (
                    f"{row.bullish_count} bullish vs {row.bearish_count} bearish tags "
                    f"({int(bullish_ratio * 100)}% bullish) across {row.total_messages} "
                    f"recent StockTwits messages."
                ),
            },
        )
