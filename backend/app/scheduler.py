"""APScheduler wiring: daily price refresh + score snapshot.

Runs in-process with the FastAPI app. Times are local server time. The scheduler
is started in the app's lifespan; jobs hold their own DB session.
"""

from __future__ import annotations

from logging import getLogger

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal
from app.services.gdelt import refresh_country_tone
from app.services.ingestion import refresh_all_prices
from app.services.insider import refresh_insider_activity
from app.services.news_sentiment import refresh_news_sentiment
from app.services.reddit import refresh_reddit_mentions
from app.services.snapshots import run_daily_snapshot
from app.services.stocktwits import refresh_stocktwits_activity

log = getLogger(__name__)


def _refresh_prices_job() -> None:
    log.info("scheduled job: refresh_all_prices")
    with SessionLocal() as db:
        try:
            refresh_all_prices(db, period="1mo")  # short window: only fill recent days
        except Exception as e:
            log.exception("price refresh failed: %s", e)


def _refresh_reddit_job() -> None:
    log.info("scheduled job: refresh_reddit_mentions")
    with SessionLocal() as db:
        try:
            result = refresh_reddit_mentions(db)
            log.info("reddit refresh complete: %s", result)
        except Exception as e:
            log.exception("reddit refresh failed: %s", e)


def _refresh_news_job() -> None:
    log.info("scheduled job: refresh_news_sentiment")
    with SessionLocal() as db:
        try:
            result = refresh_news_sentiment(db)
            log.info("news refresh complete: %s", result)
        except Exception as e:
            log.exception("news refresh failed: %s", e)


def _refresh_gdelt_job() -> None:
    log.info("scheduled job: refresh_country_tone")
    with SessionLocal() as db:
        try:
            result = refresh_country_tone(db)
            log.info("gdelt refresh complete: %s", result)
        except Exception as e:
            log.exception("gdelt refresh failed: %s", e)


def _refresh_insider_job() -> None:
    log.info("scheduled job: refresh_insider_activity")
    with SessionLocal() as db:
        try:
            result = refresh_insider_activity(db)
            log.info("insider refresh complete: %s", result)
        except Exception as e:
            log.exception("insider refresh failed: %s", e)


def _refresh_stocktwits_job() -> None:
    log.info("scheduled job: refresh_stocktwits_activity")
    with SessionLocal() as db:
        try:
            result = refresh_stocktwits_activity(db)
            log.info("stocktwits refresh complete: %s", result)
        except Exception as e:
            log.exception("stocktwits refresh failed: %s", e)


def _daily_snapshot_job() -> None:
    log.info("scheduled job: run_daily_snapshot")
    with SessionLocal() as db:
        try:
            result = run_daily_snapshot(db)
            log.info("snapshot complete: %s", result)
        except Exception as e:
            log.exception("snapshot failed: %s", e)


def build_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Europe/Copenhagen")
    # Price refresh after US market close: 22:30 CET / 23:30 CEST. Pick 23:00 as compromise.
    sched.add_job(_refresh_prices_job, CronTrigger(hour=23, minute=0), id="refresh_prices", replace_existing=True)
    # Reddit mention scrape — independent of market timing; pick a slot before snapshot.
    sched.add_job(_refresh_reddit_job, CronTrigger(hour=23, minute=5), id="refresh_reddit", replace_existing=True)
    # News sentiment refresh — also before snapshot.
    sched.add_job(_refresh_news_job, CronTrigger(hour=23, minute=7), id="refresh_news", replace_existing=True)
    # GDELT geopolitical tone — also before snapshot.
    sched.add_job(_refresh_gdelt_job, CronTrigger(hour=23, minute=8), id="refresh_gdelt", replace_existing=True)
    # Finnhub insider transactions (US-only; skipped if key not set).
    sched.add_job(_refresh_insider_job, CronTrigger(hour=23, minute=9), id="refresh_insider", replace_existing=True)
    # StockTwits per-symbol streams (US-only).
    sched.add_job(_refresh_stocktwits_job, CronTrigger(hour=22, minute=58), id="refresh_stocktwits", replace_existing=True)
    # Snapshot 10 minutes later so all upstream signals have landed.
    sched.add_job(_daily_snapshot_job, CronTrigger(hour=23, minute=10), id="daily_snapshot", replace_existing=True)
    return sched
