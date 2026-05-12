"""GDELT 2.0 DOC API: daily country-level news tone.

GDELT is a free, open project (https://www.gdeltproject.org/) that monitors every
news article published worldwide and scores its sentiment ("tone") in a scale
roughly [-10, +10]. Bad news days (wars, crises, political turmoil) drive the
country average tone sharply negative; routine days hover near 0.

For Stocky we pull the last 7 days of hourly tone per country and aggregate
to a daily mean. The geopolitical_tone signal then maps the home-country tone
to a 0-100 score: very negative = low score (avoid stocks in countries getting
hammered by bad news right now).
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timezone
from logging import getLogger

import httpx
from sqlalchemy.orm import Session

from app.models import CountryToneScore, Stock

log = getLogger(__name__)

API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "stocky-local/0.1 (paper-trading research)"}
# GDELT's published rate limit: "one every 5 seconds". 6.0 leaves comfortable margin.
INTER_REQUEST_DELAY_SEC = 6.0
RETRY_DELAYS_SEC = (10.0, 30.0)  # successive backoffs on 429 / network error


def _parse_gdelt_ts(s: str) -> datetime | None:
    # GDELT format: "20260512T140000Z"
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _fetch_country_tone(country_code: str) -> list[tuple[date, float, int]]:
    """Return [(date, mean_tone, sample_size_hours), ...] for the last 7 days for `country_code`.

    Retries on 429 and network errors with increasing backoff.
    """
    params = {
        "query": f"sourcecountry:{country_code}",
        "mode": "timelinetone",
        "timespan": "7d",
        "format": "json",
    }
    last_err: Exception | str | None = None
    for attempt, extra_wait in enumerate((0.0, *RETRY_DELAYS_SEC)):
        if extra_wait > 0:
            log.info("gdelt %s retry %d after %ss", country_code, attempt, extra_wait)
            time.sleep(extra_wait)
        try:
            r = httpx.get(API_URL, params=params, headers=HEADERS, timeout=30)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = e
            continue
        if r.status_code == 429:
            last_err = f"429: {r.text[:120]}"
            continue
        if r.status_code != 200:
            log.warning("gdelt %s -> %s: %s", country_code, r.status_code, r.text[:120])
            return []
        try:
            timeline = r.json().get("timeline", [])
        except Exception as e:
            log.warning("gdelt %s parse failed: %s", country_code, e)
            return []
        if not timeline:
            return []

        by_day: dict[date, list[float]] = defaultdict(list)
        for point in timeline[0].get("data", []):
            ts = _parse_gdelt_ts(point.get("date", ""))
            if ts is None:
                continue
            value = point.get("value")
            if value is None:
                continue
            by_day[ts.date()].append(float(value))

        return [(d, sum(vs) / len(vs), len(vs)) for d, vs in sorted(by_day.items())]

    log.warning("gdelt %s exhausted retries: %s", country_code, last_err)
    return []


def refresh_country_tone(db: Session) -> dict:
    """Pull tone for every country present in the stock universe. Idempotent."""
    countries = sorted({
        s.country_code
        for s in db.query(Stock).filter(Stock.country_code.isnot(None)).all()
    })

    inserted = 0
    updated = 0
    failures: list[str] = []

    for i, country in enumerate(countries):
        if i > 0:
            time.sleep(INTER_REQUEST_DELAY_SEC)
        try:
            day_rows = _fetch_country_tone(country)
        except Exception as e:
            log.warning("gdelt fetch failed for %s: %s", country, e)
            failures.append(country)
            continue
        if not day_rows:
            failures.append(country)
            continue

        for day, mean_tone, sample_size in day_rows:
            existing = (
                db.query(CountryToneScore)
                .filter(CountryToneScore.country_code == country, CountryToneScore.score_date == day)
                .one_or_none()
            )
            if existing is None:
                db.add(CountryToneScore(
                    country_code=country,
                    score_date=day,
                    mean_tone=mean_tone,
                    article_count=sample_size,
                ))
                inserted += 1
            else:
                existing.mean_tone = mean_tone
                existing.article_count = sample_size
                updated += 1
    db.commit()
    return {
        "countries_scanned": len(countries),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "failures": failures,
    }
