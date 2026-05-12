"""News-sentiment signal: rolling VADER compound score across recent headlines.

We don't have historical news scrapes (yfinance.Ticker.news only returns *current*
news), so for backtests this returns confidence=0. Live scoring uses the most recent
row in NewsSentimentScore, plus any scores in the trailing 5 days as a sanity-check
sample-size boost — a 1-headline day in isolation isn't very informative.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import NewsSentimentScore, Stock
from app.services.signals.base import SignalResult, clip, empty_result

LOOKBACK_DAYS = 5
MIN_HEADLINES_FOR_CONFIDENCE = 3


class NewsSentimentSignal:
    name = "news_sentiment"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        if as_of is not None:
            return empty_result("no historical news backdata — confidence 0 for backtests")

        latest = (
            db.query(NewsSentimentScore)
            .filter(NewsSentimentScore.stock_id == stock.id)
            .order_by(desc(NewsSentimentScore.score_date))
            .first()
        )
        if latest is None:
            return empty_result("no news sentiment data yet — run /api/admin/refresh-news")

        # Pool the last few days for a more stable read on quiet tickers.
        window_start = latest.score_date - timedelta(days=LOOKBACK_DAYS - 1)
        window = (
            db.query(NewsSentimentScore)
            .filter(
                NewsSentimentScore.stock_id == stock.id,
                NewsSentimentScore.score_date >= window_start,
                NewsSentimentScore.score_date <= latest.score_date,
            )
            .all()
        )
        total_headlines = sum(r.sample_size for r in window)

        if total_headlines < MIN_HEADLINES_FOR_CONFIDENCE:
            return SignalResult(
                score=50.0,
                confidence=0.0,
                evidence={
                    "headlines_in_window": total_headlines,
                    "narrative": f"Only {total_headlines} headlines in last {LOOKBACK_DAYS} days — too quiet to score.",
                },
            )

        # Sample-size weighted mean of compound scores in the window.
        weighted_sum = sum(r.mean_compound * r.sample_size for r in window)
        pooled_mean = weighted_sum / total_headlines  # in [-1, +1]

        # Map -1..+1 -> 0..100. Strong positive coverage = bullish score.
        score = clip(50.0 + pooled_mean * 50.0)

        # Confidence ramps up with sample size, capping around ~15 headlines.
        confidence = min(1.0, total_headlines / 15.0)

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "pooled_mean_compound": round(pooled_mean, 3),
                "headlines_in_window": total_headlines,
                "lookback_days": LOOKBACK_DAYS,
                "top_headline": latest.top_headline,
                "top_headline_score": (
                    round(latest.top_headline_score, 3) if latest.top_headline_score is not None else None
                ),
                "narrative": (
                    f"Pooled compound {pooled_mean:+.2f} across {total_headlines} headlines "
                    f"(last {LOOKBACK_DAYS}d). Positive = bullish news tone."
                ),
            },
        )
