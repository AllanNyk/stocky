"""Reddit mention scraper.

Pulls recent submissions from a small list of finance subreddits, counts how many
posts contain each stock's WSB aliases, and persists per-stock daily totals.

This is the alt-data piece that differentiates Stocky's prediction score from a
plain-quant tool: a stock with a sudden mention spike on r/wallstreetbets is
attracting retail attention, which historically correlates with short-term price moves
(direction varies; we expose the signal, the user decides what it means).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timezone
from logging import getLogger

import praw
from prawcore.exceptions import PrawcoreException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RedditMentionCount, Stock

log = getLogger(__name__)

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]
POSTS_PER_SUB = 250  # `new` listing only; covers ~24h of low-volume subs, less for WSB


def _build_reddit_client() -> praw.Reddit:
    if not settings.reddit_enabled:
        raise RuntimeError("Reddit credentials are not configured (see backend/.env)")
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        check_for_async=False,
    )


def _compile_patterns(stocks: list[Stock]) -> dict[int, re.Pattern[str]]:
    """One regex per stock matching any of its WSB aliases as a whole word."""
    patterns: dict[int, re.Pattern[str]] = {}
    for s in stocks:
        aliases = (s.wsb_aliases or s.ticker).split("|")
        # Sort by length desc so longer aliases match first inside the alternation.
        aliases = sorted({a.strip() for a in aliases if a.strip()}, key=len, reverse=True)
        escaped = [re.escape(a) for a in aliases]
        # Custom boundary: a name char (letter/digit/_) must not abut the match on either side.
        # Standard \b doesn't work for "BRK.B" or "H&M" since . and & aren't word chars.
        pattern = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_])", re.IGNORECASE)
        patterns[s.id] = pattern
    return patterns


def fetch_mention_counts(stocks: list[Stock]) -> dict[int, tuple[int, set[str]]]:
    """Count today's mentions per stock across SUBREDDITS.

    Returns {stock_id: (mention_count, set_of_subreddits_seen_in)}.
    `mention_count` is 'number of posts mentioning the stock at least once',
    not 'number of regex matches' — multiple matches in one post still count as one.
    """
    reddit = _build_reddit_client()
    patterns = _compile_patterns(stocks)
    counts: Counter[int] = Counter()
    subs_per_stock: dict[int, set[str]] = {s.id: set() for s in stocks}

    for sub_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.new(limit=POSTS_PER_SUB):
                text = f"{post.title}\n{post.selftext or ''}"
                for stock_id, pat in patterns.items():
                    if pat.search(text):
                        counts[stock_id] += 1
                        subs_per_stock[stock_id].add(sub_name)
        except PrawcoreException as e:
            log.warning("reddit fetch failed for r/%s: %s", sub_name, e)
            continue

    return {sid: (counts[sid], subs_per_stock[sid]) for sid in patterns}


def refresh_reddit_mentions(db: Session, mention_date: date | None = None) -> dict:
    """Pull + persist today's mention counts. Idempotent (overwrites the row for the date)."""
    if not settings.reddit_enabled:
        return {"skipped": True, "reason": "Reddit credentials not configured"}

    today = mention_date or date.today()
    stocks = db.query(Stock).filter(Stock.is_benchmark.is_(False)).all()

    counts = fetch_mention_counts(stocks)

    total_mentions = 0
    nonzero = 0
    for stock in stocks:
        count, subs = counts.get(stock.id, (0, set()))
        total_mentions += count
        if count > 0:
            nonzero += 1
        existing = (
            db.query(RedditMentionCount)
            .filter(RedditMentionCount.stock_id == stock.id, RedditMentionCount.mention_date == today)
            .one_or_none()
        )
        if existing is None:
            db.add(RedditMentionCount(
                stock_id=stock.id,
                mention_date=today,
                count=count,
                subreddits_seen="|".join(sorted(subs)) or None,
            ))
        else:
            existing.count = count
            existing.subreddits_seen = "|".join(sorted(subs)) or None
    db.commit()
    return {
        "mention_date": today.isoformat(),
        "stocks_scanned": len(stocks),
        "stocks_with_mentions": nonzero,
        "total_mentions": total_mentions,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
