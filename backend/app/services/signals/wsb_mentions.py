"""WSB mention-delta signal: today's mentions vs 7-day baseline.

Stocks getting unusual Reddit attention right now score high. The sign of the score
isn't a directional bet — it captures *attention*, and the user/model has to decide
whether attention is bullish (FOMO rallies) or bearish (overbought tops). For Phase 2
we score attention spikes positively; users can reweight in scoring config later.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import RedditMentionCount, Stock
from app.services.signals.base import SignalResult, clip, empty_result

BASELINE_DAYS = 7
MIN_TOTAL_MENTIONS_FOR_CONFIDENCE = 5  # if 7d+today total < this, confidence is 0


class WsbMentionDeltaSignal:
    name = "wsb_mention_delta"

    def compute(self, db: Session, stock: Stock) -> SignalResult:
        # Most recent mention row (today's if scraper ran, else most recent past).
        latest = (
            db.query(RedditMentionCount)
            .filter(RedditMentionCount.stock_id == stock.id)
            .order_by(desc(RedditMentionCount.mention_date))
            .first()
        )
        if latest is None:
            return empty_result("no reddit mention data yet — run /api/admin/refresh-reddit")

        baseline_start = latest.mention_date - timedelta(days=BASELINE_DAYS)
        baseline_rows = (
            db.query(RedditMentionCount)
            .filter(
                RedditMentionCount.stock_id == stock.id,
                RedditMentionCount.mention_date >= baseline_start,
                RedditMentionCount.mention_date < latest.mention_date,
            )
            .all()
        )
        baseline_total = sum(r.count for r in baseline_rows)
        baseline_avg = baseline_total / BASELINE_DAYS  # divide by full window, not row count

        total_window = baseline_total + latest.count
        if total_window < MIN_TOTAL_MENTIONS_FOR_CONFIDENCE:
            return SignalResult(
                score=50.0,
                confidence=0.0,
                evidence={
                    "today_mentions": latest.count,
                    "baseline_avg": round(baseline_avg, 2),
                    "narrative": f"Only {total_window} mentions in last {BASELINE_DAYS + 1} days — too quiet to score.",
                },
            )

        # Smoothed ratio so a 0-baseline doesn't divide by zero. delta in [0, ~4]+.
        ratio = latest.count / (baseline_avg + 1.0)

        # Map ratio: 1.0 (normal attention) -> 50; 3.0+ (3x baseline) -> 100; 0 -> ~30.
        score = clip(35.0 + ratio * 22.0)

        # Confidence ramps with total sample size up to a cap.
        confidence = min(1.0, total_window / 20.0)

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "today_mentions": latest.count,
                "baseline_avg_per_day": round(baseline_avg, 2),
                "ratio_vs_baseline": round(ratio, 2),
                "subreddits": latest.subreddits_seen or "",
                "narrative": (
                    f"{latest.count} mentions today vs {baseline_avg:.1f}/day baseline "
                    f"({ratio:.1f}x). Higher = stronger Reddit attention."
                ),
            },
        )
