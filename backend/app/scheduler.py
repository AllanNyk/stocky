"""APScheduler wiring: daily price refresh + score snapshot.

Runs in-process with the FastAPI app. Times are local server time. The scheduler
is started in the app's lifespan; jobs hold their own DB session.
"""

from __future__ import annotations

from logging import getLogger

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal
from app.services.ingestion import refresh_all_prices
from app.services.reddit import refresh_reddit_mentions
from app.services.snapshots import run_daily_snapshot

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
    # Snapshot 10 minutes later so prices + reddit have landed.
    sched.add_job(_daily_snapshot_job, CronTrigger(hour=23, minute=10), id="daily_snapshot", replace_existing=True)
    return sched
