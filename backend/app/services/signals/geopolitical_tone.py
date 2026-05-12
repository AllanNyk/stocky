"""Geopolitical-tone signal: read GDELT mean tone for the stock's home country.

GDELT tone roughly spans [-10, +10]. Empirically the *baseline* news tone in most
countries hovers between -1 and 0 (news skews negative) — full-on crisis days
reach -2 or -3. So we map a tone window of [-3.0, +1.0] to a 0-100 score:
very negative = bearish, slightly positive = bullish. Confidence scales with the
number of hourly samples that fed today's mean.

Has historical backdata: GDELT scrapes are persisted daily, so as_of=past_date
returns the tone known on that day (assuming we've been scraping for that long).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import CountryToneScore, Stock
from app.services.signals.base import SignalResult, clip, empty_result

TONE_MIN = -3.0
TONE_MAX = 1.0
MIN_SAMPLES_FOR_CONFIDENCE = 6  # at least 6 hours of GDELT coverage on the day


class GeopoliticalToneSignal:
    name = "geopolitical_tone"

    def compute(self, db: Session, stock: Stock, as_of: date | None = None) -> SignalResult:
        if not stock.country_code:
            return empty_result("stock has no country_code")

        q = db.query(CountryToneScore).filter(CountryToneScore.country_code == stock.country_code)
        if as_of is not None:
            q = q.filter(CountryToneScore.score_date <= as_of)
        row = q.order_by(desc(CountryToneScore.score_date)).first()
        if row is None:
            return empty_result("no GDELT tone data — run /api/admin/refresh-gdelt")

        if row.article_count < MIN_SAMPLES_FOR_CONFIDENCE:
            return SignalResult(
                score=50.0,
                confidence=0.0,
                evidence={
                    "country_code": stock.country_code,
                    "score_date": row.score_date.isoformat(),
                    "mean_tone": round(row.mean_tone, 3),
                    "article_count": row.article_count,
                    "narrative": "Too few GDELT samples on this day to score.",
                },
            )

        # Linear map of mean_tone in [TONE_MIN, TONE_MAX] -> [0, 100].
        fraction = (row.mean_tone - TONE_MIN) / (TONE_MAX - TONE_MIN)
        score = clip(fraction * 100.0)
        confidence = min(1.0, row.article_count / 20.0)

        return SignalResult(
            score=score,
            confidence=confidence,
            evidence={
                "country_code": stock.country_code,
                "score_date": row.score_date.isoformat(),
                "mean_tone": round(row.mean_tone, 3),
                "article_count": row.article_count,
                "narrative": (
                    f"GDELT mean tone for {stock.country_code} on {row.score_date} "
                    f"is {row.mean_tone:+.2f} (across {row.article_count} hourly samples). "
                    f"Negative tone = bearish geopolitical backdrop."
                ),
            },
        )
